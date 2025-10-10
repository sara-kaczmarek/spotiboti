import os
import json
import pandas as pd
from spotify_api import SpotifyAPI
from tqdm import tqdm

# Load credentials from Streamlit secrets if available
try:
    import streamlit as st
    st.secrets.load_if_toml_exists()
    client_id = st.secrets["SPOTIFY_CLIENT_ID"]
    client_secret = st.secrets["SPOTIFY_CLIENT_SECRET"]
except Exception:
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")

if not client_id or not client_secret:
    print("❌ Spotify API credentials not found. Please set them in .streamlit/secrets.toml or as environment variables.")
    exit(1)

sp_api = SpotifyAPI(client_id=client_id, client_secret=client_secret)
if not sp_api.authenticate():
    print("❌ Spotify API authentication failed. Please authenticate first.")
    exit(1)

# Load your enriched or raw data
if os.path.exists("data/enriched_spotify_data.json"):
    with open("data/enriched_spotify_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    df = pd.DataFrame(data)
else:
    print("No data/enriched_spotify_data.json found. Please run your enrichment first.")
    exit(1)

# Get all unique (track, artist) pairs
tracks = df[['master_metadata_track_name', 'master_metadata_album_artist_name', 'spotify_track_uri']].drop_duplicates()
tracks = tracks[tracks['spotify_track_uri'].notna()]

print(f"Fetching audio features for {len(tracks)} unique tracks...")

features_list = []
for _, row in tqdm(tracks.iterrows(), total=len(tracks)):
    track_uri = row['spotify_track_uri']
    try:
        features = sp_api.sp.audio_features([track_uri])[0]
        if features:
            features_list.append({
                'spotify_track_uri': track_uri,
                **{k: features[k] for k in [
                    'danceability', 'energy', 'key', 'loudness', 'mode', 'speechiness',
                    'acousticness', 'instrumentalness', 'liveness', 'valence', 'tempo',
                    'duration_ms', 'time_signature']}
            })
    except Exception as e:
        print(f"Error fetching features for {track_uri}: {e}")

features_df = pd.DataFrame(features_list)

# Merge features into your main dataframe
if not features_df.empty:
    df = df.merge(features_df, on='spotify_track_uri', how='left')
    df.to_json("enriched_spotify_data_with_audio_features.json", orient="records", force_ascii=False)
    print("✅ Saved enriched_spotify_data_with_audio_features.json with audio features!")
else:
    print("No audio features were fetched. Check your track URIs and API access.")
