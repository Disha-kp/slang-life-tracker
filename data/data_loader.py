import pandas as pd
import sqlite3
from pathlib import Path
from app.logger import get_logger

logger = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

class DataLoader:
    def __init__(self, db_path: str = None):
        # Relative paths (e.g. the "test.db" used by tests) are kept relative
        # on purpose; only the default falls back to an absolute, project-root
        # anchored path so it works regardless of the process's cwd.
        if db_path is None:
            db_path = str(_PROJECT_ROOT / "data" / "slang_data.db")
        self.db_path = Path(db_path)
        self.ensure_db_exists()
    
    def ensure_db_exists(self):
        """Create database and tables if they don't exist."""
        try:
            if not self.db_path.exists():
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created database at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to create database: {e}")
            raise
    
    def load_slang_data(self) -> pd.DataFrame:
        """Load slang data from CSV with validation."""
        try:
            csv_path = _PROJECT_ROOT / "data" / "slang_2026_master.csv"
            
            # Check file exists
            if not csv_path.exists():
                logger.warning(f"CSV not found at {csv_path}")
                return pd.DataFrame()
            
            # Load with error handling
            df = pd.read_csv(csv_path, encoding='utf-8')
            
            # Validate
            if df.empty:
                logger.warning("Loaded CSV is empty")
                return df
            
            # Check required columns
            required_cols = ['word', 'meaning', 'status_2026', 'origin_era']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                logger.error(f"Missing columns: {missing_cols}")
                raise ValueError(f"CSV missing columns: {missing_cols}")
            
            # Remove duplicates
            df = df.drop_duplicates(subset=['word'], keep='first')
            
            logger.info(f"Loaded {len(df)} slang entries")
            return df
            
        except pd.errors.EmptyDataError:
            logger.error("CSV file is empty")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            raise
    
    def query_database(self, query: str, params: tuple = ()) -> list:
        """Execute database query with error handling."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            cursor = conn.cursor()
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            conn.close()
            return results
            
        except sqlite3.OperationalError as e:
            logger.error(f"Database error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return []