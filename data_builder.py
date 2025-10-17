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
import urllib.request
import shutil


def resolve_project_path(relative_path):
    """
    Resolve a path relative to the project root.
    Works from any directory (pages/, root, etc.)
    """
    # Try different base paths
    potential_bases = [
        os.getcwd(),  # Current working directory
        os.path.dirname(__file__),  # Same directory as this script
        os.path.join(os.path.dirname(__file__), '..'),  # Parent directory (if in pages/)
    ]

    for base in potential_bases:
        full_path = os.path.join(base, relative_path)
        full_path = os.path.abspath(full_path)

        # Check if this path exists or if its parent directory exists (for files to be created)
        if os.path.exists(full_path) or os.path.exists(os.path.dirname(full_path)):
            return full_path

    # Default: return relative to current working directory
    return os.path.abspath(relative_path)


def load_raw_streaming_data(data_dir='streaming_data'):
    """Load all raw Spotify streaming history JSON files"""
    # Try to find the data directory - could be relative to cwd or script location
    search_paths = [
        data_dir,  # Relative to current working directory
        os.path.join(os.path.dirname(__file__), data_dir),  # Relative to this script
        os.path.join(os.path.dirname(__file__), '..', data_dir),  # One level up from pages/
    ]

    audio_files = []
    found_dir = None

    for path in search_paths:
        pattern = os.path.join(path, 'Streaming_History_Audio_*.json')
        files = glob.glob(pattern)
        if files:
            audio_files = files
            found_dir = path
            break

    if not audio_files:
        # Give helpful error with all paths tried
        tried_paths = '\n  '.join([os.path.abspath(p) for p in search_paths])
        raise FileNotFoundError(
            f"No streaming history files found. Tried:\n  {tried_paths}\n"
            f"Current working directory: {os.getcwd()}"
        )

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
    output_file = resolve_project_path(output_file)

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

    # Resolve output file path
    output_file = resolve_project_path(output_file)
    print(f"📁 Output file: {output_file}")

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

    # Convert timestamps to strings for JSON serialization
    if 'ts' in df.columns:
        df['ts'] = df['ts'].astype(str)

    # Convert to JSON and save
    data = df.to_dict('records')
    with open(output_file, 'w') as f:
        json.dump(data, f)

    print(f"✅ Successfully created enriched dataset with {len(df)} records")
    print(f"{'='*60}\n")

    return df


def download_enriched_data_from_release(output_file='data/enriched_spotify_data.json',
                                         release_url=None,
                                         progress_callback=None):
    """
    Download enriched data file from GitHub release.

    Args:
        output_file: Path to save enriched data
        release_url: URL to the release asset (if None, uses latest release)
        progress_callback: Function for progress updates

    Returns:
        True if downloaded successfully, False otherwise
    """
    if release_url is None:
        # Default to latest release
        release_url = "https://github.com/sara-kaczmarek/spotiboti/releases/latest/download/enriched_spotify_data.json"

    output_file = resolve_project_path(output_file)

    print(f"📥 Downloading enriched data from GitHub release...")
    if progress_callback:
        progress_callback("Downloading enriched dataset from GitHub...")

    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Download with progress
        with urllib.request.urlopen(release_url) as response:
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            chunk_size = 8192

            with open(output_file, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0 and progress_callback:
                        percent = (downloaded / total_size) * 100
                        progress_callback(f"Downloading... {percent:.1f}% ({downloaded // 1024 // 1024}MB / {total_size // 1024 // 1024}MB)")

        print(f"✅ Successfully downloaded enriched data")

        # Verify the downloaded file is valid JSON
        try:
            with open(output_file, 'r') as f:
                json.load(f)
            print(f"✅ Verified: File is valid JSON")
            return True
        except json.JSONDecodeError as e:
            print(f"❌ Downloaded file is not valid JSON: {e}")
            # Remove corrupted file
            if os.path.exists(output_file):
                os.remove(output_file)
            return False

    except Exception as e:
        print(f"⚠️  Failed to download from release: {e}")
        # Clean up partial download if it exists
        if os.path.exists(output_file):
            os.remove(output_file)
        return False


def ensure_enriched_data_exists(spotify_api=None, force_rebuild=False,
                                 output_file='data/enriched_spotify_data.json',
                                 progress_callback=None,
                                 try_download_first=True):
    """
    Ensure enriched data file exists. Tries to download from GitHub release first,
    then falls back to building from raw data if download fails.

    Args:
        spotify_api: SpotifyAPI instance (for genre enrichment)
        force_rebuild: Force rebuild even if file exists
        output_file: Path to enriched data file
        progress_callback: Function for progress updates
        try_download_first: Try downloading from GitHub release before building

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
        print("⚠️  Enriched data file not found.")

        # Try downloading from release first
        if try_download_first:
            print("📥 Attempting to download from GitHub release...")
            if progress_callback:
                progress_callback("Downloading enriched dataset from GitHub release...")

            if download_enriched_data_from_release(output_file, progress_callback=progress_callback):
                return True

            print("⚠️  Download failed. Falling back to building from raw data...")
            if progress_callback:
                progress_callback("Download failed. Building from raw streaming history...")

    # Build from raw data as fallback
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
