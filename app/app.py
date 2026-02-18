import streamlit as st
import pandas as pd
import plotly.express as px
from plotly import graph_objs as go
import time
import sys
import os
import random

# Add project root to path to import models
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# from models.analyzer import SlangAnalyzer
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

# Sidebar
with st.sidebar:
    st.header("Controls")
    # Bind text input to session state
    target_word_input = st.text_input("Pop a Word", value=st.session_state.target_word)
    analyze_btn = st.button("Uncover Truth")
    
    st.markdown("---")
    st.caption("From the 1600s to 2026\nTracking Linguistic Evolution")

if analyze_btn:
    st.session_state.searched = True
    st.session_state.target_word = target_word_input

# ... (Analyzer init remains)
from models.lifecycle_engine import LifecycleEngine
lifecycle = LifecycleEngine()

# ... (CSS remains)

# Main App Logic
if st.session_state.searched:
    # ... (Existing search logic with new Wave Graph)
    target_word = st.session_state.target_word
    with st.spinner(f" Traversing the Timeline for '{target_word}'..."):
        time.sleep(0.5)
        data, source = lifecycle.get_slang_data(target_word)
        
        if data:
            # ... (Header & Cringe Meter - Keep as is)
            st.title(f" {data['word']} ({data['origin_era']})")
            st.caption(f"Category: {data['category']} | Source: {source}")
            
            # Cringe Meter Logic
            status = data['status_2026']
            cringe_level = 0
            color = "green"
            
            if status == "Niche":
                cringe_level = 10
                color = "#617891" # Slate
            elif status == "Peak" or status == "Mainstream":
                cringe_level = 50
                color = "#D5B893" # Beige
            elif status == "Cringe":
                cringe_level = 100
                color = "#632024" # Burgundy
                
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.metric("Linguistic Status", status)
                st.write(f"**Cringe Meter:** {cringe_level}%")
                st.progress(cringe_level)
                
            with col2:
                st.subheader("Definition")
                st.info(data['meaning'])

            # WAVE GRAPH VISUALIZATION
            st.markdown("---")
            st.subheader("The Cultural Wave (1600 - 2026)")
            
            timeline_data = lifecycle.get_timeline_data(target_word)
            
            if timeline_data:
                target = timeline_data['target']
                anchors = timeline_data['anchors']
                
                # Sort by year for the wave to make sense
                all_points = anchors + [target]
                all_points.sort(key=lambda x: x['year'])
                
                names = [p['word'] for p in all_points]
                years = [p['year'] for p in all_points]
                
                # Generate Wave Heights
                # Target gets peak height (1.0), others random (0.3 - 0.7)
                import random
                heights = []
                colors = []
                sizes = []
                
                vintage_palette = ['#D5B893', '#617891', '#6F4D38', '#632024', '#FFFFFF']

                for p in all_points:
                    if p['word'] == target['word']:
                        heights.append(1.0)
                        colors.append(color) # Status color
                        sizes.append(40)
                    else:
                        heights.append(random.uniform(0.3, 0.7))
                        colors.append(random.choice(vintage_palette))
                        sizes.append(20)

                fig = go.Figure()
                
                # 1. The Wave (Area Chart)
                fig.add_trace(go.Scatter(
                    x=years, 
                    y=heights,
                    mode='lines',
                    line=dict(width=0, shape='spline', smoothing=1.3),
                    fill='tozeroy',
                    fillcolor='rgba(213, 184, 147, 0.2)', # Beige low opacity
                    hoverinfo='skip'
                ))

                # 2. The Peaks (Markers)
                fig.add_trace(go.Scatter(
                    x=years, 
                    y=heights,
                    mode='markers+text',
                    text=names,
                    textposition="top center",
                    textfont=dict(size=14, color='white', family="Courier New"),
                    marker=dict(
                        size=sizes, 
                        color=colors, 
                        line=dict(width=2, color='#25344F'),
                        opacity=1.0
                    ),
                    hoverinfo='text+x',
                    hovertext=[f"{n} ({y})" for n, y in zip(names, years)]
                ))
                
                fig.update_layout(
                    title="Contextual Peaks",
                    title_font=dict(size=20, color="#D5B893"),
                    xaxis=dict(
                        title="Time-Space Continuum", 
                        range=[1600, 2030], 
                        showgrid=False,
                        color="#D5B893",
                        fixedrange=True
                    ),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, 1.3], fixedrange=True),
                    height=400,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=False,
                    margin=dict(t=50, b=0, l=0, r=0)
                )
                
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            else:
                 st.info("Timeline unavailable.")
        else:
            st.error("404 Coded. This word has transcended our database.")

else:
    # LANDING PAGE STATE
    st.title("Welcome to the SlangVerse")
    st.markdown("### Don't let your vocabulary flop.")
    
    # Show a random "Word of the Moment"
    st.info("**Tip:** Search for 'Rizz', 'Cooked', or go old school with 'Zounds'.")
    
    # Show a decorative random timeline immediately to populate the screen
    st.subheader("Random Context Trace")
    
    # Mock a random wave for visual interest
    random_target = "Rizz" # Default placeholder
    timeline_data = lifecycle.get_timeline_data(random_target)
    
    if timeline_data:
        target = timeline_data['target']
        anchors = timeline_data['anchors']
        all_points = anchors + [target]
        all_points.sort(key=lambda x: x['year'])
        
        names = [p['word'] for p in all_points]
        years = [p['year'] for p in all_points]
        heights = [random.uniform(0.3, 0.8) for _ in all_points]
        colors = ['#D5B893', '#617891', '#6F4D38', '#632024', '#FFFFFF'] * 2
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=years, y=heights, mode='lines', 
            line=dict(width=2, color='#D5B893', shape='spline'),
            fill='tozeroy', fillcolor='rgba(213, 184, 147, 0.1)'
        ))
        fig.add_trace(go.Scatter(
            x=years, y=heights, mode='markers',
            marker=dict(size=15, color=colors[:len(years)], line=dict(width=1, color='#25344F'))
        ))
        fig.update_layout(
             xaxis=dict(showgrid=False, showticklabels=False, fixedrange=True),
             yaxis=dict(showgrid=False, showticklabels=False, fixedrange=True),
             height=300,
             paper_bgcolor='rgba(0,0,0,0)',
             plot_bgcolor='rgba(0,0,0,0)',
             showlegend=False,
             margin=dict(t=0, b=0, l=0, r=0)
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

st.markdown("---")
# Footer moved to Sidebar roughly, or just kept here if Sidebar is too crowded.
# User said "not visible", likely meaning they didn't scroll down.
# But keeping it consistent.
