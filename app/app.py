import re
import streamlit as st
import pandas as pd
import plotly.express as px
from plotly import graph_objs as go
import time
import sys
import os
import random

# Add project root to path FIRST, before any local (data./models.) imports,
# so they resolve correctly regardless of Streamlit Cloud's working directory.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Access secrets safely (st.secrets raises if no secrets.toml file exists at all,
# so we guard with try/except instead of relying on dict.get alone)
try:
    reddit_config = {
        'client_id': st.secrets.get("reddit", {}).get("client_id", ""),
        'client_secret': st.secrets.get("reddit", {}).get("client_secret", ""),
        'user_agent': st.secrets.get("reddit", {}).get("user_agent", "slang_tracker_v1")
    }
except Exception:
    reddit_config = {'client_id': "", 'client_secret': "", 'user_agent': "slang_tracker_v1"}

# Fallback scraper (used when no Reddit API credentials are configured)
from data.no_api_scraper import scrape_word

st.set_page_config(page_title="Slang Life Tracker", layout="wide")

# Poppy & Bubbly / Neubrutalist Styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@300;400;600&display=swap');
    @import url('https://fonts.cdnfonts.com/css/butler'); /* Fabian De Smet's Butler Font */

    /* Main Background - Navy */
    .stApp {
        background-color: #25344F; 
        font-family: 'Fredoka', sans-serif;
        color: #D5B893;
    }

    /* Bubble Cards - Brown with Beige Border */
    .bubble-card {
        background-color: #6F4D38;
        border: 2px solid #D5B893;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 5px 5px 0px #1a253a; /* Darker Navy shadow */
        margin-bottom: 20px;
        color: #D5B893;
    }

    /* Headings - Beige - Butler (High Contrast Serif) */
    h1, h2, h3, h4, h5, h6 {
        color: #D5B893 !important; 
        font-family: 'Butler', 'Playfair Display', serif;
        font-weight: 700;
        text-transform: uppercase;
        text-shadow: none;
    }

    /* Metrics */
    div[data-testid="stMetricValue"] {
        color: #D5B893 !important;
        font-family: 'Fredoka', sans-serif;
        font-weight: 600;
    }
    div[data-testid="stMetricLabel"] {
        color: #617891 !important; /* Slate */
        font-weight: bold;
    }

    /* Buttons - Burgundy with Beige Text */
    div.stButton > button {
        background-color: #632024; 
        color: #D5B893;
        border: 2px solid #D5B893;
        border-radius: 5px; 
        font-family: 'Fredoka', sans-serif;
        font-weight: bold;
        font-size: 18px;
        padding: 10px 30px;
        box-shadow: 4px 4px 0px #1a253a;
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        background-color: #D5B893; 
        color: #25344F; /* Navy Text */
        transform: translate(-1px, -1px);
        box-shadow: 6px 6px 0px #1a253a;
        border-color: #632024;
    }
    div.stButton > button:active {
        transform: translate(2px, 2px);
        box-shadow: 1px 1px 0px #1a253a;
    }

    /* Inputs - Slate Background */
    .stTextInput > div > div > input {
        background-color: #617891;
        color: #D5B893;
        border: 2px solid #D5B893;
        border-radius: 10px;
        font-family: 'Fredoka', sans-serif;
        padding-left: 15px;
    }
    /* Input Label */
    .stTextInput label {
        color: #D5B893 !important;
    }

    /* Sidebar - Slate */
    section[data-testid="stSidebar"] {
        background-color: #617891; 
        border-right: 2px solid #25344F;
    }
    
    /* Info Box Styling (Streamlit's st.info) */
    .stAlert {
        background-color: #6F4D38;
        color: #D5B893;
        border: 1px solid #D5B893;
    }

    /* Mobile Responsiveness */
    @media (max-width: 768px) {
        /* Reduce main container padding */
        .block-container {
            padding-top: 3rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        
        /* Adjust headings */
        h1 { font-size: 2.2rem !important; }
        h2 { font-size: 1.8rem !important; }
        h3 { font-size: 1.4rem !important; }
        
        /* Compact cards */
        .bubble-card {
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 3px 3px 0px #1a253a;
        }
        .bubble-card:hover {
            transform: none; /* Disable hover effect on touch */
            box-shadow: 3px 3px 0px #1a253a;
        }
        
        /* Full width buttons */
        div.stButton > button {
            width: 100%;
            margin-bottom: 10px;
            font-size: 16px;
        }
        
        /* Adjust metrics */
        div[data-testid="stMetricValue"] {
            font-size: 1.8rem !important;
        }
        
        /* Hide complex decoration if needed or adjust badges */
        .badge {
            padding: 3px 10px;
            font-size: 0.8rem;
        }
        
        /* Adjust chart margins */
        .js-plotly-plot {
            margin-left: -10px !important; 
            margin-right: -10px !important;
        }
    }

    </style>
""", unsafe_allow_html=True)

st.title("Slang Life Tracker")

# ... (Previous imports and setup remain similar)

# Initialize Session State
if 'searched' not in st.session_state:
    st.session_state.searched = False
if 'target_word' not in st.session_state:
    st.session_state.target_word = "aura"

# Sidebar setup happens below (single, validated implementation)

from models.lifecycle_engine import LifecycleEngine
from models.analyzer import SlangAnalyzer
lifecycle = LifecycleEngine()

def validate_slang_word(word: str) -> tuple[bool, str]:
    """
    Validate user input word.
    
    Returns:
        (is_valid, error_message)
    """
    # Remove whitespace
    word = word.strip().lower()
    
    # Check if empty
    if not word:
        return False, "Please enter a word"
    
    # Check length
    if len(word) > 50:
        return False, "Word too long (max 50 characters)"
    
    # Check format (alphanumeric + hyphens/spaces only)
    if not re.match(r'^[a-z0-9\s\-]{1,50}$', word):
        return False, "Invalid format. Use letters, numbers, hyphens, and spaces only"
    
    return True, ""

# Sidebar
with st.sidebar:
    st.header("Controls")
    with st.form(key="search_form"):
        target_word_input = st.text_input("Pop a Word", value=st.session_state.target_word)
        submitted = st.form_submit_button("Uncover Truth")

    if submitted:
        is_valid, error_msg = validate_slang_word(target_word_input)
        if is_valid:
            st.session_state.searched = True
            st.session_state.target_word = target_word_input.strip().lower()
        else:
            st.error(error_msg)

    st.markdown("---")
    st.caption("From the 1600s to 2026\nTracking Linguistic Evolution")

# Main App Logic
if st.session_state.searched:
    target_word = st.session_state.target_word
    with st.spinner(f"Tracking '{target_word}'..."):

        # Pull the archive record (definition / category) regardless of
        # whether we have time-series mention history yet.
        data, source = lifecycle.get_slang_data(target_word)

        # Make sure today's mention counts are recorded so the line chart
        # has fresh data even for a brand-new search. This is on-demand,
        # supplementing the daily history the scheduled auto-updater builds.
        try:
            scrape_word(target_word)
        except Exception:
            pass  # Network may be unavailable; fall back to whatever history exists.

        if data:
            st.title(f" {data['word']}")
            st.caption(f"Category: {data['category']} | Source: {source}")

            st.subheader("Definition")
            st.info(data['meaning'])

            # CULTURAL WAVE — a deterministic curve from this word's own
            # documented origin era to its current 2026 status. Rebuilt to
            # use only real archive fields (no random numbers, no unrelated
            # words) after the original version was found to be decorative
            # placeholder data.
            st.markdown("---")
            st.subheader("The Cultural Wave (Origin → 2026)")

            wave_data = lifecycle.get_timeline_data(target_word)
            if wave_data:
                years = [p['year'] for p in wave_data['points']]
                heights = [p['height'] for p in wave_data['points']]

                wave_status_colors = {
                    'Niche': '#617891', 'Unverified': '#617891', 'Emerging': '#D5B893',
                    'Peak': '#D5B893', 'Mainstream': '#D5B893', 'Cringe': '#632024',
                }
                wave_marker_color = wave_status_colors.get(wave_data['status'], '#D5B893')

                wave_fig = go.Figure()
                wave_fig.add_trace(go.Scatter(
                    x=years, y=heights,
                    mode='lines',
                    line=dict(width=2, color='#D5B893', shape='spline', smoothing=1.0),
                    fill='tozeroy',
                    fillcolor='rgba(213, 184, 147, 0.15)',
                    hovertemplate="Year: %{x}<br>Relative usage: %{y:.0%}<extra></extra>",
                ))
                wave_fig.add_trace(go.Scatter(
                    x=[years[-1]], y=[heights[-1]],
                    mode='markers+text',
                    text=[wave_data['status']],
                    textposition="top center",
                    textfont=dict(size=13, color='#D5B893'),
                    marker=dict(size=14, color=wave_marker_color, line=dict(width=2, color='#25344F')),
                    hoverinfo='skip',
                ))
                year_span = years[-1] - years[0]
                if year_span <= 5:
                    dtick = 1
                elif year_span <= 30:
                    dtick = 5
                elif year_span <= 100:
                    dtick = 20
                else:
                    dtick = 50

                wave_fig.update_layout(
                    xaxis=dict(
                        title=f"From {wave_data['origin_year']} to 2026", color="#D5B893",
                        showgrid=False, fixedrange=True,
                        tickformat="d", separatethousands=False, dtick=dtick,
                    ),
                    yaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=[0, 1.1], fixedrange=True),
                    height=300,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=False,
                    margin=dict(t=10, b=0, l=0, r=0),
                )
                st.plotly_chart(wave_fig, width='stretch', config={'displayModeBar': False})
                st.caption(
                    "Illustrative trajectory from this word's documented origin era to its "
                    "current archive status — not a measured historical count."
                )
            else:
                st.info("No origin data available to plot a trajectory for this word.")

            st.markdown("---")
            st.subheader("Niche vs. Mainstream Popularity")

            analyzer = SlangAnalyzer()
            analysis = analyzer.analyze_word(target_word)

            if analysis is not None:
                hist_df = analysis['historical']
                metrics = analysis['metrics']
                cringe_alert = analysis['cringe_alert']

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=hist_df['date'], y=hist_df['niche'],
                    mode='lines+markers', name='Niche',
                    line=dict(color='#617891', width=3)
                ))
                fig.add_trace(go.Scatter(
                    x=hist_df['date'], y=hist_df['mainstream'],
                    mode='lines+markers', name='Mainstream',
                    line=dict(color='#632024', width=3)
                ))
                fig.update_layout(
                    xaxis=dict(title="Date", color="#D5B893", showgrid=False),
                    yaxis=dict(title="Mentions / day", color="#D5B893", showgrid=False),
                    height=400,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    legend=dict(font=dict(color="#D5B893")),
                    margin=dict(t=20, b=0, l=0, r=0)
                )
                st.plotly_chart(fig, width='stretch', config={'displayModeBar': False})

                # Cringe Threshold status, derived from real growth-rate comparison
                # (not a static category lookup).
                if cringe_alert:
                    threshold_status = "Cringe Threshold Crossed"
                    color = "#632024"
                elif metrics['mainstream_growth'] > 0 and metrics['niche_growth'] <= metrics['mainstream_growth']:
                    threshold_status = "Approaching Cringe Threshold"
                    color = "#D5B893"
                else:
                    threshold_status = "Still Niche"
                    color = "#617891"

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Cringe Threshold", threshold_status)
                with col2:
                    st.metric("Mainstream Growth", f"{metrics['mainstream_growth']*100:.1f}%")
                with col3:
                    st.metric("Niche Growth", f"{metrics['niche_growth']*100:.1f}%")
            else:
                st.info(
                    "No usage history yet for this word — mention tracking just started. "
                    "Check back after the next scheduled update, or this word will accumulate "
                    "history the more it's searched and tracked."
                )
        else:
            st.error("404 Coded. This word has transcended our database.")

else:
    # LANDING PAGE STATE
    st.title("Welcome to the SlangVerse")
    st.markdown("### Don't let your vocabulary flop.")
    st.info("**Tip:** Search for 'aura', 'cooked', or 'peng' to see niche vs. mainstream trends.")

st.markdown("---")
# Footer moved to Sidebar roughly, or just kept here if Sidebar is too crowded.
# User said "not visible", likely meaning they didn't scroll down.
# But keeping it consistent.