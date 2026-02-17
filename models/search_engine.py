import sqlite3
import pandas as pd
import requests
import json
import time
import os
import csv
from datetime import datetime

# Configuration
CSV_PATH = 'data/slang_2026_master.csv'
DB_PATH = 'data/slang_vault.db'
CUSTOM_USER_AGENT = 'SlangResearchBot/1.0'

class SearchEngine:
    def __init__(self):
        self._init_db()
        self.csv_data = self._load_csv()

    def _init_db(self):
        """Initialize the slang_vault.db"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS discovered_slang (
                word TEXT PRIMARY KEY,
                status TEXT,
                found_date TEXT,
                niche_count INTEGER,
                mainstream_count INTEGER,
                source TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def _load_csv(self):
        """Load the static CSV into a dictionary for fast lookup."""
        data = {}
        if os.path.exists(CSV_PATH):
            with open(CSV_PATH, mode='r') as infile:
                reader = csv.DictReader(infile)
                for row in reader:
                    data[row['word'].lower()] = {
                        'meaning': row['meaning'],
                        'status': row['initial_status'],
                        'source': '2026 Archive'
                    }
        return data

    def _fetch_reddit_count(self, word, subreddit):
        """Fetch count of mentions from a subreddit using search.json."""
        url = f"https://www.reddit.com/r/{subreddit}/search.json"
        headers = {'User-Agent': CUSTOM_USER_AGENT}
        params = {
            'q': word,
            'restrict_sr': '1',
            'sort': 'new',
            't': 'month',
            'limit': 100
        }
        try:
            response = requests.get(url, headers=headers, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return len(data.get('data', {}).get('children', []))
            elif response.status_code == 429:
                print("Rate limit hit. Sleeping 2s.")
                time.sleep(2)
        except Exception as e:
            print(f"Error fetching from {subreddit}: {e}")
        return 0

    def search_word(self, word):
        """
        Main Search Function (3-Layer Logic).
        """
        word_lower = word.lower()

        # LAYER 1: CSV Check
        if word_lower in self.csv_data:
            return self.csv_data[word_lower]

        # LAYER 2: Deep Search & LAYER 3: Classification
        # If not in CSV, we scrape to classify.
        
        # Niche Subreddits
        niche_subs = ['london', 'ukdrill']
        niche_total = 0
        for sub in niche_subs:
            niche_total += self._fetch_reddit_count(word_lower, sub)
            time.sleep(1) # Polite delay

        # Mainstream Subreddits
        mainstream_subs = ['AskReddit', 'funny']
        mainstream_total = 0
        for sub in mainstream_subs:
            mainstream_total += self._fetch_reddit_count(word_lower, sub)
            time.sleep(1)

        # Classification Logic
        total = niche_total + mainstream_total
        status = "Unknown"
        
        if total == 0:
            # Fallback to r/all if specifically requested by user requirement, 
            # or just return Unknown. The prompt says "Layers... Deep Search Fallback... r/all".
            # Let's do one last check on r/all if specific subs failed.
            all_count = self._fetch_reddit_count(word_lower, 'all')
            if all_count > 0:
                status = "Emerging" # Found in r/all but not specific buckets -> Emerging
            else:
                return None # Truly not found
        else:
            if niche_total > mainstream_total:
                status = "Niche"
            elif mainstream_total > (niche_total * 3):
                status = "Cringe"
            else:
                status = "Peak"

        # Save to DB (Layer 4)
        result = {
            'word': word,
            'meaning': 'Discovered via Deep Search', # Placeholder meaning
            'status': status,
            'source': 'Deep Search'
        }
        self._save_to_db(word, status, niche_total, mainstream_total)
        
        return result

    def _save_to_db(self, word, status, niche, mainstream):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO discovered_slang 
            (word, status, found_date, niche_count, mainstream_count, source)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (word, status, datetime.now().strftime('%Y-%m-%d'), niche, mainstream, 'Deep Search'))
        conn.commit()
        conn.close()

# For quick testing
if __name__ == "__main__":
    engine = SearchEngine()
    print(engine.search_word("aura")) # Should be in CSV
    print(engine.search_word("skibidi")) # Should be in CSV
    print(engine.search_word("madeupword123")) # Should return None
