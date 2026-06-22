import sqlite3
import pandas as pd
import os
import csv
from datetime import datetime
from data.no_api_scraper import search_global_feed

# Anchor paths to the project root (not the current working directory),
# since Streamlit Cloud doesn't guarantee cwd == repo root.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_PROJECT_ROOT, 'data', 'word_vault.db')
CSV_PATH = os.path.join(_PROJECT_ROOT, 'data', 'slang_master_2026.csv')

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
        from data.no_api_scraper import log_pending_word
        from data.urban_dictionary import fetch_definition
        print(f"Deep Search triggered for {word}...")

        # Heuristic Analysis for new words
        status = "Unverified"
        meaning = "Deep search returned no results. Try again later."
        origin_era = "2026"
        category = "Unknown"
        found_definition = False

        # Primary source: Urban Dictionary, an actual dictionary of slang
        # definitions. This is far more reliable than scanning Reddit post
        # text for the literal phrase " is a " or " means ", which almost
        # never naturally occurs — that was the real reason most words came
        # back with no definition.
        ud_definition = fetch_definition(word)
        if ud_definition:
            meaning = ud_definition
            status = "Emerging"
            category = "Slang (Urban Dictionary)"
            found_definition = True
        else:
            # Fallback: scan Reddit for any usage context, in case the word
            # is too new even for Urban Dictionary.
            results = search_global_feed(word)
            valid_results = [r for r in results if r and len(r.strip()) > 10]

            if valid_results:
                import random
                def_candidates = [r for r in valid_results if " means " in r or " is a " in r]
                selected_text = random.choice(def_candidates) if def_candidates else random.choice(valid_results)

                selected_text = selected_text.replace('\n', ' ').strip()
                if len(selected_text) > 200:
                    selected_text = selected_text[:197] + "..."

                meaning = f"Context: \"{selected_text}\""
                status = "Emerging"
                found_definition = True

        if not found_definition:
            # Queue this word so the scheduled auto-updater (full internet
            # access, no UI timeout) can retry it more thoroughly later.
            log_pending_word(word)

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
            'status_2026': status,
            'category': category
        }

    def get_timeline_data(self, target_word):
        """
        Builds a deterministic "Cultural Wave" curve for this word, derived
        only from its own real archive fields (origin_era, status_2026) —
        not random numbers, and not unrelated other words. The curve
        illustrates the word's rise from its documented origin year to its
        current lifecycle status by 2026.

        Returns: {'word': str, 'origin_year': int, 'status': str,
                  'points': [{'year': int, 'height': float}, ...]} or None.
        """
        data, _ = self.get_slang_data(target_word)
        if not data:
            return None

        origin_year = self._parse_origin_year(data.get('origin_era', ''))
        status = data.get('status_2026', 'Unverified')
        current_year = datetime.now().year

        end_height = self.STATUS_HEIGHTS.get(status, 0.3)
        start_height = 0.05

        if origin_year >= current_year:
            # Brand-new word: just show a short, sharp recent rise.
            origin_year = current_year - 1

        num_points = 6
        points = []
        for i in range(num_points):
            t = i / (num_points - 1)
            year = round(origin_year + t * (current_year - origin_year))
            # Ease-in curve: slow start, faster rise near the present —
            # mirrors how slang typically stays flat/niche for a long time
            # before suddenly taking off.
            height = start_height + (end_height - start_height) * (t ** 1.6)
            points.append({'year': year, 'height': round(height, 3)})

        # Make sure the final point lands exactly on the current status height.
        points[-1] = {'year': current_year, 'height': end_height}

        return {
            'word': data.get('word', target_word),
            'origin_year': origin_year,
            'status': status,
            'points': points,
        }

    STATUS_HEIGHTS = {
        'Niche': 0.2,
        'Unverified': 0.15,
        'Emerging': 0.3,
        'Peak': 0.55,
        'Mainstream': 0.75,
        'Cringe': 1.0,
    }

    @staticmethod
    def _parse_origin_year(origin_era: str) -> int:
        """Thin wrapper kept for clarity at the call site; delegates to the
        richer _parse_era heuristic below."""
        return LifecycleEngine._parse_era(None, origin_era)

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