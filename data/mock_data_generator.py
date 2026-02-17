import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

DB_PATH = 'data/slang_data.db'

def generate_mock_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Ensure table exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_mentions (
            date TEXT,
            subreddit_type TEXT,
            word TEXT,
            count INTEGER,
            PRIMARY KEY (date, subreddit_type, word)
        )
    ''')

    words = ['aura', 'cooked', 'peng']
    start_date = datetime.now() - timedelta(days=60)
    
    data = []
    
    for i in range(60):
        current_date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
        
        # 'aura': Rising in mainstream, high in niche
        # Niche: constant high. Mainstream: Exponential growth.
        data.append((current_date, 'niche', 'aura', int(50 + np.random.normal(0, 5))))
        data.append((current_date, 'mainstream', 'aura', int(10 * np.exp(0.05 * i) + np.random.normal(0, 2))))

        # 'cooked': Already Cringe (Mainstream > 5x Niche)
        # Niche: dropping. Mainstream: High.
        data.append((current_date, 'niche', 'cooked', int(max(10, 50 - 0.5 * i) + np.random.normal(0, 5))))
        data.append((current_date, 'mainstream', 'cooked', int(300 + np.random.normal(0, 20))))

        # 'peng': Stable Niche, low Mainstream
        data.append((current_date, 'niche', 'peng', int(80 + np.random.normal(0, 10))))
        data.append((current_date, 'mainstream', 'peng', int(20 + np.random.normal(0, 5))))

    # Insert data
    cursor.executemany('''
        INSERT INTO daily_mentions (date, subreddit_type, word, count)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(date, subreddit_type, word) DO UPDATE SET count=excluded.count
    ''', data)
    
    conn.commit()
    conn.close()
    print("Mock data generated.");

if __name__ == "__main__":
    generate_mock_data()
