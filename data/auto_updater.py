"""
Automatic Slang Database Updater
---------------------------------
Periodically discovers new candidate slang words from Reddit (niche
subreddits especially), scores them with the existing slang-detection
heuristic, estimates a lifecycle status, and appends genuinely new
entries to data/slang_master_2026.csv.

Designed to be run:
  - Manually:    python data/auto_updater.py
  - On a schedule: see .github/workflows/update-slang-db.yml

It deliberately never *removes* or *overwrites* existing rows — only
appends new, deduplicated entries — so it's safe to re-run repeatedly.
"""

import csv
import os
import re
import sys
from collections import Counter
from datetime import datetime

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from data.no_api_scraper import fetch_reddit_data, SUBREDDITS, PENDING_WORDS_PATH  # noqa: E402
from data.urban_dictionary import fetch_definition as fetch_ud_definition  # noqa: E402
from models.slang_detector import is_slang  # noqa: E402
from models.analyzer import SlangAnalyzer  # noqa: E402

CSV_PATH = os.path.join(_PROJECT_ROOT, "data", "slang_master_2026.csv")

# Common English words / Reddit boilerplate to never flag as "new slang",
# even if they pass the heuristic (keeps noise out of the CSV).
STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "her",
    "was", "one", "our", "out", "day", "get", "has", "him", "his", "how",
    "man", "new", "now", "old", "see", "two", "way", "who", "boy", "did",
    "its", "let", "put", "say", "she", "too", "use", "this", "that", "with",
    "have", "from", "they", "will", "what", "when", "your", "just", "into",
    "post", "comment", "reddit", "thread", "deleted", "removed", "edit",
    "https", "http", "www", "com",
}

MIN_WORD_LEN = 3
MAX_WORD_LEN = 20
MIN_MENTIONS_TO_QUALIFY = 2  # how many times a word must appear before we consider it


def load_known_words() -> set:
    """Read the existing CSV and return the set of already-known words (lowercased)."""
    known = set()
    if not os.path.exists(CSV_PATH):
        return known
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            w = row.get("word", "").strip().lower()
            if w:
                known.add(w)
    return known


def extract_candidate_words(text: str) -> list:
    """Pull plausible slang candidate tokens out of a chunk of text."""
    tokens = re.findall(r"[a-zA-Z']+", text.lower())
    candidates = []
    for tok in tokens:
        tok = tok.strip("'")
        if MIN_WORD_LEN <= len(tok) <= MAX_WORD_LEN and tok not in STOPWORDS:
            candidates.append(tok)
    return candidates


