import sqlite3
import pandas as pd
import nltk
from nltk.corpus import words, wordnet
from nltk.sentiment import SentimentIntensityAnalyzer
import os
import csv
import datetime
from data.no_api_scraper import fetch_reddit_data

# Configuration
DB_PATH = 'data/word_vault.db'
SLANG_CSV_PATH = 'data/slang_data.csv'

# Ensure NLTK data (re-run just in case)
try:
    nltk.data.find('corpora/words')
except LookupError:
    nltk.download('words')
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon')
try:
    nltk.data.find('corpora/wordnet.zip')
except LookupError:
    nltk.download('wordnet')

class WordVault:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS word_intelligence (
                word TEXT PRIMARY KEY,
                classification TEXT,
                slang_ratio REAL,
                avg_sentiment REAL,
                data_source TEXT,
                last_analyzed TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def get_word(self, word):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM word_intelligence WHERE word = ?", (word,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                'word': row[0],
                'classification': row[1],
                'slang_ratio': row[2],
                'avg_sentiment': row[3],
                'data_source': row[4],
                'last_analyzed': row[5]
            }
        return None

    def save_word(self, data):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO word_intelligence 
            (word, classification, slang_ratio, avg_sentiment, data_source, last_analyzed)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['word'], 
            data['classification'], 
            data['slang_ratio'], 
            data['avg_sentiment'], 
            data['data_source'], 
            datetime.datetime.now()
        ))
        conn.commit()
        conn.close()

class MasterWordAnalyzer:
    def __init__(self):
        self.vault = WordVault()
        self.english_vocab = set(words.words())
        self.sia = SentimentIntensityAnalyzer()
        self.known_slang = self._load_slang_csv()

    def _load_slang_csv(self):
        slang_dict = {}
        if os.path.exists(SLANG_CSV_PATH):
            with open(SLANG_CSV_PATH, mode='r') as infile:
                reader = csv.DictReader(infile)
                for row in reader:
                    slang_dict[row['word'].lower()] = row['sentiment']
        return slang_dict

    def analyze(self, word):
        word_lower = word.lower()
        
        # 0. Check Vault (Persistence Layer)
        cached_data = self.vault.get_word(word_lower)
        if cached_data:
            print(f"[{word}] found in Vault: {cached_data['classification']}")
            return cached_data

        result = {
            'word': word_lower,
            'classification': 'unknown',
            'slang_ratio': 0.0,
            'avg_sentiment': 0.0,
            'data_source': 'system'
        }

        # 1. Baseline Layer (Standard English)
        if word_lower in self.english_vocab or wordnet.synsets(word_lower):
            result['classification'] = 'standard'
            result['slang_ratio'] = 0.0
            result['data_source'] = 'nltk_corpus'
            self.vault.save_word(result)
            return result

        # 2. Slang Layer (Static)
        if word_lower in self.known_slang:
            result['classification'] = 'established_slang'
            result['slang_ratio'] = 1.0
            sentiment_map = {'positive': 0.5, 'negative': -0.5, 'neutral': 0.0}
            result['avg_sentiment'] = sentiment_map.get(self.known_slang[word_lower], 0.0)
            result['data_source'] = 'slang_csv'
            self.vault.save_word(result)
            return result

        # 3. Dynamic Layer (Emerging)
        print(f"[{word}] unknown. initiating rapid scrape...")
        subreddits = ['london', 'ukdrill', 'teenagers']
        total_mentions = 0
        total_sentiment = 0.0
        niche_mentions = 0
        
        all_comments = []
        for sub in subreddits:
            # Reusing existing scraper logic logic but treating all as potential sources
            is_niche = sub in ['london', 'ukdrill']
            fetched = fetch_reddit_data(sub, word_lower, is_mainstream=not is_niche)
            
            for item in fetched:
                # item structure: (id, keyword, sub, content, timestamp, is_mainstream)
                content = item[3]
                all_comments.append(content)
                total_mentions += 1
                if is_niche:
                    niche_mentions += 1
                
                # VADER Sentiment
                vs = self.sia.polarity_scores(content)
                total_sentiment += vs['compound']

        if total_mentions > 0:
            result['classification'] = 'emerging_slang'
            result['avg_sentiment'] = total_sentiment / total_mentions
            # Slang Ratio: How much is it used in niche/slang-heavy subs vs general? 
            # Or just usage count? Let's use simple Niche Ratio for now.
            result['slang_ratio'] = niche_mentions / total_mentions
            result['data_source'] = 'reddit_dynamic'
        else:
             result['classification'] = 'unknown_neologism'
             result['data_source'] = 'not_found'

        self.vault.save_word(result)
        return result

if __name__ == "__main__":
    analyzer = MasterWordAnalyzer()
    
    test_words = ['apple', 'aura', 'cooked'] # apple=standard, aura=slang/standard ambiguity, cooked=slang
    # Note: 'cooked' is a standard word too, so it might get caught by layer 1 unless we handle polysemy.
    # NLTK 'cooked' is standard. The plan said "If not found...". 
    # 'cooked' IS found in NLTK. So it will return 'standard'.
    # Data correction: 'cooked' usage as slang is slang. 
    # But strictly following the prompt requirements: "Baseline Layer... identify if recognized as standard English".
    # So 'cooked' -> Standard is 'correct' per the strict requirements, even if semanticially 'slang' in context.
    # However, 'scran' or 'skibidi' would hit Layer 3.
    # 'aura' is also standard.
    
    # Let's verify 'skibidi' as well to see Layer 3 in action.
    test_words.append('skibidi') 
    
    print("--- MasterWordAnalyzer Test Run ---")
    for w in test_words:
        res = analyzer.analyze(w)
        print(f"Word: {w.ljust(10)} | Class: {res['classification'].ljust(15)} | Source: {res['data_source']}")
