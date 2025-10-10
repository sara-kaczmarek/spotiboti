import streamlit as st
import sys
import os
sys.path.append('..')
from spotiboti import SpotifyChatbot
from shared_components import render_footer

# Get the parent directory path for logo access
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Page config
st.set_page_config(
    page_title="SpotiBoti - AI Music Assistant",
    page_icon="logo/spotiboti_no_text.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    # Custom CSS for SpotiBoti page
    st.markdown("""
    <style>
    .spotiboti-header {
        text-align: center;
        margin-top: -80px;
        margin-bottom: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # Large centered SpotiBoti logo at the top
    st.markdown('<div class="spotiboti-header">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1.5, 1, 1.5])
    with col2:
        st.image(os.path.join(parent_dir, "logo", "spotiboti_full_light.png"), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Initialize and render chatbot
    chatbot = SpotifyChatbot()
    chatbot.render_chat_interface()

    # Add footer
    render_footer()

if __name__ == "__main__":
    main()