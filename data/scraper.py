import praw
import sqlite3
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Reddit API Credentials
CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
USER_AGENT = os.getenv('REDDIT_USER_AGENT')

# Initialize PRAW
reddit = praw.Reddit(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    user_agent=USER_AGENT
)

# Configuration
NICHE_SUBREDDITS = ['london', 'ukdrill']
MAINSTREAM_SUBREDDITS = ['AskReddit', 'memes']
TARGET_WORDS = ['aura', 'cooked', 'peng']
DB_PATH = 'data/slang_data.db'

def init_db():
    """Initialize the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_mentions (
            date TEXT,
            subreddit_type TEXT,
            word TEXT,
            count INTEGER,
            PRIMARY KEY (date, subreddit_type, word)
        )
    ''')
    conn.commit()
    conn.close()

def search_slang(subreddits, subreddit_type):
    """Search for slang words in given subreddits."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    
    print(f"Scraping {subreddit_type} subreddits...")

    for word in TARGET_WORDS:
        for sub_name in subreddits:
            print(f"  Searching r/{sub_name} for '{word}' (past 30 days)...")
            try:
                subreddit = reddit.subreddit(sub_name)
                # Search for comments matching the word in the last month
                # Note: Reddit API search limit is typically ~1000 results.
                # For high-volume words/subs, this will be a sample, but sufficient for a 'Mainstream' signal.
                
                comments = subreddit.search(f'"{word}"', type='comment', time_filter='month', limit=None)
                
                daily_counts = {}
                
                count_total = 0
                for comment in comments:
                    created_date = datetime.fromtimestamp(comment.created_utc).strftime('%Y-%m-%d')
                    daily_counts[created_date] = daily_counts.get(created_date, 0) + 1
                    count_total += 1

                print(f"    Found {count_total} total mentions in last 30 days.")
                
                # Upsert daily counts into DB
                for date_str, count in daily_counts.items():
                    cursor.execute('''
                        INSERT INTO daily_mentions (date, subreddit_type, word, count)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(date, subreddit_type, word) 
                        DO UPDATE SET count = excluded.count
                    ''', (date_str, subreddit_type, word, count))
                    # Note: Using excluded.count (REPLACE) for the backfill. 
                    # If running daily incrementally, we might want logic to ADD, 
                    # but since we are searching 'month' every time here, REPLACE is safer to avoid double counting 
                    # if the script is run multiple times on the same day for the same historical window.
                    # A true production incremental scraper would only search 'day' and ADD (or check IDs).
                    # This script fulfills the "Fetch last 30 days" requirement.

            except Exception as e:
                print(f"Error scraping r/{sub_name}: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Error: Reddit credentials not found. Check your .env file.")
    else:
        init_db()
        search_slang(NICHE_SUBREDDITS, 'niche')
        search_slang(MAINSTREAM_SUBREDDITS, 'mainstream')
        print("Scraping complete.")
