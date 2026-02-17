import sqlite3
import pandas as pd
import os
import csv
from datetime import datetime
from data.no_api_scraper import search_global_feed

DB_PATH = 'data/word_vault.db'
CSV_PATH = 'data/slang_master_2026.csv'

class LifecycleEngine:
    def __init__(self):
        self._init_db()
        self._seed_from_csv()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS slang_terms (
                word TEXT PRIMARY KEY,
                meaning TEXT,
                origin_era TEXT,
                category TEXT,
                status_2026 TEXT,
                last_searched_at TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def _seed_from_csv(self):
        if not os.path.exists(CSV_PATH):
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if empty (simple check) - or just use INSERT OR IGNORE
        with open(CSV_PATH, mode='r') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                cursor.execute('''
                    INSERT OR IGNORE INTO slang_terms (word, meaning, origin_era, category, status_2026)
                    VALUES (?, ?, ?, ?, ?)
                ''', (row['word'], row['meaning'], row['origin_era'], row['category'], row['2026_status']))
        
        conn.commit()
        conn.close()

    def get_slang_data(self, word):
        """
        Retrieves slang data. 
        Layer 1: DB (pre-seeded with CSV).
        Layer 2: Scraper Fallback.
        """
        word_lower = word.lower() # DB storage logic? Let's store original case from CSV, but search case-insensitive?
        # Creating a case-insensitive search logic
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM slang_terms WHERE lower(word) = ?", (word_lower,))
        row = cursor.fetchone()
        
        if row:
            # Update last_searched_at
            cursor.execute("UPDATE slang_terms SET last_searched_at = ? WHERE lower(word) = ?", 
                           (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), word_lower))
            conn.commit()
            data = dict(row)
            conn.close()
            return data, "Archive"
        
        conn.close()
        
        # Not found -> Layer 2 Scraper
        return self._perform_deep_search(word), "Deep Search"

    def _perform_deep_search(self, word):
        print(f"Deep Search triggered for {word}...")
        results = search_global_feed(word)
        
        # Heuristic Analysis for new words (Mock for now, real implementation would analyze text)
        status = "Emerging"
        meaning = "Discovered via Deep Search. Analysis pending."
        origin_era = "2026 (New)"
        category = "Unknown"
        
        # Save to DB
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO slang_terms (word, meaning, origin_era, category, status_2026, last_searched_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (word, meaning, origin_era, category, status, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        
        return {
            'word': word,
            'meaning': meaning,
            'origin_era': origin_era,
            'status_2026': status
        }

    def get_timeline_data(self, target_word):
        """
        Returns data for the 400-year timeline visualization.
        """
        # Get target word data
        target_data, _ = self.get_slang_data(target_word)
        if not target_data:
            return None
        
        target_year = self._parse_era(target_data['origin_era'])
        
        # Get Anchors (One from each century if possible)
        anchors = []
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Simple random sample of anchors from different eras
        # We want a spread: 1600s, 1700s, 1800s, 1900s, 2000s
        eras_to_sample = ["1600s", "1700s", "1800s", "1900s", "2000s"]
        
        for era_search in eras_to_sample:
            cursor.execute("SELECT word, origin_era FROM slang_terms WHERE origin_era LIKE ? ORDER BY RANDOM() LIMIT 1", (f"%{era_search}%",))
            row = cursor.fetchone()
            if row:
                anchors.append({
                    'word': row['word'],
                    'year': self._parse_era(row['origin_era']),
                    'type': 'anchor'
                })
        conn.close()
        
        return {
            'target': {
                'word': target_data['word'],
                'year': target_year,
                'type': 'target'
            },
            'anchors': anchors
        }

    def _parse_era(self, era_str):
        """
        Heuristic parsing of Era strings into an approximate Year integer.
        """
        if not era_str:
            return 2026 # Default to now
            
        era_str = era_str.lower()
        
        if "1600" in era_str: return 1650
        if "1700" in era_str or "1750" in era_str: return 1750
        if "1770" in era_str: return 1770
        if "1800" in era_str: return 1850
        if "victorian" in era_str: return 1880
        if "1830" in era_str: return 1830
        if "1840" in era_str: return 1840
        if "1880" in era_str: return 1880
        if "1890" in era_str or "flapper" in era_str: return 1895
        if "1900" in era_str: return 1905
        if "1910" in era_str: return 1915
        if "1920" in era_str: return 1925
        if "1930" in era_str: return 1935
        if "1950" in era_str: return 1955
        if "1960" in era_str: return 1965
        if "1980" in era_str: return 1985
        if "1990" in era_str: return 1995
        if "2000" in era_str: return 2005
        if "2010" in era_str: return 2015
        if "2020" in era_str: return 2023
        if "2021" in era_str: return 2021
        if "2022" in era_str: return 2022
        if "2023" in era_str: return 2023
        if "2024" in era_str: return 2024
        if "2025" in era_str: return 2025
        
        # Fallback for "2026 (New)" etc.
        import re
        match = re.search(r'(\d{4})', era_str)
        if match:
            return int(match.group(1))
            
        return 2026
