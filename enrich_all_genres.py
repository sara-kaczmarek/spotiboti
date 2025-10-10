#!/usr/bin/env python3
"""
One-time script to fetch genres for ALL your Spotify history and save it permanently.
Run this once, then you'll never need to fetch genres again!
"""

import pandas as pd
import json
import glob
import os
from datetime import datetime
import streamlit as st
from spotify_api import SpotifyAPI

def load_all_spotify_data():
    """Load all Spotify data from JSON files"""
    data_dir = '/Users/sarakaczmarek/Desktop/Spotify/streaming_data'
    audio_files = glob.glob(os.path.join(data_dir, 'Streaming_History_Audio_*.json'))

    print(f"Found {len(audio_files)} JSON files")

    all_streams = []
    for i, file in enumerate(audio_files):
        print(f"Loading file {i+1}/{len(audio_files)}: {os.path.basename(file)}")
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            all_streams.extend(data)

    print(f"Loaded {len(all_streams)} total tracks")

    # Convert to DataFrame
    df = pd.DataFrame(all_streams)
    df['ts'] = pd.to_datetime(df['ts'])

    # Filter short plays
    df_filtered = df[df['ms_played'] >= 30000].copy()
    print(f"After filtering short plays: {len(df_filtered)} tracks")

    return df_filtered

def enrich_and_save(df, spotify_api, output_file='data/enriched_spotify_data.json'):
    """Enrich data with genres and save to file"""
    print(f"\n🎵 Starting genre enrichment for {len(df)} tracks...")

    # Get unique artists to minimize API calls
    unique_artists = df['master_metadata_album_artist_name'].unique()
    print(f"Found {len(unique_artists)} unique artists")

    # Fetch genres for all unique artists
    artist_genres_map = {}
    for i, artist in enumerate(unique_artists):
        if i % 50 == 0:  # Progress update every 50 artists
            print(f"Processing artist {i+1}/{len(unique_artists)}: {artist}")

        genres = spotify_api.get_artist_genres(artist)
        artist_genres_map[artist] = ', '.join(genres) if genres else 'Unknown'

        # Small delay to avoid rate limiting
        import time
        time.sleep(0.1)

    print(f"✅ Fetched genres for {len(artist_genres_map)} artists")

    # Add genres to dataframe
    df['genres'] = df['master_metadata_album_artist_name'].map(artist_genres_map)

    # Save cache
    spotify_api.genre_cache.save_cache()
    print(f"💾 Saved genre cache with {len(spotify_api.genre_cache.cache)} artists")

    # Convert to JSON-serializable format and save
    df_dict = df.to_dict('records')

    print(f"💾 Saving enriched data to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(df_dict, f, indent=2, ensure_ascii=False, default=str)

    print(f"✅ Successfully saved {len(df_dict)} enriched tracks!")
    return df

def main():
    """Main function to enrich all data"""
    print("🎭 Spotify Genre Enrichment Tool")
    print("This will fetch genres for ALL your music history - run once!")
    print("=" * 60)

    # Get API credentials
    try:
        import streamlit as st
        st.secrets.load_if_toml_exists()
        client_id = st.secrets["SPOTIFY_CLIENT_ID"]
        client_secret = st.secrets["SPOTIFY_CLIENT_SECRET"]
        print("✅ Loaded API credentials from secrets.toml")
    except:
        print("❌ Could not load credentials from secrets.toml")
        print("Make sure your .streamlit/secrets.toml file exists with SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET")
        return

    # Initialize Spotify API
    spotify_api = SpotifyAPI(client_id=client_id, client_secret=client_secret)

    # Try to authenticate (should use cached token)
    try:
        if spotify_api.authenticate():
            print("✅ Authenticated with Spotify API")
        else:
            print("❌ Authentication failed")
            print("Make sure you've authenticated through the main app first")
            return
    except:
        print("❌ Authentication failed")
        return

    # Load all data
    print("\n📊 Loading your complete Spotify history...")
    df = load_all_spotify_data()

    # Check if already enriched
    if os.path.exists('data/enriched_spotify_data.json'):
        response = input("\n⚠️  data/enriched_spotify_data.json already exists. Overwrite? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return

    # Enrich with genres
    enriched_df = enrich_and_save(df, spotify_api)

    print("\n🎉 Genre enrichment complete!")
    print(f"📁 Your enriched data is saved in: data/enriched_spotify_data.json")
    print(f"🎵 Total tracks: {len(enriched_df)}")
    print(f"🎭 Unique genres found: {len([g for genres in enriched_df['genres'].unique() if genres != 'Unknown' for g in genres.split(', ')])}")
    print("\nYou can now use the genre analysis without any API calls!")

if __name__ == "__main__":
    main()