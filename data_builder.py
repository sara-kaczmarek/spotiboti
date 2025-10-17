#!/usr/bin/env python3
"""
Utility to build enriched Spotify data from raw streaming history files.
Used by the Streamlit app on startup and by update scripts.
"""

import json
import os
import glob
import pandas as pd
from datetime import datetime
from pathlib import Path


def load_raw_streaming_data(data_dir='streaming_data'):
    """Load all raw Spotify streaming history JSON files"""
    audio_files = glob.glob(os.path.join(data_dir, 'Streaming_History_Audio_*.json'))

    if not audio_files:
        raise FileNotFoundError(f"No streaming history files found in {data_dir}/")

    print(f"📁 Found {len(audio_files)} raw streaming history files")

    all_streams = []
    for file in audio_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_streams.extend(data)
        except Exception as e:
            print(f"⚠️  Error loading {file}: {e}")

    print(f"📊 Loaded {len(all_streams)} total listening records")

    # Convert to DataFrame
    df = pd.DataFrame(all_streams)

    if 'ts' in df.columns:
        df['ts'] = pd.to_datetime(df['ts'])

    # Filter short plays (less than 30 seconds)
    if 'ms_played' in df.columns:
        df_filtered = df[df['ms_played'] >= 30000].copy()
        print(f"✂️  Filtered to {len(df_filtered)} plays (removed plays < 30 seconds)")
        return df_filtered

    return df


def check_enriched_data_exists(output_file='data/enriched_spotify_data.json'):
    """Check if enriched data file exists and return basic info"""
    if not os.path.exists(output_file):
        return False, None

    try:
        with open(output_file, 'r') as f:
            data = json.load(f)

        df = pd.DataFrame(data)
        if 'ts' in df.columns:
            df['ts'] = pd.to_datetime(df['ts'], format='mixed')
            latest = df['ts'].max()
            return True, {'count': len(df), 'latest': latest}
        return True, {'count': len(df), 'latest': None}
    except:
        return False, None


def build_enriched_data_from_raw(spotify_api=None, output_file='data/enriched_spotify_data.json',
                                  enrich_genres=True, progress_callback=None):
    """
    Build enriched data file from raw streaming history.

    Args:
        spotify_api: SpotifyAPI instance (optional, needed for genre enrichment)
        output_file: Path to save enriched data
        enrich_genres: Whether to enrich with genre data (requires spotify_api)
        progress_callback: Function to call with progress updates (for Streamlit)

    Returns:
        DataFrame with enriched data
    """
    print(f"\n{'='*60}")
    print(f"🔧 Building enriched dataset from raw streaming history")
    print(f"{'='*60}\n")

    # Load raw data
    if progress_callback:
        progress_callback("Loading raw streaming history...")

    df = load_raw_streaming_data()

    # Enrich with genres if requested and API provided
    if enrich_genres and spotify_api:
        if progress_callback:
            progress_callback(f"Enriching with genre data for unique artists...")

        print(f"\n🎨 Enriching with genre data...")

        # Get unique artists
        if 'master_metadata_album_artist_name' in df.columns:
            unique_artists = df['master_metadata_album_artist_name'].unique()
            print(f"🎤 Found {len(unique_artists)} unique artists")

            # Fetch genres for each artist
            for i, artist in enumerate(unique_artists):
                if i % 100 == 0 and progress_callback:
                    progress_callback(f"Enriching genres... {i}/{len(unique_artists)} artists")

                try:
                    genres = spotify_api.get_artist_genres(artist)
                    df.loc[df['master_metadata_album_artist_name'] == artist, 'genres'] = \
                        ', '.join(genres) if genres else 'Unknown'
                except Exception as e:
                    print(f"⚠️  Error fetching genres for {artist}: {e}")
                    df.loc[df['master_metadata_album_artist_name'] == artist, 'genres'] = 'Unknown'

            # Save genre cache
            if hasattr(spotify_api, 'genre_cache'):
                spotify_api.genre_cache.save_cache()
                print("💾 Saved genre cache")

    # Sort by timestamp
    if 'ts' in df.columns:
        df = df.sort_values('ts', ascending=False).reset_index(drop=True)

    # Save to file
    if progress_callback:
        progress_callback("Saving enriched dataset...")

    print(f"\n💾 Saving enriched dataset to {output_file}...")

    # Ensure directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Convert to JSON and save
    data = df.to_dict('records')
    with open(output_file, 'w') as f:
        json.dump(data, f)

    print(f"✅ Successfully created enriched dataset with {len(df)} records")
    print(f"{'='*60}\n")

    return df


def ensure_enriched_data_exists(spotify_api=None, force_rebuild=False,
                                 output_file='data/enriched_spotify_data.json',
                                 progress_callback=None):
    """
    Ensure enriched data file exists, building it if necessary.

    Args:
        spotify_api: SpotifyAPI instance (for genre enrichment)
        force_rebuild: Force rebuild even if file exists
        output_file: Path to enriched data file
        progress_callback: Function for progress updates

    Returns:
        True if data is ready, False if failed
    """
    exists, info = check_enriched_data_exists(output_file)

    if exists and not force_rebuild:
        print(f"✅ Enriched data file exists ({info['count']} records)")
        if info['latest']:
            print(f"   Latest data: {info['latest']}")
        return True

    if force_rebuild:
        print("🔄 Force rebuild requested")
    else:
        print("⚠️  Enriched data file not found. Building from raw data...")

    try:
        build_enriched_data_from_raw(
            spotify_api=spotify_api,
            output_file=output_file,
            enrich_genres=(spotify_api is not None),
            progress_callback=progress_callback
        )
        return True
    except Exception as e:
        print(f"❌ Failed to build enriched data: {e}")
        return False


if __name__ == "__main__":
    # Allow running as standalone script
    import sys

    # Mock streamlit for standalone usage
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

    print("Building enriched dataset...")

    try:
        api = SpotifyAPI()
        ensure_enriched_data_exists(spotify_api=api, force_rebuild=True)
    except Exception as e:
        print(f"Note: Building without genre enrichment (Spotify API not available: {e})")
        ensure_enriched_data_exists(spotify_api=None, force_rebuild=True)
