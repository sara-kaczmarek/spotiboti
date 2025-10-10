import streamlit as st
import pandas as pd
import json
import os
import sys
sys.path.append('..')
from shared_components import render_footer

st.title("🎵 Song Analysis")

st.markdown("""
## 🚧 Coming Soon!

The Song Analysis page will soon let you:

- Select any song from your Spotify history
- See play stats (total plays, hours, first/last play)
- View audio features (danceability, energy, valence, tempo, etc.)
- Visualize features with charts
- Compare songs and artists
- And more!

Stay tuned for updates!
""")

render_footer()
