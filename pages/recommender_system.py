import streamlit as st
import pandas as pd
import json
import os
import sys
sys.path.append('..')
from shared_components import render_footer

st.title("<¯ Recommender System")

st.markdown("""
## =§ Coming Soon!

The Recommender System page will soon let you:

- Get personalized music recommendations based on your listening history
- Discover new artists similar to your favorites
- Find hidden gems you might have missed
- Get mood-based recommendations
- Explore different genres
- And more!

Stay tuned for updates!
""")

render_footer()