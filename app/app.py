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

    /* Main Background */
    .stApp {
        background-color: #fdf6e3; /* Soft off-white */
        font-family: 'Fredoka', sans-serif;
    }

    /* Bubble Cards */
    .bubble-card {
        background-color: #ffffff;
        border: 3px solid #000000;
        border-radius: 25px;
        padding: 20px;
        box-shadow: 10px 10px 0px #000000;
        margin-bottom: 20px;
        transition: transform 0.2s;
    }
    .bubble-card:hover {
        transform: translate(-2px, -2px);
        box-shadow: 12px 12px 0px #000000;
    }

    /* Headings */
    h1, h2, h3 {
        color: #8A2BE2 !important; /* Electric Purple */
        font-family: 'Fredoka', sans-serif;
        font-weight: 700;
        text-transform: uppercase;
        text-shadow: 2px 2px 0px #FF69B4; /* Hot Pink Shadow */
    }

    /* Metrics using Streamlit's class usually needs inspection, 
       but we can wrap them in container divs or target generic classes if needed. 
       For now, targeting the metric label/value. */
    div[data-testid="stMetricValue"] {
        color: #000000 !important;
        font-family: 'Fredoka', sans-serif;
        font-weight: 600;
    }
    div[data-testid="stMetricLabel"] {
        color: #8A2BE2 !important;
        font-weight: bold;
    }

    /* Buttons - Pill Shaped & Pop */
    div.stButton > button {
        background-color: #00FFFF; /* Neon Cyan */
        color: #000000;
        border: 3px solid #000000;
        border-radius: 50px; /* Pill shape */
        font-family: 'Fredoka', sans-serif;
        font-weight: bold;
        font-size: 18px;
        padding: 10px 30px;
        box-shadow: 5px 5px 0px #000000;
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        background-color: #FF69B4; /* Hot Pink */
        color: #ffffff;
        transform: translate(-2px, -2px);
        box-shadow: 7px 7px 0px #000000;
        border-color: #000000;
    }
    div.stButton > button:active {
        transform: translate(2px, 2px);
        box-shadow: 2px 2px 0px #000000;
    }

    /* Inputs */
    .stTextInput > div > div > input {
        background-color: #ffffff;
        color: #000000;
        border: 3px solid #8A2BE2;
        border-radius: 50px;
        font-family: 'Fredoka', sans-serif;
        padding-left: 20px;
        box-shadow: 5px 5px 0px #000000;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #FFE4E1; /* Misty Rose */
        border-right: 3px solid #000000;
    }

    /* Custom Badges */
    .badge {
        display: inline-block;
        padding: 5px 15px;
        border-radius: 50px;
        border: 2px solid #000000;
        font-weight: bold;
        box-shadow: 3px 3px 0px #000000;
        margin-right: 10px;
    }
    .badge-fresh {
        background-color: #00FF7F; /* Spring Green */
        color: #000000;
    }
    .badge-cringe {
        background-color: #FF4500; /* Orange Red */
        color: #ffffff;
        animation: blink 1s infinite;
    }
    .badge-mainstream {
        background-color: #FFD700; /* Gold */
        color: #000000;
    }

    @keyframes blink {
        50% { opacity: 0.5; }
    }

    </style>
""", unsafe_allow_html=True)

st.title("🫧 Slang Life Tracker")

# ... (Previous imports and setup remain similar)

# Initialize Session State
if 'searched' not in st.session_state:
    st.session_state.searched = False
if 'target_word' not in st.session_state:
    st.session_state.target_word = "aura"

# Sidebar
with st.sidebar:
    st.header("🎛 Controls")
    # Bind text input to session state
    target_word_input = st.text_input("Pop a Word", value=st.session_state.target_word)
    analyze_btn = st.button("Uncover Truth")
    
    st.markdown("---")
    st.caption("📜 From the 1600s to 2026\nTracking Linguistic Evolution")

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
                color = "#00ffff" # Cyan
            elif status == "Peak" or status == "Mainstream":
                cringe_level = 50
                color = "#ff69b4" # Pink
            elif status == "Cringe":
                cringe_level = 100
                color = "#ff0000" # Red
                
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
            st.subheader("🌊 The Cultural Wave (1600 - 2026)")
            
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
                
                neon_palette = ['#FF6EC7', '#00FFFF', '#CCFF00', '#BF00FF', '#FF0000', '#FFFF00']

                for p in all_points:
                    if p['word'] == target['word']:
                        heights.append(1.0)
                        colors.append(color) # Status color
                        sizes.append(40)
                    else:
                        heights.append(random.uniform(0.3, 0.7))
                        colors.append(random.choice(neon_palette))
                        sizes.append(20)

                fig = go.Figure()
                
                # 1. The Wave (Area Chart)
                fig.add_trace(go.Scatter(
                    x=years, 
                    y=heights,
                    mode='lines',
                    line=dict(width=0, shape='spline', smoothing=1.3),
                    fill='tozeroy',
                    fillcolor='rgba(138, 43, 226, 0.2)', # Electric Purple low opacity
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
                        line=dict(width=2, color='white'),
                        opacity=1.0
                    ),
                    hoverinfo='text+x',
                    hovertext=[f"{n} ({y})" for n, y in zip(names, years)]
                ))
                
                fig.update_layout(
                    title="✨ Contextual Peaks ✨",
                    title_font=dict(size=20, color="#FF6EC7"),
                    xaxis=dict(
                        title="Time-Space Continuum", 
                        range=[1600, 2030], 
                        showgrid=False,
                        color="white"
                    ),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, 1.3]),
                    height=400,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=False,
                    margin=dict(t=50, b=0, l=0, r=0)
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                 st.info("Timeline unavailable.")
        else:
            st.error("404 Coded. This word has transcended our database.")

else:
    # LANDING PAGE STATE
    st.title("👋 Welcome to the SlangVerse")
    st.markdown("### Don't let your vocabulary flop.")
    
    # Show a random "Word of the Moment"
    st.info("💡 **Tip:** Search for 'Rizz', 'Cooked', or go old school with 'Zounds'.")
    
    # Show a decorative random timeline immediately to populate the screen
    st.subheader("🎲 Random Context Trace")
    
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
        colors = ['#FF6EC7', '#00FFFF', '#CCFF00', '#BF00FF', '#FF0000', '#FFFF00'] * 2
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=years, y=heights, mode='lines', 
            line=dict(width=2, color='#00FFFF', shape='spline'),
            fill='tozeroy', fillcolor='rgba(0, 255, 255, 0.1)'
        ))
        fig.add_trace(go.Scatter(
            x=years, y=heights, mode='markers',
            marker=dict(size=15, color=colors[:len(years)], line=dict(width=1, color='white'))
        ))
        fig.update_layout(
             xaxis=dict(showgrid=False, showticklabels=False),
             yaxis=dict(showgrid=False, showticklabels=False),
             height=300,
             paper_bgcolor='rgba(0,0,0,0)',
             plot_bgcolor='rgba(0,0,0,0)',
             showlegend=False,
             margin=dict(t=0, b=0, l=0, r=0)
        )
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
# Footer moved to Sidebar roughly, or just kept here if Sidebar is too crowded.
# User said "not visible", likely meaning they didn't scroll down.
# But keeping it consistent.
