import sqlite3
import os

DB_PATH = 'data/slang_data.db'

def remove_duplicates():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check initial count
        cursor.execute("SELECT COUNT(*) FROM mentions")
        initial_count = cursor.fetchone()[0]
        print(f"Initial row count: {initial_count}")

        # Delete duplicates, keeping the one with the smallest rowid (oldest insertion)
        cursor.execute('''
            DELETE FROM mentions
            WHERE rowid NOT IN (
                SELECT MIN(rowid)
                FROM mentions
                GROUP BY content, subreddit  -- Group by content AND subreddit to be safe, or just content? User said 'body'. 
                                             -- Let's stick to content to be strict about unique text.
            )
        ''')
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        # Check final count
        cursor.execute("SELECT COUNT(*) FROM mentions")
        final_count = cursor.fetchone()[0]
        
        print(f"Removed {deleted_count} duplicates.")
        print(f"Final row count: {final_count}")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    remove_duplicates()
