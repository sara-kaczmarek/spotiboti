#!/usr/bin/env python3
"""
Auto-update script to fetch recent tracks from Spotify API
and append them to enriched_spotify_data.json with genres and artwork
"""

import json
import os
import sys
import pandas as pd
from datetime import datetime

# Mock streamlit for non-interactive usage
class MockStreamlit:
    def error(self, msg): print(f"ERROR: {msg}")
    def warning(self, msg): print(f"WARNING: {msg}")
    def success(self, msg): print(f"SUCCESS: {msg}")
    def info(self, msg): print(f"INFO: {msg}")
    class secrets:
        @staticmethod
        def get(key, default=None):
            return os.getenv(key, default)
        @staticmethod
        def __getitem__(key):
            return os.getenv(key)

sys.modules['streamlit'] = MockStreamlit()

from spotify_api import SpotifyAPI

def load_existing_data():
    """Load existing enriched data, build if missing"""
    data_file = 'data/enriched_spotify_data.json'

    # Check if file exists
    if not os.path.exists(data_file):
        print("⚠️  Enriched data file not found.")
        print("🔧 Building from raw streaming history...")

        try:
            from data_builder import build_enriched_data_from_raw
            from spotify_api import SpotifyAPI

            # Try to build with API
            try:
                api = SpotifyAPI()
                df = build_enriched_data_from_raw(
                    spotify_api=api,
                    output_file=data_file,
                    enrich_genres=True
                )
                print("✅ Successfully built enriched dataset with genres!")
                return df
            except Exception as e:
                print(f"⚠️  Building without genre enrichment: {e}")
                df = build_enriched_data_from_raw(
                    spotify_api=None,
                    output_file=data_file,
                    enrich_genres=False
                )
                print("✅ Successfully built enriched dataset (no genres)!")
                return df

        except Exception as e:
            print(f"❌ Failed to build enriched data: {e}")
            print("📊 Starting with empty dataset")
            return pd.DataFrame()

    # Load existing file
    try:
        with open(data_file, 'r') as f:
            data = json.load(f)
        return pd.DataFrame(data)
    except Exception as e:
        print(f"❌ Error loading enriched data: {e}")
        return pd.DataFrame()

def fetch_recent_tracks():
    """Fetch recent 50 tracks from Spotify API"""
    print("🎵 Fetching recent tracks from Spotify API...")

    # Initialize Spotify API
    api = SpotifyAPI()

    # Try to authenticate
    try:
        # First try cached token
        token_info = api.sp_oauth.get_cached_token()
        if token_info:
            import spotipy
            api.sp = spotipy.Spotify(auth=token_info['access_token'])
        else:
            # For GitHub Actions: use client credentials flow (no user auth needed for recently played)
            # We'll need to use a different approach - store refresh token as secret
            print("⚠️ No cached token. Attempting fresh authentication...")
            token_info = api.sp_oauth.get_access_token(as_dict=True)
            if token_info:
                import spotipy
                api.sp = spotipy.Spotify(auth=token_info['access_token'])
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return None, None

    # Get recently played tracks
    recent_df = api.get_recently_played(limit=50)

    if recent_df is None or recent_df.empty:
        print("⚠️ No recent tracks found.")
        return None, api

    print(f"✅ Fetched {len(recent_df)} recent tracks")
    return recent_df, api

def enrich_tracks(df, api):
    """Enrich tracks with genres"""
    print("🎨 Enriching tracks with genres...")

    # Get unique artists
    unique_artists = df['master_metadata_album_artist_name'].unique()

    # Fetch genres for each artist
    for i, artist in enumerate(unique_artists):
        genres = api.get_artist_genres(artist)
        df.loc[df['master_metadata_album_artist_name'] == artist, 'genres'] = ', '.join(genres) if genres else 'Unknown'
        print(f"  [{i+1}/{len(unique_artists)}] {artist}: {', '.join(genres) if genres else 'Unknown'}")

    # Save genre cache
    api.genre_cache.save_cache()

    print("✅ Enrichment complete!")
    return df

def remove_duplicates(existing_df, new_df):
    """Remove ONLY exact duplicate entries (same track at exact same timestamp)

    This keeps all your listens - if you played the same song twice, both plays are kept!
    We only filter out duplicates from re-running the API fetch (same timestamp = duplicate API call)
    """
    if existing_df.empty:
        return new_df

    # Create a key for deduplication using ONLY timestamp
    # This way, only exact duplicate API fetches are filtered, not repeated song plays
    existing_df['dedup_key'] = existing_df['ts'].astype(str)
    new_df['dedup_key'] = new_df['ts'].astype(str)

    # Filter out only exact timestamp matches (duplicate API fetches)
    new_tracks = new_df[~new_df['dedup_key'].isin(existing_df['dedup_key'])].copy()

    # Drop the dedup key
    new_tracks = new_tracks.drop('dedup_key', axis=1)

    filtered_count = len(new_df) - len(new_tracks)
    if filtered_count > 0:
        print(f"📊 Found {len(new_tracks)} new tracks (filtered {filtered_count} exact duplicate timestamps from previous API calls)")
    else:
        print(f"📊 Found {len(new_tracks)} new tracks (no duplicates)")

    return new_tracks

def update_enriched_data(new_tracks_df):
    """Append new tracks to enriched data file"""
    # Load existing data
    existing_df = load_existing_data()

    # Remove duplicates
    new_tracks_df = remove_duplicates(existing_df, new_tracks_df)

    if new_tracks_df.empty:
        print("✅ No new tracks to add. Data is up to date!")
        return False

    # Combine datasets
    if existing_df.empty:
        combined_df = new_tracks_df
    else:
        combined_df = pd.concat([existing_df, new_tracks_df], ignore_index=True)

    # Sort by timestamp (newest first)
    combined_df = combined_df.sort_values('ts', ascending=False).reset_index(drop=True)

    # Save to file
    print(f"💾 Saving {len(combined_df)} total tracks to enriched_spotify_data.json...")
    combined_data = combined_df.to_dict('records')

    with open('data/enriched_spotify_data.json', 'w') as f:
        json.dump(combined_data, f)

    print(f"✅ Successfully added {len(new_tracks_df)} new tracks!")
    print(f"📈 Total tracks in dataset: {len(combined_df)}")

    return True

def main():
    """Main update function"""
    print("=" * 60)
    print("🎵 Spotify Recent Tracks Auto-Update")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Fetch recent tracks (returns df and api object)
    recent_df, api = fetch_recent_tracks()

    if recent_df is None or api is None:
        print("❌ Failed to fetch recent tracks")
        return

    # Enrich with genres
    enriched_df = enrich_tracks(recent_df, api)

    # Update the enriched data file
    updated = update_enriched_data(enriched_df)

    if updated:
        print("\n✅ Data update complete! Your enriched dataset has been updated.")
    else:
        print("\n✅ No updates needed. Dataset is current.")

    print("=" * 60)

if __name__ == "__main__":
    main()
