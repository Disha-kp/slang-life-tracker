import requests
import sqlite3
import random
import time
import datetime
import os
import json

# Configuration
# Anchor to the project root (not cwd), since Streamlit Cloud doesn't
# guarantee the working directory equals the repo root.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_PROJECT_ROOT, 'data', 'slang_data.db')
_USER_AGENTS_PATH = os.path.join(_PROJECT_ROOT, 'data', 'user_agents.txt')
PENDING_WORDS_PATH = os.path.join(_PROJECT_ROOT, 'data', 'pending_words.txt')


def _load_user_agents():
    """Load real browser User-Agent strings from data/user_agents.txt.

    Reddit's anti-bot detection blocks an obviously fake UA (like the old
    hardcoded 'SlangResearchBot/1.0') almost immediately, which is why Deep
    Search kept returning empty results even for real, common slang. Using
    a real, rotating browser UA significantly improves reliability.
    """
    fallback = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36']
    if os.path.exists(_USER_AGENTS_PATH):
        with open(_USER_AGENTS_PATH, encoding='utf-8') as f:
            agents = [line.strip() for line in f if line.strip()]
        if agents:
            return agents
    return fallback


USER_AGENTS = _load_user_agents()

SUBREDDITS = {
    'niche': ['london', 'ukdrill', 'CasualUK'],
    'mainstream': ['AskReddit', 'memes']
}
DEFAULT_KEYWORDS = ['aura', 'cooked', 'peng']

def setup_database():
    """Create the 'mentions' table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mentions (
            id TEXT PRIMARY KEY,
            keyword TEXT,
            subreddit TEXT,
            content TEXT,
            timestamp REAL,
            is_mainstream BOOLEAN
        )
    ''')
    conn.commit()
    conn.close()

def fetch_reddit_data(subreddit, keyword, is_mainstream, print_preview=False, _retry=True):
    """
    Fetch posts from a subreddit for a specific keyword using the JSON search endpoint.
    URL: https://www.reddit.com/r/[SUBREDDIT]/search.json?q=[KEYWORD]&restrict_sr=1&sort=new
    """
    url = f"https://www.reddit.com/r/{subreddit}/search.json"
    user_agent = random.choice(USER_AGENTS)
    headers = {
        'User-Agent': user_agent,
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    params = {
        'q': keyword,
        'restrict_sr': '1',
        'sort': 'new',
        'limit': 100
    }
    
    print(f"Fetching '{keyword}' from r/{subreddit}...")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 429:
            print(f"Rate limited (429)! Sleeping for 10 seconds...")
            time.sleep(10)
            return []

        if response.status_code == 403 and _retry:
            # Likely blocked on this UA/session - back off briefly and retry once
            # with a fresh, randomly-chosen User-Agent before giving up.
            print("Blocked (403). Retrying once with a different User-Agent...")
            time.sleep(2)
            return fetch_reddit_data(subreddit, keyword, is_mainstream, print_preview, _retry=False)

        if response.status_code != 200:
            print(f"Error {response.status_code}: {response.text[:200]}")
            return []
            
        data = response.json()
        results = []
        
        children = data.get('data', {}).get('children', [])
        
        for i, child in enumerate(children):
            item = child.get('data', {})
            # Extract content: title + selftext gives the best coverage for 'mentions' in posts
            title = item.get('title', '')
            selftext = item.get('selftext', '')
            content = f"{title} {selftext}".strip()
            
            # Print preview if requested (first 5)
            if print_preview and i < 5:
                print(f"--- Result {i+1} ---")
                print(f"ID: {item.get('name')}")
                print(f"Content: {content[:100]}...") # Truncate for display
                print(f"Timestamp: {item.get('created_utc')}")

            results.append((
                item.get('name'), # ID
                keyword,
                subreddit,
                content,
                item.get('created_utc'),
                is_mainstream
            ))
            
        print(f"Found {len(results)} results.")
        return results

    except Exception as e:
        print(f"Exception fetching data: {e}")
        return []

def save_to_db(results):
    """Save a list of results to the database."""
    if not results:
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    count = 0
    for row in results:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO mentions (id, keyword, subreddit, content, timestamp, is_mainstream)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', row)
            count += 1
        except sqlite3.Error as e:
            print(f"DB Error: {e}")
            
    conn.commit()
    conn.close()
    print(f"Saved {count} new mentions to DB.")

def run_test_fetch():
    """Specific test: 'aura' in 'r/london' showing first 5 results."""
    print(">>> RUNNING TEST FETCH: 'aura' in 'r/london' <<<")
    results = fetch_reddit_data('london', 'aura', is_mainstream=False, print_preview=True)
    save_to_db(results)
    print(">>> TEST COMPLETE <<<\n")

def scrape_word(word):
    """
    Scrape a specific word from all configured subreddits (Niche & Mainstream).
    Returns the total number of mentions found and saved.
    """
    setup_database() # Ensure DB exists
    total_found = 0
    print(f"\n>>> STARTING ON-DEMAND SCRAPE FOR: '{word}' <<<")
    
    # 1. Scrape Niche Subreddits
    for sub in SUBREDDITS['niche']:
        results = fetch_reddit_data(sub, word, is_mainstream=False)
        save_to_db(results)
        total_found += len(results)
        time.sleep(1) # Slight delay

    # 2. Scrape Mainstream Subreddits
    for sub in SUBREDDITS['mainstream']:
        results = fetch_reddit_data(sub, word, is_mainstream=True)
        save_to_db(results)
        total_found += len(results)
        time.sleep(1)

    print(f">>> SCRAPE COMPLETE FOR '{word}'. Total new mentions: {total_found} <<<\n")
    return total_found

def log_pending_word(word):
    """
    Record a word that a live user searched for but Deep Search couldn't
    find anything on. The scheduled auto_updater.py job (which has full,
    unrestricted internet access and no UI timeout pressure) retries these
    specifically, so a word that fails live can still get added later
    without anyone re-typing it.
    """
    word = (word or "").strip().lower()
    if not word:
        return
    existing = set()
    if os.path.exists(PENDING_WORDS_PATH):
        with open(PENDING_WORDS_PATH, encoding='utf-8') as f:
            existing = {line.strip() for line in f if line.strip()}
    if word not in existing:
        with open(PENDING_WORDS_PATH, 'a', encoding='utf-8') as f:
            f.write(word + "\n")


def search_global_feed(word):
    """
    Fallback: Search r/all for the word to find any usage context.
    Returns: List of content strings.
    """
    print(f"Searching r/all for '{word}'...")
    results = fetch_reddit_data('all', word, is_mainstream=True, print_preview=False)
    # Return just the text content for analysis
    return [r[3] for r in results]


def main():
    setup_database()
    
    # Run the specific test first as requested
    run_test_fetch()
    
    # Run the full scrape loop for defaults
    print(">>> STARTING BATCH SCRAPE <<<")
    for word in DEFAULT_KEYWORDS:
        scrape_word(word)

if __name__ == "__main__":
    main()