"""
SlangAnalyzer
-------------
Provides two kinds of analysis:
1. Lookup / validation of slang words (used by integration tests and as a
   thin convenience wrapper around the CSV-seeded archive).
2. Growth/"cringe" analysis on historical mention data pulled from the
   `mentions` table that `data/no_api_scraper.py` populates.

Note: this module previously depended on the `prophet` package for
forecasting, which is not declared in requirements.txt and is not
installed in production. It has been replaced with a lightweight,
dependency-free linear trend estimate so the app/tests don't crash with
`ModuleNotFoundError: No module named 'prophet'`.
"""

import csv
import os
import re
import sqlite3
from typing import Any, Dict, Optional, Tuple

import pandas as pd

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("SLANG_DB_PATH", os.path.join(_PROJECT_ROOT, "data", "slang_data.db"))
CSV_PATH = os.path.join(_PROJECT_ROOT, "data", "slang_master_2026.csv")

_WORD_RE = re.compile(r"^[a-z0-9\s\-]{1,50}$")


class SlangAnalyzer:
    """Analyze slang terms for lifecycle status and growth trends."""

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path

    # ------------------------------------------------------------------
    # Lookup / validation
    # ------------------------------------------------------------------
    def _is_valid_word(self, word: str) -> bool:
        if word is None:
            return False
        cleaned = word.strip().lower()
        if not cleaned or len(cleaned) > 50:
            return False
        return bool(_WORD_RE.match(cleaned))

    def get_slang_data(self, word: str) -> Dict[str, Any]:
        """
        Look up a slang word in the seeded CSV archive.

        Returns an empty dict for invalid input (empty, too long, or
        containing characters outside [a-z0-9 -]) or when the word can't
        be found anywhere.
        """
        if not self._is_valid_word(word):
            return {}

        cleaned = word.strip().lower()

        if os.path.exists(CSV_PATH):
            with open(CSV_PATH, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row.get("word", "").strip().lower() == cleaned:
                        return {
                            "word": cleaned,
                            "meaning": row.get("meaning", ""),
                            "origin_era": row.get("origin_era", ""),
                            "category": row.get("category", ""),
                            "status_2026": row.get("2026_status", "Unverified"),
                        }

        # Not found in the archive: return a minimal placeholder record
        # instead of an empty dict, since the word itself was valid input.
        return {
            "word": cleaned,
            "meaning": "No archive entry found for this word yet.",
            "origin_era": "Unknown",
            "category": "Unknown",
            "status_2026": "Unverified",
        }

    # ------------------------------------------------------------------
    # Simple heuristic scoring (kept for backwards compatibility)
    # ------------------------------------------------------------------
    def calculate_cringe_score(self, niche_usage: int, mainstream_usage: int) -> float:
        """Calculate a cringe score (0-100) based on usage ratio."""
        if niche_usage == 0:
            return 0.0
        ratio = mainstream_usage / niche_usage
        return min(100.0, ratio * 50)

    def detect_lifecycle_status(self, cringe_score: float) -> str:
        """Map a cringe score (0-100) to a lifecycle status label."""
        if cringe_score < 20:
            return "Niche"
        elif cringe_score < 40:
            return "Peak"
        elif cringe_score < 80:
            return "Mainstream"
        else:
            return "Cringe"

    # ------------------------------------------------------------------
    # Mention-history based growth analysis
    # ------------------------------------------------------------------
    def get_data(self, word: str) -> pd.DataFrame:
        """
        Fetch daily mainstream/niche mention counts for a word, combining:
        1. The git-tracked history CSV (data/mentions_history.csv) built by
           the scheduled auto-updater — this is the real persistent record,
           since *.db files are gitignored and don't survive across restarts
           or fresh Action checkouts.
        2. Today's live SQLite 'mentions' table, in case the word was just
           searched on-demand and hasn't made it into a scheduled run yet.
        """
        word_lower = word.strip().lower()
        rows = []

        history_path = os.path.join(
            os.path.dirname(self.db_path), "mentions_history.csv"
        )
        if os.path.exists(history_path):
            hist = pd.read_csv(history_path)
            hist = hist[hist["word"].str.lower() == word_lower]
            for _, r in hist.iterrows():
                rows.append({"date": r["date"], "subreddit_type": "niche", "count": int(r["niche_count"])})
                rows.append({"date": r["date"], "subreddit_type": "mainstream", "count": int(r["mainstream_count"])})

        try:
            conn = sqlite3.connect(self.db_path)
            query = """
                SELECT
                    date(timestamp, 'unixepoch') as date,
                    CASE WHEN is_mainstream = 1 THEN 'mainstream' ELSE 'niche' END as subreddit_type,
                    COUNT(*) as count
                FROM mentions
                WHERE keyword = ?
                GROUP BY date, subreddit_type
            """
            live = pd.read_sql_query(query, conn, params=(word_lower,))
            rows.extend(live.to_dict("records"))
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        # Sum in case both sources have an entry for the same date.
        return df.groupby(["date", "subreddit_type"], as_index=False)["count"].sum()

    def process_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Pivot raw mention counts into a continuous daily time series."""
        if df.empty:
            return pd.DataFrame()

        pivot_df = df.pivot_table(
            index="date", columns="subreddit_type", values="count", fill_value=0
        ).reset_index()

        for col in ["mainstream", "niche"]:
            if col not in pivot_df.columns:
                pivot_df[col] = 0

        pivot_df["date"] = pd.to_datetime(pivot_df["date"])
        all_dates = pd.date_range(start=pivot_df["date"].min(), end=pivot_df["date"].max())
        pivot_df = (
            pivot_df.set_index("date")
            .reindex(all_dates, fill_value=0)
            .reset_index()
            .rename(columns={"index": "date"})
        )

        pivot_df["total"] = pivot_df["mainstream"] + pivot_df["niche"]
        pivot_df["ratio"] = (pivot_df["mainstream"] + 1) / (pivot_df["niche"] + 1)
        pivot_df["saturation"] = pivot_df["mainstream"] / (pivot_df["total"] + 1)

        return pivot_df

    @staticmethod
    def _linear_growth_rate(series: pd.Series) -> float:
        """
        Dependency-free replacement for the old Prophet-based forecast.
        Estimates the growth rate as the relative change implied by a
        simple linear fit over the available history.
        """
        n = len(series)
        if n < 2:
            return 0.0

        x = list(range(n))
        y = series.tolist()
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        denom = sum((xi - mean_x) ** 2 for xi in x)
        if denom == 0:
            return 0.0

        slope = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y)) / denom
        start_value = mean_y - slope * mean_x
        if start_value <= 0:
            return 0.0

        end_value = start_value + slope * (n - 1)
        return (end_value - start_value) / start_value

    def calculate_growth_rate(self, df: pd.DataFrame, column: str) -> float:
        """Estimate the growth rate of a column over the historical data."""
        if df is None or df.empty or column not in df.columns:
            return 0.0
        return self._linear_growth_rate(df[column])

    def analyze_word(self, word: str) -> Optional[Dict[str, Any]]:
        """Full mention-history analysis pipeline for a word."""
        raw_data = self.get_data(word)
        if raw_data.empty:
            return None

        hist_df = self.process_data(raw_data)
        if hist_df.empty:
            return None

        m_growth = self.calculate_growth_rate(hist_df, "mainstream")
        n_growth = self.calculate_growth_rate(hist_df, "niche")
        is_cringe_alert = self.check_cringe_alert(m_growth, n_growth)

        return {
            "historical": hist_df,
            "metrics": {
                "mainstream_growth": m_growth,
                "niche_growth": n_growth,
                "current_ratio": hist_df.iloc[-1]["ratio"],
                "saturation": hist_df.iloc[-1]["saturation"],
            },
            "cringe_alert": is_cringe_alert,
        }

    def check_cringe_alert(self, m_growth: float, n_growth: float) -> bool:
        """
        Alert if mainstream growth rate exceeds niche growth rate by 200%
        (i.e., mainstream growth > 3x niche growth).
        """
        if n_growth <= 0:
            # If niche is flat/dying, any significant mainstream growth is cringe.
            return m_growth > 0.1

        return m_growth > (n_growth + 2.0 * n_growth)


if __name__ == "__main__":
    analyzer = SlangAnalyzer()
    print("Analyzer initialized.")
