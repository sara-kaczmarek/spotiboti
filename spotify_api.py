import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
import pandas as pd
from datetime import datetime
import os
import streamlit as st
from genre_cache import GenreCache

class SpotifyAPI:
    def __init__(self, client_id=None, client_secret=None, redirect_uri="http://127.0.0.1:8080/callback"):
        """
        Initialize Spotify API client

        To get your credentials:
        1. Go to https://developer.spotify.com/dashboard
        2. Create a new app
        3. Add 'http://127.0.0.1:8080/callback' to Redirect URIs
        4. Copy Client ID and Client Secret
        """
        self.client_id = client_id or os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('SPOTIFY_CLIENT_SECRET')
        self.redirect_uri = redirect_uri

        if not self.client_id or not self.client_secret:
            st.error("Spotify credentials not found. Please set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables or pass them directly.")
            return

        self.scope = "user-read-recently-played user-read-playback-state user-library-read user-top-read"

        self.sp_oauth = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope,
            cache_path=".spotify_cache"
        )

        self.sp = None
        self.genre_cache = GenreCache()

    def authenticate(self):
        """Authenticate with Spotify using cached token or automatic flow"""
        try:
            # Try to get cached token first
            token_info = self.sp_oauth.get_cached_token()

            if token_info:
                self.sp = spotipy.Spotify(auth=token_info['access_token'])
                return True
            else:
                # If no cached token, we need manual auth
                auth_url = self.sp_oauth.get_authorize_url()
                st.markdown(f"**[Click here to authorize with Spotify]({auth_url})**")
                st.markdown("After authorization, copy the full URL and paste it below:")

                redirect_response = st.text_input(
                    "Paste the redirect URL:",
                    placeholder="http://127.0.0.1:8080/callback?code=...",
                    key="spotify_auth_url"
                )

                if redirect_response and "code=" in redirect_response:
                    try:
                        code = self.sp_oauth.parse_response_code(redirect_response)
                        if code:
                            token_info = self.sp_oauth.get_access_token(code)
                            if token_info:
                                self.sp = spotipy.Spotify(auth=token_info['access_token'])
                                st.success("✅ Authentication successful!")
                                st.rerun()
                                return True
                    except Exception as e:
                        st.error(f"Authentication error: {e}")
                        return False

        except Exception as e:
            st.error(f"Authentication failed: {e}")

        return False

    def is_authenticated(self):
        """Check if we have a valid authenticated session"""
        return self.sp is not None

    def get_recently_played(self, limit=50):
        """Get recently played tracks (last 50 maximum)"""
        if not self.sp:
            st.error("Not authenticated. Please authenticate first.")
            return None

        try:
            results = self.sp.current_user_recently_played(limit=limit)
            tracks = []

            for item in results['items']:
                track = item['track']
                played_at = item['played_at']

                # Get album artwork (use medium size if available)
                album_image_url = None
                if track['album']['images']:
                    # Spotify provides images in different sizes, pick medium size (typically 300x300)
                    images = track['album']['images']
                    if len(images) >= 2:
                        album_image_url = images[1]['url']  # Medium size
                    else:
                        album_image_url = images[0]['url']  # Use whatever is available

                track_data = {
                    'ts': played_at,
                    'master_metadata_track_name': track['name'],
                    'master_metadata_album_artist_name': track['artists'][0]['name'] if track['artists'] else 'Unknown',
                    'master_metadata_album_album_name': track['album']['name'],
                    'spotify_track_uri': track['uri'],
                    'album_image_url': album_image_url,
                    'ms_played': track['duration_ms'],  # Full duration since we don't have actual play time
                    'conn_country': 'Unknown',  # Not available in recently played
                    'ip_addr_decrypted': 'Unknown',  # Not available
                    'user_agent_decrypted': 'API',
                    'platform': 'API',
                    'skipped': False  # Assume not skipped for recently played
                }
                tracks.append(track_data)

            return pd.DataFrame(tracks)

        except Exception as e:
            st.error(f"Error fetching recently played tracks: {e}")
            return None

    def get_top_tracks(self, time_range='medium_term', limit=50):
        """Get user's top tracks"""
        if not self.sp:
            st.error("Not authenticated. Please authenticate first.")
            return None

        try:
            results = self.sp.current_user_top_tracks(
                time_range=time_range,  # short_term (~4 weeks), medium_term (~6 months), long_term (~several years)
                limit=limit
            )

            tracks = []
            for track in results['items']:
                track_data = {
                    'master_metadata_track_name': track['name'],
                    'master_metadata_album_artist_name': track['artists'][0]['name'] if track['artists'] else 'Unknown',
                    'master_metadata_album_album_name': track['album']['name'],
                    'spotify_track_uri': track['uri'],
                    'popularity': track['popularity'],
                    'duration_ms': track['duration_ms']
                }
                tracks.append(track_data)

            return pd.DataFrame(tracks)

        except Exception as e:
            st.error(f"Error fetching top tracks: {e}")
            return None

    def get_top_artists(self, time_range='medium_term', limit=50):
        """Get user's top artists"""
        if not self.sp:
            st.error("Not authenticated. Please authenticate first.")
            return None

        try:
            results = self.sp.current_user_top_artists(
                time_range=time_range,
                limit=limit
            )

            artists = []
            for artist in results['items']:
                artist_data = {
                    'name': artist['name'],
                    'popularity': artist['popularity'],
                    'genres': ', '.join(artist['genres']) if artist['genres'] else 'Unknown',
                    'followers': artist['followers']['total'],
                    'spotify_uri': artist['uri']
                }
                artists.append(artist_data)

            return pd.DataFrame(artists)

        except Exception as e:
            st.error(f"Error fetching top artists: {e}")
            return None

    def get_user_profile(self):
        """Get current user's profile"""
        if not self.sp:
            return None

        try:
            return self.sp.current_user()
        except Exception as e:
            st.error(f"Error fetching user profile: {e}")
            return None

    def get_artist_genres(self, artist_name):
        """Get genres for an artist, using cache first"""
        if not self.sp:
            return []

        # Check cache first
        cached_data = self.genre_cache.get_artist_genres(artist_name)
        if cached_data:
            return cached_data.get('genres', [])

        try:
            # Search for the artist
            results = self.sp.search(q=f"artist:{artist_name}", type='artist', limit=1)

            if results['artists']['items']:
                artist = results['artists']['items'][0]
                genres = artist.get('genres', [])

                # Cache the result
                self.genre_cache.set_artist_genres(artist_name, genres)
                return genres

        except Exception:
            # Silently fail for individual artist lookups
            pass

        # Cache empty result to avoid repeated API calls
        self.genre_cache.set_artist_genres(artist_name, [])
        return []

    def enrich_dataframe_with_genres(self, df, max_tracks=None, show_progress=True):
        """Add genre information to a dataframe of tracks using artist genres"""
        if not self.sp:
            return df

        # Make a copy to avoid modifying the original
        df_copy = df.copy()
        df_copy['genres'] = ''

        # Get unique artists to minimize API calls
        unique_artists = df_copy['master_metadata_album_artist_name'].unique()
        if max_tracks:
            # Limit by taking artists from first N tracks
            limited_df = df_copy.head(max_tracks)
            unique_artists = limited_df['master_metadata_album_artist_name'].unique()

        if show_progress:
            with st.sidebar:
                progress_bar = st.progress(0)
                status_text = st.empty()

        # Fetch genres for unique artists
        artist_genres_map = {}
        for i, artist in enumerate(unique_artists):
            if show_progress:
                status_text.text(f"Fetching genres for artist {i+1}/{len(unique_artists)}: {artist}")

            genres = self.get_artist_genres(artist)
            artist_genres_map[artist] = ', '.join(genres) if genres else 'Unknown'

            if show_progress:
                progress_bar.progress((i + 1) / len(unique_artists))

            # Small delay to avoid rate limiting (only for new API calls)
            cached_data = self.genre_cache.get_artist_genres(artist)
            if not cached_data:
                import time
                time.sleep(0.1)

        # Apply genres to all tracks
        df_copy['genres'] = df_copy['master_metadata_album_artist_name'].map(artist_genres_map)

        if show_progress:
            progress_bar.empty()
            status_text.empty()

        # Save cache after processing
        self.genre_cache.save_cache()

        return df_copy

    def get_user_playlists(self):
        """Get ALL user's playlists using pagination"""
        if not self.sp:
            st.error("Not authenticated. Please authenticate first.")
            return None

        try:
            playlists = []
            offset = 0
            batch_size = 50

            while True:
                results = self.sp.current_user_playlists(limit=batch_size, offset=offset)

                if not results['items']:
                    break  # No more playlists

                for playlist in results['items']:
                    # Get playlist image
                    playlist_image = None
                    if playlist['images']:
                        playlist_image = playlist['images'][0]['url']

                    playlist_data = {
                        'name': playlist['name'],
                        'description': playlist['description'] or '',
                        'tracks_total': playlist['tracks']['total'],
                        'public': playlist['public'],
                        'collaborative': playlist['collaborative'],
                        'owner': playlist['owner']['display_name'],
                        'playlist_id': playlist['id'],
                        'playlist_url': playlist['external_urls']['spotify'],
                        'image_url': playlist_image
                    }
                    playlists.append(playlist_data)

                # Check if we have more playlists
                if len(results['items']) < batch_size or offset + batch_size >= results['total']:
                    break

                offset += batch_size

            return pd.DataFrame(playlists)

        except Exception as e:
            st.error(f"Error fetching playlists: {e}")
            return None

    def get_playlist_tracks(self, playlist_id, limit=100):
        """Get tracks from a specific playlist"""
        if not self.sp:
            return None

        try:
            results = self.sp.playlist_tracks(playlist_id, limit=limit)
            tracks = []

            for item in results['items']:
                if item['track'] and item['track']['type'] == 'track':
                    track = item['track']

                    # Get album artwork
                    album_image_url = None
                    if track['album']['images']:
                        images = track['album']['images']
                        if len(images) >= 2:
                            album_image_url = images[1]['url']  # Medium size
                        else:
                            album_image_url = images[0]['url']

                    # Audio features require additional permissions, skip for now
                    audio_features = None

                    track_data = {
                        'name': track['name'],
                        'artist': track['artists'][0]['name'] if track['artists'] else 'Unknown',
                        'album': track['album']['name'],
                        'duration_ms': track['duration_ms'],
                        'popularity': track['popularity'],
                        'track_id': track['id'],
                        'album_image_url': album_image_url,
                        'added_at': item['added_at'],
                        'preview_url': track.get('preview_url'),
                        'spotify_url': track['external_urls']['spotify']
                    }

                    # Add audio features if available
                    if audio_features:
                        track_data.update({
                            'danceability': audio_features.get('danceability'),
                            'energy': audio_features.get('energy'),
                            'valence': audio_features.get('valence'),
                            'tempo': audio_features.get('tempo'),
                            'acousticness': audio_features.get('acousticness'),
                            'instrumentalness': audio_features.get('instrumentalness'),
                            'speechiness': audio_features.get('speechiness')
                        })

                    tracks.append(track_data)

            return pd.DataFrame(tracks)

        except Exception as e:
            st.error(f"Error fetching playlist tracks: {e}")
            return None

    def find_track_artwork_from_playlists(self, track_name, artist_name):
        """Search for track artwork by looking through user's playlists"""
        if not self.sp:
            return None

        try:
            # Get user playlists
            playlists = self.get_user_playlists()
            if playlists is None or playlists.empty:
                return None

            # Search through playlists for the track
            for _, playlist in playlists.iterrows():
                playlist_tracks = self.get_playlist_tracks(playlist['playlist_id'], limit=50)
                if playlist_tracks is not None and not playlist_tracks.empty:
                    # Look for matching track
                    matching_tracks = playlist_tracks[
                        (playlist_tracks['name'].str.lower() == track_name.lower()) &
                        (playlist_tracks['artist'].str.lower() == artist_name.lower())
                    ]

                    if not matching_tracks.empty and 'album_image_url' in matching_tracks.columns:
                        album_image = matching_tracks['album_image_url'].iloc[0]
                        if pd.notna(album_image):
                            return album_image

            return None

        except Exception as e:
            # Silently fail and return None
            return None