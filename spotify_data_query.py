import pandas as pd
import json
import re

class SpotifyDataQuery:
    def __init__(self):
        with open('data/enriched_spotify_data.json', 'r') as f:
            self.df = pd.DataFrame(json.load(f))
        self.df['ts'] = pd.to_datetime(self.df['ts'])
        self.df['date'] = self.df['ts'].dt.date
        self.df['year'] = self.df['ts'].dt.year
        # Convert ms_played to hours_played for easier calculations
        if 'ms_played' in self.df.columns:
            self.df['hours_played'] = self.df['ms_played'] / (1000 * 60 * 60)  # ms to hours
        else:
            self.df['hours_played'] = 0  # fallback

    def analyze_query(self, query):
        """Simple query analysis - just look at the data directly"""

        # "Song by Artist" pattern
        song_by_artist = re.search(r'([^\\n]+?)\\s+by\\s+([^\\n]+?)(?:[\\s\\n]|$)', query, re.IGNORECASE)
        if song_by_artist:
            song, artist = song_by_artist.groups()
            return self._query_song_by_artist(song.strip(), artist.strip())

        # Extract temporal info from query
        filtered_data, period_info = self._filter_by_time(query)

        # Check for artist-specific song queries FIRST (e.g., "my top j cole songs", "favorite drake songs")
        # This must come before general song/artist detection to avoid conflicts
        artist_song_patterns = [
            r'(?:top|favorite|best|fave)\s+\d+\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)\s+songs?',  # "top 5 j cole songs" - with number
            r'(?:top|favorite|best|fave)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)\s+songs?',  # "top j cole songs" - without number
            r'(?:my|give me|show me)\s+(?:my\s+)?(?:top|favorite|best|fave)?\s*\d+\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)\s+songs?',  # "give me my top 5 j cole songs"
            r'(?:my|give me|show me)\s+(?:my\s+)?(?:top|favorite|best|fave)?\s*([a-zA-Z]+(?:\s+[a-zA-Z]+)*)\s+songs?',  # "give me j cole songs"
            r'([a-zA-Z]+(?:\s+[a-zA-Z]+)*)\s+songs?',  # "j cole songs" or "tyla songs"
            r'songs?\s+by\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)',  # "songs by j cole"
        ]

        detected_artist = None
        for pattern in artist_song_patterns:
            match = re.search(pattern, query.lower())
            if match:
                potential_artist = match.group(1).strip()
                # Filter out generic words that aren't artist names
                if potential_artist not in ['my', 'me', 'favorite', 'top', 'best', 'fave', 'all', 'the']:
                    # Check if this artist exists in our data (exact match first)
                    if self.df['master_metadata_album_artist_name'].str.lower().str.contains(potential_artist, case=False, na=False).any():
                        detected_artist = potential_artist
                        break

                    # Try common variations if exact match fails
                    variations = self._generate_artist_name_variations(potential_artist)

                    for variation in variations:
                        if self.df['master_metadata_album_artist_name'].str.lower().str.contains(variation.lower(), case=False, na=False).any():
                            detected_artist = potential_artist  # Keep original for user feedback
                            break

                    if detected_artist:
                        break

        if detected_artist:
            return self._get_artist_songs(filtered_data, period_info, detected_artist)

        # Check for "first song" queries
        first_song_patterns = [
            r'(?:first|earliest)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)\s+song',  # "first tyla song"
            r'(?:what|which)\s+(?:is|was)\s+(?:the\s+)?(?:first|earliest)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)\s+song',  # "what is the first tyla song"
            r'(?:first|earliest)\s+song\s+(?:by|from)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)',  # "first song by tyla"
        ]

        for pattern in first_song_patterns:
            match = re.search(pattern, query.lower())
            if match:
                potential_artist = match.group(1).strip()
                if potential_artist not in ['my', 'me', 'favorite', 'top', 'best', 'fave', 'all', 'the']:
                    # Check if this artist exists in our data
                    if self.df['master_metadata_album_artist_name'].str.lower().str.contains(potential_artist, case=False, na=False).any():
                        return self._get_first_song_by_artist(filtered_data, period_info, potential_artist)

                    # Try variations
                    variations = self._generate_artist_name_variations(potential_artist)
                    for variation in variations:
                        if self.df['master_metadata_album_artist_name'].str.lower().str.contains(variation.lower(), case=False, na=False).any():
                            return self._get_first_song_by_artist(filtered_data, period_info, potential_artist)

        # Check for first song in genre queries
        first_genre_patterns = [
            r'(?:first|earliest)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)\s+song',  # "first afrobeats song"
            r'(?:what|which)\s+(?:is|was)\s+(?:the\s+)?(?:first|earliest)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)\s+song',  # "what is the first afrobeats song"
        ]

        for pattern in first_genre_patterns:
            match = re.search(pattern, query.lower())
            if match:
                potential_genre = match.group(1).strip()
                if potential_genre not in ['my', 'me', 'favorite', 'top', 'best', 'fave', 'all', 'the']:
                    return self._get_first_song_by_genre(filtered_data, period_info, potential_genre)

        # Check for "last song" queries
        last_song_patterns = [
            r'(?:last|latest|most recent)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)\s+song',  # "last tyla song"
            r'(?:what|which)\s+(?:is|was)\s+(?:the\s+)?(?:last|latest|most recent)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)\s+song',  # "what is the last tyla song"
            r'(?:last|latest|most recent)\s+song\s+(?:by|from)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)',  # "last song by tyla"
            r'(?:and\s+)?(?:my\s+)?(?:last|latest)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)\s+song',  # "and my last drake song"
        ]

        for pattern in last_song_patterns:
            match = re.search(pattern, query.lower())
            if match:
                potential_artist = match.group(1).strip()
                if potential_artist not in ['my', 'me', 'favorite', 'top', 'best', 'fave', 'all', 'the']:
                    # Check if this artist exists in our data
                    if self.df['master_metadata_album_artist_name'].str.lower().str.contains(potential_artist, case=False, na=False).any():
                        return self._get_last_song_by_artist(filtered_data, period_info, potential_artist)

                    # Try variations
                    variations = self._generate_artist_name_variations(potential_artist)
                    for variation in variations:
                        if self.df['master_metadata_album_artist_name'].str.lower().str.contains(variation.lower(), case=False, na=False).any():
                            return self._get_last_song_by_artist(filtered_data, period_info, potential_artist)

        # Check for last song in genre queries
        last_genre_patterns = [
            r'(?:last|latest|most recent)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)\s+song',  # "last afrobeats song"
            r'(?:what|which)\s+(?:is|was)\s+(?:the\s+)?(?:last|latest|most recent)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)\s+song',  # "what is the last afrobeats song"
        ]

        for pattern in last_genre_patterns:
            match = re.search(pattern, query.lower())
            if match:
                potential_genre = match.group(1).strip()
                if potential_genre not in ['my', 'me', 'favorite', 'top', 'best', 'fave', 'all', 'the']:
                    return self._get_last_song_by_genre(filtered_data, period_info, potential_genre)

        # Check for multiple requests (artist AND song)
        wants_song = any(phrase in query.lower() for phrase in ['favorite song', 'top song', 'best song', 'song'])
        wants_artist = any(phrase in query.lower() for phrase in ['favorite artist', 'top artist', 'best artist', 'artist'])
        wants_genre = any(phrase in query.lower() for phrase in ['favorite genre', 'top genre', 'best genre', 'genre'])

        # Check for AND combinations first (most specific)
        if wants_song and wants_artist and wants_genre:
            return self._get_multiple_favorites(filtered_data, period_info, ['song', 'artist', 'genre'])
        elif wants_song and wants_artist:
            return self._get_multiple_favorites(filtered_data, period_info, ['song', 'artist'])
        elif wants_song and wants_genre:
            return self._get_multiple_favorites(filtered_data, period_info, ['song', 'genre'])
        elif wants_artist and wants_genre:
            return self._get_multiple_favorites(filtered_data, period_info, ['artist', 'genre'])
        # Single requests (less specific)
        elif wants_song:
            return self._get_favorite_song(filtered_data, period_info)
        elif wants_artist:
            return self._get_favorite_artist(filtered_data, period_info)
        elif wants_genre:
            return self._get_favorite_genre(filtered_data, period_info)
        # Check for daily listening requests (including duration queries)
        elif any(phrase in query.lower() for phrase in ['what did i listen', 'listened to on', 'music on', 'listening history', 'how long did i listen', 'how much music', 'music for on']):
            return self._get_daily_listening(filtered_data, period_info)

        # Generate simple stats
        if filtered_data.empty:
            return {
                'query': query,
                'analysis_type': 'general',
                'data': {'error': f'No data found for {period_info}'},
                'period_info': period_info
            }

        return {
            'query': query,
            'analysis_type': 'general',
            'data': {
                'stats': {
                    'total_plays': len(filtered_data),
                    'total_hours': filtered_data['hours_played'].sum(),
                    'unique_artists': filtered_data['master_metadata_album_artist_name'].nunique(),
                    'unique_songs': filtered_data['master_metadata_track_name'].nunique(),
                    'date_range': f"{filtered_data['date'].min()} to {filtered_data['date'].max()}",
                    'avg_daily_hours': filtered_data.groupby('date')['hours_played'].sum().mean() if not filtered_data.empty else 0,
                    'most_active_day': filtered_data.groupby(filtered_data['ts'].dt.day_name()).size().idxmax() if not filtered_data.empty else 'Unknown',
                    'most_active_hour': filtered_data.groupby(filtered_data['ts'].dt.hour).size().idxmax() if not filtered_data.empty else 0
                },
                'top_artists': filtered_data['master_metadata_album_artist_name'].value_counts().head(10).to_dict(),
                'top_songs': filtered_data['master_metadata_track_name'].value_counts().head(10).to_dict(),
                'top_genres': self._extract_top_genres(filtered_data, 5),
                'time_patterns': {
                    'peak_listening_hour': filtered_data.groupby(filtered_data['ts'].dt.hour).size().idxmax() if not filtered_data.empty else 0,
                    'peak_listening_day': filtered_data.groupby(filtered_data['ts'].dt.day_name()).size().idxmax() if not filtered_data.empty else 'Unknown'
                },
                'total_tracks_in_period': len(filtered_data)
            },
            'period_info': period_info
        }

    def _query_song_by_artist(self, song, artist):
        """Direct pandas query for song by artist"""

        # Exact match query
        matches = self.df[
            (self.df['master_metadata_track_name'].str.lower() == song.lower()) &
            (self.df['master_metadata_album_artist_name'].str.lower() == artist.lower())
        ]

        if matches.empty:
            # Check what actually exists
            song_matches = self.df[self.df['master_metadata_track_name'].str.lower() == song.lower()]
            artist_matches = self.df[self.df['master_metadata_album_artist_name'].str.lower() == artist.lower()]

            if not song_matches.empty and not artist_matches.empty:
                actual_artist = song_matches['master_metadata_album_artist_name'].iloc[0]
                error_msg = f'You have listened to "{song}" but by {actual_artist}, not {artist}'
            elif not song_matches.empty:
                actual_artist = song_matches['master_metadata_album_artist_name'].iloc[0]
                error_msg = f'You have listened to "{song}" but by {actual_artist}, not {artist}'
            elif not artist_matches.empty:
                error_msg = f'You listen to {artist}, but not the song "{song}"'
            else:
                error_msg = f'No data found for "{song}" by {artist}'

            return {
                'query': f'{song} by {artist}',
                'analysis_type': 'song_by_artist',
                'data': {'error': error_msg},
                'period_info': None
            }

        # We found it! Get the actual data
        first_play = matches['ts'].min()
        last_play = matches['ts'].max()

        return {
            'query': f'{song} by {artist}',
            'analysis_type': 'song_by_artist',
            'data': {
                'song': matches.iloc[0]['master_metadata_track_name'],
                'artist': matches.iloc[0]['master_metadata_album_artist_name'],
                'first_listen_date': first_play.strftime('%B %d, %Y'),
                'first_listen_time': first_play.strftime('%H:%M'),
                'last_listen_date': last_play.strftime('%B %d, %Y'),
                'total_plays': len(matches),
                'years_active': f"{first_play.year}" if first_play.year == last_play.year else f"{first_play.year}-{last_play.year}"
            },
            'period_info': f"First played: {first_play.strftime('%B %d, %Y')}"
        }

    def _get_favorite_artist(self, filtered_data, period_info):
        """Get favorite artist for the filtered period"""
        if filtered_data.empty:
            return {
                'query': f'favorite artist in {period_info}',
                'analysis_type': 'favorite_artist',
                'data': {'error': f'No data found for {period_info}'},
                'period_info': period_info
            }

        top_artist = filtered_data['master_metadata_album_artist_name'].value_counts().index[0]
        play_count = filtered_data['master_metadata_album_artist_name'].value_counts().iloc[0]

        return {
            'query': f'favorite artist in {period_info}',
            'analysis_type': 'favorite_artist',
            'data': {
                'top_artists': {top_artist: play_count},
                'period': period_info
            },
            'period_info': period_info
        }

    def _filter_by_time(self, query):
        """Filter data based on time period mentioned in query"""
        query_lower = query.lower()

        # Month mapping
        months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
            'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
        }

        # Extract year
        years_in_data = sorted(self.df['year'].unique())
        detected_year = None
        for year in years_in_data:
            if str(year) in query:
                detected_year = year
                break

        # Extract month
        detected_month = None
        for month_name, month_num in months.items():
            if month_name in query_lower:
                detected_month = month_num
                break

        # Extract day - look for patterns like "March 15", "15th", "on the 3rd", "17th of"
        detected_day = None
        day_patterns = [
            r'\b(\d{1,2})(?:st|nd|rd|th)\s+of\b',  # "17th of September"
            r'\b(\d{1,2})(?:st|nd|rd|th)?\b',      # "15th", "3rd", "22"
            r'\b(\d{1,2})\s*,?\s*\d{4}',          # "15, 2020" or "15 2020"
        ]

        for pattern in day_patterns:
            matches = re.findall(pattern, query)
            for match in matches:
                day = int(match)
                if 1 <= day <= 31:  # Valid day range
                    detected_day = day
                    break
            if detected_day:
                break

        # Filter data based on what we found
        if detected_year and detected_month and detected_day:
            # Specific date
            target_date = pd.Timestamp(year=detected_year, month=detected_month, day=detected_day).date()
            filtered_data = self.df[self.df['date'] == target_date]
            month_name = list(months.keys())[detected_month-1].title()
            period_info = f"{month_name} {detected_day}, {detected_year}"
        elif detected_year and detected_month:
            # Specific month
            filtered_data = self.df[(self.df['year'] == detected_year) & (self.df['ts'].dt.month == detected_month)]
            period_info = f"{list(months.keys())[detected_month-1].title()} {detected_year}"
        elif detected_year:
            # Specific year
            filtered_data = self.df[self.df['year'] == detected_year]
            period_info = f"Year {detected_year}"
        elif 'recent' in query_lower or 'lately' in query_lower:
            # Recent data
            max_date = self.df['date'].max()
            cutoff = max_date - pd.Timedelta(days=30)
            filtered_data = self.df[self.df['date'] >= cutoff]
            period_info = "Last 30 days"
        else:
            # All time
            filtered_data = self.df.copy()
            period_info = "All time"

        return filtered_data, period_info

    def _get_favorite_song(self, filtered_data, period_info):
        """Get favorite song for the filtered period"""
        if filtered_data.empty:
            return {
                'query': f'favorite song in {period_info}',
                'analysis_type': 'favorite_song',
                'data': {'error': f'No data found for {period_info}'},
                'period_info': period_info
            }

        top_song = filtered_data['master_metadata_track_name'].value_counts().index[0]
        play_count = filtered_data['master_metadata_track_name'].value_counts().iloc[0]
        artist = filtered_data[filtered_data['master_metadata_track_name'] == top_song]['master_metadata_album_artist_name'].iloc[0]

        return {
            'query': f'favorite song in {period_info}',
            'analysis_type': 'favorite_song',
            'data': {
                'top_songs': {top_song: play_count},
                'artist': artist,
                'period': period_info
            },
            'period_info': period_info
        }
    def _get_favorite_genre(self, filtered_data, period_info):
        """Get favorite genre for the filtered period"""
        if filtered_data.empty:
            return {
                "query": f"favorite genre in {period_info}",
                "analysis_type": "favorite_genre",
                "data": {"error": f"No data found for {period_info}"},
                "period_info": period_info
            }

        # Check if genres column exists
        if "genres" not in filtered_data.columns:
            return {
                "query": f"favorite genre in {period_info}",
                "analysis_type": "favorite_genre",
                "data": {"error": "No genre data available"},
                "period_info": period_info
            }

        # Extract all genres from the period
        all_genres = []
        for genres_str in filtered_data["genres"]:
            if genres_str and genres_str != "Unknown":
                # Split genres and add to list
                genres = [genre.strip() for genre in genres_str.split(",")]
                all_genres.extend(genres)

        if not all_genres:
            return {
                "query": f"favorite genre in {period_info}",
                "analysis_type": "favorite_genre", 
                "data": {"error": f"No genre data found for {period_info}"},
                "period_info": period_info
            }

        # Count genres
        genre_counts = pd.Series(all_genres).value_counts()
        top_genre = genre_counts.index[0]
        track_count = genre_counts.iloc[0]

        return {
            "query": f"favorite genre in {period_info}",
            "analysis_type": "favorite_genre",
            "data": {
                "top_genre": top_genre,
                "track_count": track_count,
                "top_genres": genre_counts.head(5).to_dict(),
                "period": period_info
            },
            "period_info": period_info
        }

    def _get_multiple_favorites(self, filtered_data, period_info, requested_types):
        """Get multiple favorites (song, artist, genre) at once"""
        if filtered_data.empty:
            return {
                'query': f'multiple favorites in {period_info}',
                'analysis_type': 'multiple_favorites',
                'data': {'error': f'No data found for {period_info}'},
                'period_info': period_info
            }

        results = {}

        # Get top song
        if 'song' in requested_types:
            top_song = filtered_data['master_metadata_track_name'].value_counts().index[0]
            song_count = filtered_data['master_metadata_track_name'].value_counts().iloc[0]
            song_artist = filtered_data[filtered_data['master_metadata_track_name'] == top_song]['master_metadata_album_artist_name'].iloc[0]
            results['top_song'] = {
                'name': top_song,
                'artist': song_artist,
                'plays': song_count
            }

        # Get top artist
        if 'artist' in requested_types:
            top_artist = filtered_data['master_metadata_album_artist_name'].value_counts().index[0]
            artist_count = filtered_data['master_metadata_album_artist_name'].value_counts().iloc[0]
            results['top_artist'] = {
                'name': top_artist,
                'plays': artist_count
            }

        # Get top genre
        if 'genre' in requested_types and 'genres' in filtered_data.columns:
            all_genres = []
            for genres_str in filtered_data['genres']:
                if genres_str and genres_str != 'Unknown':
                    genres = [genre.strip() for genre in genres_str.split(',')]
                    all_genres.extend(genres)

            if all_genres:
                genre_counts = pd.Series(all_genres).value_counts()
                top_genre = genre_counts.index[0]
                genre_count = genre_counts.iloc[0]
                results['top_genre'] = {
                    'name': top_genre,
                    'tracks': genre_count
                }

        return {
            'query': f'multiple favorites in {period_info}',
            'analysis_type': 'multiple_favorites',
            'data': results,
            'period_info': period_info
        }

    def _generate_artist_name_variations(self, artist_name):
        """Generate common variations of an artist name"""
        variations = []
        words = artist_name.split()

        if len(words) >= 2:
            # Try with periods after first letter: "j cole" -> "j. cole"
            first_initial = words[0][0].upper() + "."
            variations.append(f"{first_initial} {' '.join(words[1:])}")

            # Try capitalized version: "tyla" -> "Tyla"
            variations.append(" ".join(word.capitalize() for word in words))

            # Try all caps: "tyla" -> "TYLA"
            variations.append(" ".join(word.upper() for word in words))

            # Try with "The" prefix: "weeknd" -> "The Weeknd"
            variations.append(f"The {' '.join(words).title()}")

        else:
            # Single word artist
            word = words[0]
            # Try capitalized
            variations.append(word.capitalize())
            # Try all caps
            variations.append(word.upper())
            # Try with "The" prefix
            variations.append(f"The {word.capitalize()}")

        return variations

    def _get_first_song_by_artist(self, filtered_data, period_info, artist_name):
        """Get the first song listened to by a specific artist"""
        # Filter data for this artist - try multiple matching strategies
        artist_data = filtered_data[
            filtered_data['master_metadata_album_artist_name'].str.contains(artist_name, case=False, na=False)
        ]

        # If no exact match, try common name variations
        if artist_data.empty:
            variations = self._generate_artist_name_variations(artist_name)
            for variation in variations:
                artist_data = filtered_data[
                    filtered_data['master_metadata_album_artist_name'].str.contains(variation, case=False, na=False)
                ]
                if not artist_data.empty:
                    break

        if artist_data.empty:
            return {
                'query': f'first {artist_name} song',
                'analysis_type': 'first_song',
                'data': {'error': f'No songs found for {artist_name}'},
                'period_info': period_info
            }

        # Get the actual artist name from the data
        actual_artist_name = artist_data['master_metadata_album_artist_name'].iloc[0]

        # Find the earliest song by this artist
        first_song = artist_data.loc[artist_data['ts'].idxmin()]

        return {
            'query': f'first {artist_name} song',
            'analysis_type': 'first_song',
            'data': {
                'artist': actual_artist_name,
                'song': first_song['master_metadata_track_name'],
                'date': first_song['ts'].strftime('%B %d, %Y'),
                'time': first_song['ts'].strftime('%H:%M'),
                'timestamp': first_song['ts'].isoformat()
            },
            'period_info': period_info
        }

    def _get_first_song_by_genre(self, filtered_data, period_info, genre_name):
        """Get the first song listened to in a specific genre"""
        if 'genres' not in filtered_data.columns:
            return {
                'query': f'first {genre_name} song',
                'analysis_type': 'first_song',
                'data': {'error': 'No genre data available'},
                'period_info': period_info
            }

        # Filter data for this genre
        genre_data = filtered_data[
            filtered_data['genres'].str.contains(genre_name, case=False, na=False)
        ]

        if genre_data.empty:
            return {
                'query': f'first {genre_name} song',
                'analysis_type': 'first_song',
                'data': {'error': f'No songs found for genre {genre_name}'},
                'period_info': period_info
            }

        # Find the earliest song in this genre
        first_song = genre_data.loc[genre_data['ts'].idxmin()]

        return {
            'query': f'first {genre_name} song',
            'analysis_type': 'first_song',
            'data': {
                'genre': genre_name,
                'song': first_song['master_metadata_track_name'],
                'artist': first_song['master_metadata_album_artist_name'],
                'date': first_song['ts'].strftime('%B %d, %Y'),
                'time': first_song['ts'].strftime('%H:%M'),
                'timestamp': first_song['ts'].isoformat()
            },
            'period_info': period_info
        }

    def _get_last_song_by_artist(self, filtered_data, period_info, artist_name):
        """Get the last song listened to by a specific artist"""
        # Filter data for this artist - try multiple matching strategies
        artist_data = filtered_data[
            filtered_data['master_metadata_album_artist_name'].str.contains(artist_name, case=False, na=False)
        ]

        # If no exact match, try common name variations
        if artist_data.empty:
            variations = self._generate_artist_name_variations(artist_name)
            for variation in variations:
                artist_data = filtered_data[
                    filtered_data['master_metadata_album_artist_name'].str.contains(variation, case=False, na=False)
                ]
                if not artist_data.empty:
                    break

        if artist_data.empty:
            return {
                'query': f'last {artist_name} song',
                'analysis_type': 'last_song',
                'data': {'error': f'No songs found for {artist_name}'},
                'period_info': period_info
            }

        # Get the actual artist name from the data
        actual_artist_name = artist_data['master_metadata_album_artist_name'].iloc[0]

        # Find the latest song by this artist
        last_song = artist_data.loc[artist_data['ts'].idxmax()]

        return {
            'query': f'last {artist_name} song',
            'analysis_type': 'last_song',
            'data': {
                'artist': actual_artist_name,
                'song': last_song['master_metadata_track_name'],
                'date': last_song['ts'].strftime('%B %d, %Y'),
                'time': last_song['ts'].strftime('%H:%M'),
                'timestamp': last_song['ts'].isoformat()
            },
            'period_info': period_info
        }

    def _get_last_song_by_genre(self, filtered_data, period_info, genre_name):
        """Get the last song listened to in a specific genre"""
        if 'genres' not in filtered_data.columns:
            return {
                'query': f'last {genre_name} song',
                'analysis_type': 'last_song',
                'data': {'error': 'No genre data available'},
                'period_info': period_info
            }

        # Filter data for this genre
        genre_data = filtered_data[
            filtered_data['genres'].str.contains(genre_name, case=False, na=False)
        ]

        if genre_data.empty:
            return {
                'query': f'last {genre_name} song',
                'analysis_type': 'last_song',
                'data': {'error': f'No songs found for genre {genre_name}'},
                'period_info': period_info
            }

        # Find the latest song in this genre
        last_song = genre_data.loc[genre_data['ts'].idxmax()]

        return {
            'query': f'last {genre_name} song',
            'analysis_type': 'last_song',
            'data': {
                'genre': genre_name,
                'song': last_song['master_metadata_track_name'],
                'artist': last_song['master_metadata_album_artist_name'],
                'date': last_song['ts'].strftime('%B %d, %Y'),
                'time': last_song['ts'].strftime('%H:%M'),
                'timestamp': last_song['ts'].isoformat()
            },
            'period_info': period_info
        }

    def _get_artist_songs(self, filtered_data, period_info, artist_name):
        """Get top songs for a specific artist"""
        # Filter data for this artist - try multiple matching strategies
        artist_data = filtered_data[
            filtered_data['master_metadata_album_artist_name'].str.contains(artist_name, case=False, na=False)
        ]

        # If no exact match, try common name variations
        if artist_data.empty:
            variations = self._generate_artist_name_variations(artist_name)

            for variation in variations:
                artist_data = filtered_data[
                    filtered_data['master_metadata_album_artist_name'].str.contains(variation, case=False, na=False)
                ]
                if not artist_data.empty:
                    break

        if artist_data.empty:
            return {
                'query': f'{artist_name} songs in {period_info}',
                'analysis_type': 'artist_songs',
                'data': {'error': f'No songs found for {artist_name} in {period_info}'},
                'period_info': period_info
            }

        # Get the actual artist name from the data
        actual_artist_name = artist_data['master_metadata_album_artist_name'].iloc[0]

        # Get top songs for this artist
        top_songs = artist_data['master_metadata_track_name'].value_counts().head(10).to_dict()

        return {
            'query': f'{artist_name} songs in {period_info}',
            'analysis_type': 'artist_songs',
            'data': {
                'artist': actual_artist_name,
                'top_songs': top_songs,
                'total_plays': len(artist_data),
                'total_hours': artist_data['hours_played'].sum() if 'hours_played' in artist_data.columns else 0
            },
            'period_info': period_info
        }

    def _extract_top_genres(self, data, limit=5):
        """Extract top genres from filtered data"""
        if data.empty or "genres" not in data.columns:
            return {}

        all_genres = []
        for genres_str in data["genres"]:
            if genres_str and genres_str != "Unknown":
                genres = [genre.strip() for genre in genres_str.split(",")]
                all_genres.extend(genres)

        if not all_genres:
            return {}

        return pd.Series(all_genres).value_counts().head(limit).to_dict()

    def _get_daily_listening(self, filtered_data, period_info):
        """Get detailed listening info for a specific day/period"""
        if filtered_data.empty:
            return {
                "query": f"listening on {period_info}",
                "analysis_type": "daily_listening",
                "data": {"error": f"No listening data found for {period_info}"},
                "period_info": period_info
            }

        # If its a single day, show chronological order
        if len(filtered_data["date"].unique()) == 1:
            daily_tracks = filtered_data.sort_values("ts")
            tracks_list = []
            for _, track in daily_tracks.iterrows():
                tracks_list.append({
                    "time": track["ts"].strftime("%H:%M"),
                    "song": track["master_metadata_track_name"],
                    "artist": track["master_metadata_album_artist_name"]
                })

            return {
                "query": f"listening on {period_info}",
                "analysis_type": "daily_listening",
                "data": {
                    "date": period_info,
                    "total_tracks": len(filtered_data),
                    "total_hours": filtered_data["hours_played"].sum(),
                    "tracks_chronological": tracks_list[:20],  # Limit to first 20
                    "top_artist_that_day": filtered_data["master_metadata_album_artist_name"].value_counts().index[0],
                    "most_played_song": filtered_data["master_metadata_track_name"].value_counts().index[0]
                },
                "period_info": period_info
            }
        else:
            # Multiple days - show summary
            return {
                "query": f"listening in {period_info}",
                "analysis_type": "period_summary",
                "data": {
                    "stats": {
                        "total_plays": len(filtered_data),
                        "total_hours": filtered_data["hours_played"].sum(),
                        "unique_artists": filtered_data["master_metadata_album_artist_name"].nunique(),
                        "unique_songs": filtered_data["master_metadata_track_name"].nunique()
                    },
                    "top_artists": filtered_data["master_metadata_album_artist_name"].value_counts().head(5).to_dict(),
                    "top_songs": filtered_data["master_metadata_track_name"].value_counts().head(5).to_dict(),
                    "top_genres": self._extract_top_genres(filtered_data, 5),
                    "time_patterns": {
                        "peak_listening_hour": filtered_data.groupby(filtered_data["ts"].dt.hour).size().idxmax() if not filtered_data.empty else 0,
                        "peak_listening_day": filtered_data.groupby(filtered_data["ts"].dt.day_name()).size().idxmax() if not filtered_data.empty else "Unknown"
                    }
                },
                "period_info": period_info
            }
