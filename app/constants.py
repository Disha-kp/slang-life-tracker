"""Application constants and configuration."""

import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Cringe Score Levels
CRINGE_LEVELS = {
    "Niche": 10,
    "Peak": 50,
    "Mainstream": 50,
    "Cringe": 100
}

# Status Colors
STATUS_COLORS = {
    "Niche": "#617891",      # Slate
    "Peak": "#D5B893",       # Beige
    "Mainstream": "#D5B893", # Beige
    "Cringe": "#632024"      # Burgundy
}

# Timeline Configuration
TIMELINE_START_YEAR = 1600
TIMELINE_END_YEAR = 2026

# Database Configuration
DB_PATH = os.path.join(_PROJECT_ROOT, "data", "slang_data.db")
BACKUP_PATH = os.path.join(_PROJECT_ROOT, "data", "backups")

# Cache Configuration
CACHE_TTL = 3600  # 1 hour in seconds
CACHE_MAX_SIZE = 256

# Rate Limiting
RATE_LIMIT_CALLS = 1
RATE_LIMIT_PERIOD = 2  # seconds

# Scraper Configuration
SCRAPER_TIMEOUT = 10
SCRAPER_RETRIES = 3

# UI Configuration
PAGE_CONFIG = {
    "page_title": "Slang Life Tracker",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# Color Palette
COLORS = {
    "navy": "#25344F",
    "slate": "#617891",
    "brown": "#6F4D38",
    "beige": "#D5B893",
    "burgundy": "#632024"
}

# Fonts
FONTS = {
    "serif": "Butler, Playfair Display, serif",
    "sans": "Fredoka, sans-serif"
}