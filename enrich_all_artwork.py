#!/usr/bin/env python3
"""
One-time script to fetch artwork for ALL your top tracks and save it permanently.
Run this once, then you'll never need to fetch artwork again!
"""

import pandas as pd
import json
import os
from datetime import datetime
import streamlit as st
from spotify_api import SpotifyAPI
from artwork_cache import ArtworkCache

def load_spotify_data():
    """Load Spotify data (enriched or regular)"""
    # Try enriched data first
    if os.path.exists('data/enriched_spotify_data.json'):
        print("📊 Loading enriched Spotify data...")
        with open('data/enriched_spotify_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        df['ts'] = pd.to_datetime(df['ts'])
        print(f"✅ Loaded {len(df)} enriched tracks")
        return df
    else:
        print("❌ No enriched data found. Please run genre enrichment first.")
        return None

def get_all_unique_tracks(df):
    """Get all unique tracks with sufficient play time"""
    if df is None:
        return []

    # Filter short plays
    df_filtered = df[df['ms_played'] >= 30000].copy()

    # Get all unique (track, artist) pairs
    unique_pairs = df_filtered.drop_duplicates(subset=['master_metadata_track_name', 'master_metadata_album_artist_name'])
    unique_tracks = list(zip(unique_pairs['master_metadata_track_name'], unique_pairs['master_metadata_album_artist_name']))
    return unique_tracks

def enrich_artwork(spotify_api, artwork_cache, top_tracks):
    """Enrich tracks with artwork from playlists and API searches"""
    print(f"🎨 Starting artwork enrichment for {len(top_tracks)} tracks...")

    # First, try to get artwork from playlists
    print("📂 Getting artwork from playlists...")

    # Get all playlists
    playlists_df = spotify_api.get_user_playlists()
    if playlists_df is None or playlists_df.empty:
        print("❌ No playlists found")
        return

    print(f"Found {len(playlists_df)} playlists")

    # Collect all tracks from all playlists
    all_playlist_tracks = {}

    for i, playlist in playlists_df.iterrows():
        print(f"Processing playlist {i+1}/{len(playlists_df)}: {playlist['name']}")

        playlist_tracks = spotify_api.get_playlist_tracks(playlist['playlist_id'], limit=100)
        if playlist_tracks is not None and not playlist_tracks.empty:
            for _, track in playlist_tracks.iterrows():
                track_key = f"{track['name'].lower().strip()}|||{track['artist'].lower().strip()}"
                if track_key not in all_playlist_tracks and pd.notna(track.get('album_image_url')):
                    all_playlist_tracks[track_key] = track['album_image_url']

    print(f"✅ Collected artwork for {len(all_playlist_tracks)} tracks from playlists")

    # Match with top tracks and cache
    found_in_playlists = 0
    not_found = []


    for track_name, artist_name in top_tracks:
        # Skip if track or artist is missing
        if not track_name or not artist_name:
            print(f"⚠️ Skipping track with missing name or artist: {track_name}, {artist_name}")
            continue

        track_key = artwork_cache.get_track_key(track_name, artist_name)

        # Check if already cached
        cached = artwork_cache.get_track_artwork(track_name, artist_name)
        if cached:
            continue

        # Try to find in playlist tracks
        if track_key in all_playlist_tracks:
            artwork_cache.set_track_artwork(track_name, artist_name, all_playlist_tracks[track_key])
            found_in_playlists += 1
        else:
            not_found.append((track_name, artist_name))

    print(f"✅ Found {found_in_playlists} tracks in playlists")
    print(f"🔍 Need to search API for {len(not_found)} tracks")


    # For tracks not found in playlists, make individual API searches with improved fallback and logging
    for i, (track_name, artist_name) in enumerate(not_found):
        print(f"\n🔍 Attempting to fetch artwork for: {track_name} by {artist_name} (#{i+1} of {len(not_found)})")
        found = False
        try:
            # 1. Try full query (track + artist)
            query = f"track:{track_name} artist:{artist_name}"
            results = spotify_api.sp.search(q=query, type='track', limit=1)
            if results['tracks']['items']:
                track = results['tracks']['items'][0]
                if track['album']['images']:
                    images = track['album']['images']
                    artwork_url = images[1]['url'] if len(images) >= 2 else images[0]['url']
                    artwork_cache.set_track_artwork(track_name, artist_name, artwork_url)
                    print(f"✅ Found artwork via full query: {artwork_url}")
                    found = True
            if not found:
                # 2. Try searching by track name only
                print("❌ No artwork with full query. Trying by track name only...")
                query = f"track:{track_name}"
                results = spotify_api.sp.search(q=query, type='track', limit=3)
                for t in results['tracks']['items']:
                    if t['album']['images']:
                        images = t['album']['images']
                        artwork_url = images[1]['url'] if len(images) >= 2 else images[0]['url']
                        artwork_cache.set_track_artwork(track_name, artist_name, artwork_url)
                        print(f"✅ Found artwork via track name: {artwork_url}")
                        found = True
                        break
            if not found:
                # 3. Try searching by artist only
                print("❌ No artwork with track name. Trying by artist only...")
                query = f"artist:{artist_name}"
                results = spotify_api.sp.search(q=query, type='track', limit=3)
                for t in results['tracks']['items']:
                    if t['album']['images']:
                        images = t['album']['images']
                        artwork_url = images[1]['url'] if len(images) >= 2 else images[0]['url']
                        artwork_cache.set_track_artwork(track_name, artist_name, artwork_url)
                        print(f"✅ Found artwork via artist: {artwork_url}")
                        found = True
                        break
            if not found:
                print("❌ No artwork found for this track after all fallbacks.")
                artwork_cache.set_track_artwork(track_name, artist_name, None)
        except Exception as e:
            print(f"Error searching for {track_name}: {e}")
            artwork_cache.set_track_artwork(track_name, artist_name, None)
        # Small delay to avoid rate limiting
        import time
        time.sleep(0.1)

    # Save cache
    artwork_cache.save_cache()
    print(f"💾 Saved artwork cache with {len(artwork_cache.cache)} tracks")

def main():
    """Main function to enrich all artwork"""
    print("🎨 Spotify Artwork Enrichment Tool")
    print("This will fetch artwork for your top tracks - run once!")
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

    # Load Spotify data
    df = load_spotify_data()
    if df is None:
        return


    # Get all unique tracks
    all_tracks = get_all_unique_tracks(df)
    print(f"🎵 Found {len(all_tracks)} unique tracks with >30s play time")

    # Initialize artwork cache
    artwork_cache = ArtworkCache()

    # Check if already enriched
    if os.path.exists('track_artwork_cache.json'):
        print("\\n⚠️ track_artwork_cache.json already exists. Adding new tracks...")


    # Enrich with artwork for all tracks
    enrich_artwork(spotify_api, artwork_cache, all_tracks)

    print("\\n🎉 Artwork enrichment complete!")
    print(f"📁 Your artwork cache is saved in: track_artwork_cache.json")
    print(f"🎨 Total tracks with artwork: {len([t for t in artwork_cache.cache.values() if t.get('artwork_url')])}")
    print("\\nYou can now see artwork in Track Details without any delays!")

if __name__ == "__main__":
    main()