import sqlite3
import os
from pathlib import Path
from app.logger import get_logger

logger = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = _PROJECT_ROOT / 'data' / 'slang_data.db'

def remove_duplicates():
    """Remove duplicate entries from database."""
    if not DB_PATH.exists():
        logger.error(f"Database not found at {DB_PATH}")
        return False

    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mentions'")
        if not cursor.fetchone():
            logger.warning("Table 'mentions' does not exist")
            conn.close()
            return False

        # Check initial count
        cursor.execute("SELECT COUNT(*) FROM mentions")
        initial_count = cursor.fetchone()[0]
        logger.info(f"Initial row count: {initial_count}")

        # Delete duplicates (keep the first occurrence)
        cursor.execute('''
            DELETE FROM mentions
            WHERE rowid NOT IN (
                SELECT MIN(rowid)
                FROM mentions
                GROUP BY content, subreddit
            )
        ''')
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        # Check final count
        cursor.execute("SELECT COUNT(*) FROM mentions")
        final_count = cursor.fetchone()[0]
        
        logger.info(f"Removed {deleted_count} duplicates (from {initial_count} to {final_count})")
        return True

    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = remove_duplicates()
    print("✅ Deduplication complete" if success else "❌ Deduplication failed")