def load_pending_words() -> list:
    """Words real users searched for that Deep Search couldn't resolve live."""
    if not os.path.exists(PENDING_WORDS_PATH):
        return []
    with open(PENDING_WORDS_PATH, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def clear_pending_words():
    if os.path.exists(PENDING_WORDS_PATH):
        os.remove(PENDING_WORDS_PATH)


def resolve_pending_words(known_words: set) -> list:
    """
    Specifically (re)search every word a live user looked up but Deep Search
    couldn't find anything for. This runs with full internet access and no
    UI timeout pressure, so it can afford to be much more thorough than a
    live request — checking every configured subreddit individually.
    """
    pending = load_pending_words()
    if not pending:
        return []

    print(f"Found {len(pending)} pending word(s) from failed live searches: {pending}")
    analyzer = SlangAnalyzer()
    current_year = datetime.now().year
    new_entries = []

    for word in pending:
        if word in known_words:
            continue

        niche_count, mainstream_count, sample_context, sample_sub = 0, 0, "", ""
        for sub in SUBREDDITS["niche"]:
            results = fetch_reddit_data(sub, word, is_mainstream=False)
            niche_count += len(results)
            if results and not sample_context:
                sample_context, sample_sub = results[0][3], sub
        for sub in SUBREDDITS["mainstream"]:
            results = fetch_reddit_data(sub, word, is_mainstream=True)
            mainstream_count += len(results)
            if results and not sample_context:
                sample_context, sample_sub = results[0][3], sub

        total_mentions = niche_count + mainstream_count
        if total_mentions < MIN_MENTIONS_TO_QUALIFY or not sample_context:
            continue

        verdict = is_slang(word, sample_context, sample_sub)
        if not verdict["is_slang"]:
            continue

        cringe_score = analyzer.calculate_cringe_score(
            niche_usage=niche_count, mainstream_usage=mainstream_count
        )
        status = analyzer.detect_lifecycle_status(cringe_score)

        ud_definition = fetch_ud_definition(word)
        if ud_definition:
            meaning = ud_definition
            category = "Slang (Urban Dictionary)"
        else:
            context = sample_context.replace("\n", " ").strip()
            if len(context) > 150:
                context = context[:147] + "..."
            meaning = f"Auto-detected from Reddit usage. Context: \"{context}\""
            category = "Auto-Detected"

        new_entries.append({
            "word": word,
            "meaning": meaning,
            "origin_era": f"{current_year} (Auto-Detected)",
            "category": category,
            "2026_status": status,
        })

    return new_entries


def discover_candidates(sample_words=None, max_posts_per_sub=50):
    """
    Scan configured niche/mainstream subreddits for trending terms.

    Args:
        sample_words: optional seed list of words to specifically search for
            (in addition to general frequency scanning). If None, scans
            r/all-style general activity using a small set of seed terms.
        max_posts_per_sub: cap on posts fetched per subreddit/search call.

    Returns:
        dict: word -> {
            'niche_count': int, 'mainstream_count': int,
            'sample_context': str, 'sample_subreddit': str
        }
    """
    seed_terms = sample_words or ["slang", "trend", "vibe", "viral"]
    stats = {}

    def scan(sub, keyword, is_mainstream):
        results = fetch_reddit_data(sub, keyword, is_mainstream=is_mainstream)
        for _id, _kw, subreddit, content, _ts, mainstream in results[:max_posts_per_sub]:
            for word in extract_candidate_words(content):
                entry = stats.setdefault(
                    word,
                    {"niche_count": 0, "mainstream_count": 0,
                     "sample_context": content, "sample_subreddit": subreddit},
                )
                if mainstream:
                    entry["mainstream_count"] += 1
                else:
                    entry["niche_count"] += 1

    for term in seed_terms:
        for sub in SUBREDDITS["niche"]:
            scan(sub, term, is_mainstream=False)
        for sub in SUBREDDITS["mainstream"]:
            scan(sub, term, is_mainstream=True)

    return stats


def build_new_entries(stats: dict, known_words: set) -> list:
    """Filter discovered candidates down to genuinely new, slang-like entries."""
    analyzer = SlangAnalyzer()
    new_entries = []
    current_year = datetime.now().year

    for word, info in stats.items():
        if word in known_words:
            continue

        total_mentions = info["niche_count"] + info["mainstream_count"]
        if total_mentions < MIN_MENTIONS_TO_QUALIFY:
            continue

        verdict = is_slang(word, info["sample_context"], info["sample_subreddit"])
        if not verdict["is_slang"]:
            continue

        cringe_score = analyzer.calculate_cringe_score(
            niche_usage=info["niche_count"], mainstream_usage=info["mainstream_count"]
        )
        status = analyzer.detect_lifecycle_status(cringe_score)

        ud_definition = fetch_ud_definition(word)
        if ud_definition:
            meaning = ud_definition
            category = "Slang (Urban Dictionary)"
        else:
            context = info["sample_context"].replace("\n", " ").strip()
            if len(context) > 150:
                context = context[:147] + "..."
            meaning = f"Auto-detected from Reddit usage. Context: \"{context}\""
            category = "Auto-Detected"

        new_entries.append({
            "word": word,
            "meaning": meaning,
            "origin_era": f"{current_year} (Auto-Detected)",
            "category": category,
            "2026_status": status,
        })

    return new_entries


def append_to_csv(new_entries: list):
    """Append new rows to the CSV, creating it with headers if it doesn't exist."""
    if not new_entries:
        print("No new slang words to add. Database is up to date.")
        return

    file_exists = os.path.exists(CSV_PATH)
    fieldnames = ["word", "meaning", "origin_era", "category", "2026_status"]

    with open(CSV_PATH, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for entry in new_entries:
            writer.writerow(entry)

    print(f"Added {len(new_entries)} new word(s) to {CSV_PATH}:")
    for e in new_entries:
        print(f"  - {e['word']} ({e['2026_status']})")


MENTIONS_HISTORY_PATH = os.path.join(_PROJECT_ROOT, "data", "mentions_history.csv")
MAX_WORDS_PER_RUN = 150  # cap daily request volume to stay well within rate limits


def collect_daily_mentions(known_words: set):
    """
    Record today's niche/mainstream mention counts for every known word into
    a git-tracked history CSV.

    Why a CSV and not the SQLite 'mentions' table: *.db files are gitignored
    (regenerated fresh on each container/run), and both Streamlit Cloud and
    GitHub Actions start from a clean checkout every time. Without a
    git-committed file, "today's" counts would be silently discarded and the
    niche-vs-mainstream line chart could never build real history over time.
    This function is what actually makes that chart meaningful day over day.
    """
    today = datetime.now().strftime("%Y-%m-%d")

    already_done_today = set()
    if os.path.exists(MENTIONS_HISTORY_PATH):
        with open(MENTIONS_HISTORY_PATH, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("date") == today:
                    already_done_today.add(row.get("word", "").strip().lower())

    words_to_scan = sorted(w for w in known_words if w not in already_done_today)[:MAX_WORDS_PER_RUN]
    if not words_to_scan:
        print("Mention history already up to date for today.")
        return

    print(f"Collecting today's mention counts for {len(words_to_scan)} word(s)...")
    file_exists = os.path.exists(MENTIONS_HISTORY_PATH)
    fieldnames = ["date", "word", "niche_count", "mainstream_count"]

    with open(MENTIONS_HISTORY_PATH, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        for word in words_to_scan:
            niche_count = sum(
                len(fetch_reddit_data(sub, word, is_mainstream=False))
                for sub in SUBREDDITS["niche"]
            )
            mainstream_count = sum(
                len(fetch_reddit_data(sub, word, is_mainstream=True))
                for sub in SUBREDDITS["mainstream"]
            )
            writer.writerow({
                "date": today,
                "word": word,
                "niche_count": niche_count,
                "mainstream_count": mainstream_count,
            })

    print(f"Recorded mention history for {len(words_to_scan)} word(s) on {today}.")


def main():
    print(">>> AUTO UPDATER: Discovering new slang candidates...")
    known_words = load_known_words()
    print(f"Loaded {len(known_words)} known words from archive.")

    # Step 1: resolve words that live users searched for but Deep Search
    # couldn't find anything on (the highest-value, demand-driven entries).
    pending_entries = resolve_pending_words(known_words)
    if pending_entries:
        append_to_csv(pending_entries)
        known_words.update(e["word"] for e in pending_entries)
    clear_pending_words()

    # Step 2: general discovery scan across seed terms for organic trends.
    stats = discover_candidates()
    print(f"Scanned {len(stats)} candidate words across configured subreddits.")

    new_entries = build_new_entries(stats, known_words)
    append_to_csv(new_entries)
    known_words.update(e["word"] for e in new_entries)

    # Step 3: record today's niche/mainstream counts for every known word,
    # building the persistent history the line chart depends on.
    collect_daily_mentions(known_words)

    print(">>> AUTO UPDATER: Done.")


if __name__ == "__main__":
    main()
