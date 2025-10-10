import streamlit as st
from shared_components import render_footer

class SpotifyApp:
    def __init__(self):
        # Page config
        st.set_page_config(
            page_title="Sara's Spotify",
            page_icon="logo/spotiboti_no_text.png",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        self.setup_styles()

    def setup_styles(self):
        # Custom CSS for better styling
        st.markdown("""
        <style>
        .main-header {
            font-size: 3rem;
            color: #1DB954;
            text-align: center;
            font-weight: bold;
            margin-bottom: 2rem;
        }
        .spotify-logo {
            text-align: center;
            margin: 2rem 0;
        }
        .navigation-card {
            background-color: #191414;
            padding: 2rem;
            border-radius: 20px;
            text-align: center;
            margin: 1rem;
            border: 2px solid #1DB954;
        }
        .navigation-card:hover {
            background-color: #1DB954;
            cursor: pointer;
        }
        .nav-button {
            background-color: #1DB954;
            color: white;
            padding: 1rem 2rem;
            border-radius: 50px;
            border: none;
            font-size: 1.2rem;
            font-weight: bold;
            margin: 1rem;
            cursor: pointer;
            width: 300px;
        }
        .nav-button:hover {
            background-color: #1ed760;
        }
        </style>
        """, unsafe_allow_html=True)

    def render_main_page(self):
        # Header
        st.markdown('<div class="main-header">Sara\'s Spotify</div>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: center; color: #b3b3b3; margin-top: -1rem;">Explore my personal music journey 🎵</p>', unsafe_allow_html=True)

        # Spotify Logo
        st.markdown("""
        <div class="spotify-logo">
            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/Spotify_logo_without_text.svg/512px-Spotify_logo_without_text.svg.png" width="150" alt="Spotify Icon">
        </div>
        """, unsafe_allow_html=True)

        # Navigation to other features
        st.markdown("<br><br>", unsafe_allow_html=True)

        # Feature navigation section
        st.markdown('<h3 style="text-align: center; color: #1DB954; margin-bottom: 1.5rem;">Explore My Music</h3>', unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("🤖 Chat with SpotiBoti", key="spotiboti_nav", help="Ask me anything about my music!", use_container_width=True):
                st.switch_page("pages/spotiboti.py")

        with col2:
            if st.button("📊 Streaming History", key="history_nav", help="Deep dive into my listening data", use_container_width=True):
                st.switch_page("pages/streaming_history.py")

        with col3:
            if st.button("🎵 Song Analysis", key="analysis_nav", help="Analyze individual tracks", use_container_width=True):
                st.switch_page("pages/song_analysis.py")

        with col4:
            if st.button("🎯 Get Recommendations", key="recs_nav", help="Discover new music", use_container_width=True):
                st.switch_page("pages/recommender_system.py")

        # Add footer
        render_footer()

def main():
    app = SpotifyApp()
    app.render_main_page()

if __name__ == "__main__":
    main()