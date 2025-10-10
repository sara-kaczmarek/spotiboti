import streamlit as st
import json
import pandas as pd
import random
import os
from spotify_data_query import SpotifyDataQuery
from spotiboti_memory import SpotiBotiMemory

# Import Groq
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    st.error("Groq library not installed. Please run: pip install groq")

class SpotifyChatbot:
    def __init__(self):
        self.load_data()
        self.analyzer = SpotifyDataQuery()
        self.memory = SpotiBotiMemory()

        # Initialize Groq client
        self.groq_client = None
        groq_api_key = os.getenv('GROQ_API_KEY')

        # Try to get from Streamlit secrets if not in environment
        if not groq_api_key:
            try:
                groq_api_key = st.secrets["GROQ_API_KEY"]
            except:
                pass

        if groq_api_key and GROQ_AVAILABLE:
            self.groq_client = Groq(api_key=groq_api_key)
        elif not groq_api_key:
            st.warning("⚠️ Groq API key not found. Please set GROQ_API_KEY in environment variables or Streamlit secrets.")

        # Initialize session
        if "spotiboti_session_started" not in st.session_state:
            self.memory.increment_session()
            st.session_state.spotiboti_session_started = True

        # Fun loading messages for music contextual queries
        self.music_loading_messages = [
            "🎤 Singing through your playlist...",
            "💃 Dancing through your data...",
            "🎸 Strumming through your stats...",
            "🎹 Playing the keys to your music taste...",
            "🎵 Composing your musical story...",
            "🎼 Writing songs about your listening habits...",
            "🎺 Jamming with your favorite tracks...",
            "🥁 Drumming up your music insights...",
            "🎻 Orchestrating your audio adventure...",
            "🎶 Harmonizing your hit parade...",
            "🎤 Performing an encore of your top tunes...",
            "🎸 Rocking out to your rhythm...",
            "🎧 Tuning into your musical memories...",
            "🎵 Serenading your Spotify secrets...",
            "💿 Spinning through your sound story...",
            "🎭 Setting the stage for your music tale...",
            "🎪 Conducting a symphony of your streams...",
            "🎨 Painting a portrait of your playlists...",
            "🌟 Starring in the musical of your memories...",
            "🎬 Directing the soundtrack of your life..."
        ]


    def load_data(self):
        try:
            with open('data/enriched_spotify_data.json', 'r') as f:
                self.spotify_data = json.load(f)
            self.df = pd.DataFrame(self.spotify_data)
            self.df['ts'] = pd.to_datetime(self.df['ts'])
        except Exception as e:
            self.spotify_data = None
            self.df = None
            st.error(f"Could not load spotify data: {e}")



    def get_relevant_data_for_query(self, query):
        """Get relevant data using the analyzer"""
        try:
            return self.analyzer.analyze_query(query)
        except Exception as e:
            print(f"Error analyzing query: {e}")
            return None

    def query_ollama_with_constrained_data(self, user_query, analysis_result):
        """Query Ollama with analyzed music data"""
        try:
            # Get recent chat history for context
            chat_context = ""
            if hasattr(st.session_state, 'chat_history') and st.session_state.chat_history:
                recent_history = st.session_state.chat_history[-6:]  # Last 6 messages
                for chat in recent_history:
                    role = "Sara" if chat["role"] == "user" else "SpotiBoti"
                    chat_context += f"{role}: {chat['message']}\n"

            # Handle intelligent structured responses
            if analysis_result.get('analysis_type') == 'intelligent_structured':
                if 'error' in analysis_result.get('data', {}):
                    return f"I couldn't process your query: {analysis_result['data']['error']}"

                # Use the built-in formatter
                return self.analyzer.format_response(analysis_result)

            # Handle error in analysis
            if 'error' in analysis_result.get('data', {}):
                return f"I couldn't find data for your query: {analysis_result['data']['error']}"

            data = analysis_result['data']
            period_info = analysis_result.get('period_info', 'All time')
            analysis_type = analysis_result.get('analysis_type', 'general')

            # Format the analyzed data into readable context
            if analysis_type == 'artist_timeline':
                # Special formatting for artist timeline
                artist_name = data['artist_name']
                context = f"""Sara's {artist_name} Listening Journey ({period_info}):

Timeline Overview:
- First listened: {data['first_date']}
- First song: {data['first_song']}
- Last listened: {data['last_date']}
- Last song: {data['last_song']}
- Peak year: {data['peak_year']} ({data['peak_plays']} plays)
- Total plays ever: {data['total_plays']:,}
- Active listening years: {data['active_years']} years

Year-by-Year Breakdown:
"""
                for year, stats in data['yearly_breakdown'].items():
                    context += f"\n{year}:"
                    context += f"\n  - Plays: {stats['plays']:,}"
                    context += f"\n  - Hours: {stats['hours']:.1f}"
                    context += f"\n  - Months active: {stats['months_active']}"
                    context += f"\n  - Top song: {stats['top_song']}"

                context += f"\nListening Pattern: {data['listening_journey']}"
                if data['decline_year']:
                    context += f"\nSignificant decline detected: {data['decline_year']}"

                context += f"\n\nTop Songs Overall:"
                for i, (song, count) in enumerate(list(data['top_songs_overall'].items()), 1):
                    context += f"\n{i}. {song}: {count} plays"

            elif analysis_type == 'genre_evolution':
                # Special formatting for genre evolution
                context = f"""Sara's Genre Evolution Over Time ({period_info}):

Overall Genre Distribution:
"""
                for i, (genre, count) in enumerate(list(data['overall_top_genres'].items())[:8], 1):
                    context += f"{i}. {genre}: {count} total tracks\n"

                context += "\nYear-by-Year Genre Journey:\n"
                for year, summary in data['year_summaries'].items():
                    context += f"\n{year}:"
                    context += f"\n  - Dominant genre: {summary['top_genre']}"
                    context += f"\n  - Total tracks: {summary['total_tracks']:,}"
                    context += f"\n  - Genre diversity: {summary['genre_diversity']} different genres"
                    context += f"\n  - Top genres that year: "
                    for genre, count in list(summary['genre_breakdown'].items())[:3]:
                        context += f"{genre} ({count}), "
                    context = context.rstrip(', ') + "\n"

                context += f"\nMusical Journey Summary:"
                context += f"\n- Active listening years: {data['years_active']} years ({data['first_year']}-{data['last_year']})"
                context += f"\n- Total unique genres explored: {len(data['overall_top_genres'])}"

            elif analysis_type == 'song_by_artist':
                # Handle specific song by artist queries
                if 'error' in data:
                    context = f"Sara's Listening Data: {data['error']}"
                else:
                    song_data = data
                    context = f"""Sara's Listening Data for "{song_data['song']}" by {song_data['artist']}:

First listened: {song_data['first_listen_date']} at {song_data['first_listen_time']}
Last listened: {song_data['last_listen_date']}
Total plays: {song_data['total_plays']:,}
Listening period: {song_data['listening_span']}"""

            elif analysis_type == 'song_info':
                # Handle song-specific queries
                song_data = data
                context = f"""Song Information for Sara:

Song: {song_data['song']}
Artist: {song_data['artist']}
Date: {song_data['date']}
Context: {song_data['context']}"""

            elif analysis_type == 'date_info':
                # Handle date/time specific queries
                date_data = data
                context = f"""Date Information for {date_data['artist']}:

First listened: {date_data['first_date']} at {date_data['first_time']}
Last listened: {date_data['last_date']} at {date_data['last_time']}"""

            elif analysis_type == 'quantity_info':
                # Handle quantity/frequency queries
                qty_data = data
                context = f"""Listening Statistics for {qty_data['artist']}:

Total plays: {qty_data['total_plays']:,}
Total hours: {qty_data['total_hours']} hours
Unique songs: {qty_data['unique_songs']}
Average per month: {qty_data['avg_per_month']} plays"""

            elif analysis_type == 'favorite_song':
                # Handle favorite song queries
                if 'error' in data:
                    context = f"Sara's Listening Data: {data['error']}"
                elif 'top_songs' in data and data['top_songs']:
                    top_song = list(data['top_songs'].keys())[0]
                    play_count = list(data['top_songs'].values())[0]
                    artist = data.get('artist', 'Unknown Artist')
                    context = f"""Sara's favorite song in {period_info} was "{top_song}" by {artist} with {play_count} plays.

Additional context:
- This was Sara's #1 most played song during {period_info}
- Total plays: {play_count}
- Artist: {artist}"""
                else:
                    context = f"No song data found for {period_info}"

            elif analysis_type == 'favorite_artist':
                # Handle favorite artist queries
                if 'top_artists' in data and data['top_artists']:
                    top_artist = list(data['top_artists'].keys())[0]
                    play_count = list(data['top_artists'].values())[0]
                    context = f"""Sara's favorite artist in {period_info} was {top_artist} with {play_count} plays.

Additional context:
- This was Sara's #1 most played artist during {period_info}
- Total plays: {play_count}"""
                else:
                    context = f"No artist data found for {period_info}"

            elif analysis_type == 'favorite_genre':
                # Handle favorite genre queries
                if 'error' in data:
                    context = f"Sara's Listening Data: {data['error']}"
                elif 'top_genre' in data:
                    top_genre = data['top_genre']
                    track_count = data['track_count']
                    context = f"""Sara's favorite genre in {period_info} was {top_genre} with {track_count} tracks.

Additional context:
- This was Sara's #1 most listened genre during {period_info}
- Total tracks in this genre: {track_count}

Top 5 genres for this period:"""
                    for i, (genre, count) in enumerate(list(data['top_genres'].items())[:5], 1):
                        context += f"\n{i}. {genre}: {count} tracks"
                else:
                    context = f"No genre data found for {period_info}"

            elif analysis_type == 'multiple_favorites':
                # Handle multiple favorites queries (song + artist, etc.)
                if 'error' in data:
                    context = f"Sara's Listening Data: {data['error']}"
                else:
                    context = f"Sara's top favorites for {period_info}:\n\n"
                    if 'top_song' in data:
                        song = data['top_song']
                        context += f"🎵 Top Song: \"{song['name']}\" by {song['artist']} ({song['plays']} plays)\n"
                    if 'top_artist' in data:
                        artist = data['top_artist']
                        context += f"🎤 Top Artist: {artist['name']} ({artist['plays']} plays)\n"
                    if 'top_genre' in data:
                        genre = data['top_genre']
                        context += f"🎶 Top Genre: {genre['name']} ({genre['tracks']} tracks)\n"

                    context += f"\nPeriod: {period_info}"

            elif analysis_type == 'daily_listening':
                # Handle daily listening queries
                if 'error' in data:
                    context = f"Sara's Listening Data: {data['error']}"
                else:
                    context = f"""Sara's listening on {data['date']}:

Total tracks: {data['total_tracks']}
Total hours: {data['total_hours']:.1f}
Top artist that day: {data['top_artist_that_day']}
Most played song: {data['most_played_song']}

Chronological listening history:"""
                    for track in data['tracks_chronological']:
                        context += f"\n{track['time']} - {track['song']} by {track['artist']}"

            elif analysis_type == 'first_song':
                # Handle first song queries
                if 'error' in data:
                    context = f"Sara's Listening Data: {data['error']}"
                else:
                    if 'artist' in data:
                        # First song by artist
                        context = f"""Sara's first {data['artist']} song:

Song: "{data['song']}"
Artist: {data['artist']}
Date: {data['date']} at {data['time']}

This was the very first time Sara listened to {data['artist']} in her Spotify history."""
                    elif 'genre' in data:
                        # First song in genre
                        context = f"""Sara's first {data['genre']} song:

Song: "{data['song']}" by {data['artist']}
Genre: {data['genre']}
Date: {data['date']} at {data['time']}

This was the very first time Sara listened to a {data['genre']} song in her Spotify history."""
                    else:
                        context = f"Sara's first song data: {data}"

            elif analysis_type == 'last_song':
                # Handle last song queries
                if 'error' in data:
                    context = f"Sara's Listening Data: {data['error']}"
                else:
                    if 'artist' in data:
                        # Last song by artist
                        context = f"""Sara's most recent {data['artist']} song:

Song: "{data['song']}"
Artist: {data['artist']}
Date: {data['date']} at {data['time']}

This was the most recent time Sara listened to {data['artist']} in her Spotify history."""
                    elif 'genre' in data:
                        # Last song in genre
                        context = f"""Sara's most recent {data['genre']} song:

Song: "{data['song']}" by {data['artist']}
Genre: {data['genre']}
Date: {data['date']} at {data['time']}

This was the most recent time Sara listened to a {data['genre']} song in her Spotify history."""
                    else:
                        context = f"Sara's last song data: {data}"

            elif analysis_type == 'artist_songs':
                # Handle artist-specific song queries
                if 'error' in data:
                    context = f"Sara's Listening Data: {data['error']}"
                else:
                    artist = data['artist']
                    context = f"""Sara's favorite {artist} songs for {period_info}:

Top songs by {artist}:
"""
                    for i, (song, plays) in enumerate(list(data['top_songs'].items())[:10], 1):
                        context += f"{i}. {song}: {plays} plays\n"

                    context += f"""
Total {artist} plays: {data['total_plays']:,}
Total {artist} listening time: {data['total_hours']:.1f} hours"""

            elif analysis_type == 'period_summary':
                # Handle period summary queries (months, years, etc.)
                context = f"""Sara's listening summary for {period_info}:

Basic Stats:
- Total plays: {data['stats']['total_plays']:,}
- Total hours: {data['stats']['total_hours']:.1f}
- Unique artists: {data['stats']['unique_artists']:,}
- Unique songs: {data['stats']['unique_songs']:,}
- Peak listening hour: {data['time_patterns']['peak_listening_hour']}:00
- Peak listening day: {data['time_patterns']['peak_listening_day']}

Top 5 Artists:
"""
                for i, (artist, count) in enumerate(list(data['top_artists'].items())[:5], 1):
                    context += f"{i}. {artist}: {count} plays\n"

                context += "\nTop 5 Songs:\n"
                for i, (song, count) in enumerate(list(data['top_songs'].items())[:5], 1):
                    context += f"{i}. {song}: {count} plays\n"

                if data['top_genres']:
                    context += "\nTop 5 Genres:\n"
                    for i, (genre, count) in enumerate(list(data['top_genres'].items())[:5], 1):
                        context += f"{i}. {genre}: {count} tracks\n"

            elif analysis_type == 'detailed_info':
                # Handle requests for more information
                detail_data = data
                context = f"""Detailed Information for {detail_data['artist']}:

Total plays: {detail_data['total_plays']:,}
Date range: {detail_data['date_range']}
Peak listening hour: {detail_data['peak_listening_hour']}

Top Songs:"""
                for song, count in detail_data['top_songs'].items():
                    context += f"\n- {song}: {count} plays"

                context += "\n\nListening by year:"
                for year, plays in detail_data['listening_by_year'].items():
                    context += f"\n- {year}: {plays} plays"

            else:
                # Regular formatting for other queries
                context = f"""Sara's Spotify Listening Data for {period_info}:

Basic Stats:
- Total plays: {data['stats']['total_plays']:,}
- Total hours: {data['stats'].get('total_hours', 0):.1f}
- Unique artists: {data['stats'].get('unique_artists', 0):,}
- Unique songs: {data['stats'].get('unique_songs', 0):,}
- Date range: {data['stats'].get('date_range', 'Unknown')}
- Average daily hours: {data['stats'].get('avg_daily_hours', 0):.1f}
- Most active day: {data['stats'].get('most_active_day', 'Unknown')}
- Most active hour: {data['stats'].get('most_active_hour', 0)}:00

Top 10 Artists:
"""
                for i, (artist, count) in enumerate(list(data['top_artists'].items())[:10], 1):
                    context += f"{i}. {artist}: {count} plays\n"

                context += "\nTop 10 Songs:\n"
                for i, (song, count) in enumerate(list(data['top_songs'].items())[:10], 1):
                    context += f"{i}. {song}: {count} plays\n"

                if data['top_genres']:
                    context += "\nTop Genres:\n"
                    for i, (genre, count) in enumerate(list(data['top_genres'].items())[:5], 1):
                        context += f"{i}. {genre}: {count} tracks\n"

                # Add time patterns
                context += "\nListening Patterns:\n"
                context += f"Peak listening hour: {data['time_patterns']['peak_listening_hour']}:00\n"
                context += f"Peak listening day: {data['time_patterns']['peak_listening_day']}\n"

            prompt = f"""You are SpotiBoti, Sara's personal Spotify AI assistant. Answer using ONLY the data provided below.

Previous conversation context:
{chat_context}

Current Question: {user_query}

SARA'S ACTUAL LISTENING DATA:
{context}

STRICT RULES - NO EXCEPTIONS:
1. Only reference songs, artists, dates, play counts, and statistics from the data above
2. If the data shows an error message, report that exact error - do not make up alternative information
3. Never guess, estimate, or make up any numbers, dates, or music details
4. Every statistic, artist name, or song title you mention MUST appear in the data above
5. If asked about something not in the data, explicitly say you don't have that information
6. Be engaging and conversational, but stick strictly to the provided facts
7. When you DO have the data, be confident and natural - don't apologize or say "that's all I have"
8. Answer directly and enthusiastically when the data is available
9. CRITICAL: If the data contains an error about a song not existing, never make up alternative dates or information

Response:"""

            # Use Groq API
            if not self.groq_client:
                return "⚠️ SpotiBoti is not configured. Please contact the administrator to add a Groq API key."

            # Use Llama model on Groq
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are SpotiBoti, Sara's personal Spotify AI assistant. Answer using ONLY the data provided."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model="llama-3.3-70b-versatile",  # Groq's Llama model
                temperature=0.7,
                max_tokens=1024
            )

            return chat_completion.choices[0].message.content

        except Exception as e:
            return f"Error connecting to Groq API: {str(e)}"

    def get_available_models(self):
        """Get list of available Groq models"""
        # Available Groq models (2025)
        return [
            'llama-3.3-70b-versatile',
            'llama-3.1-8b-instant',
            'qwen/qwen3-32b'
        ]

    def query_groq_general(self, user_query):
        """Query Groq for general questions (no music context)"""
        try:
            # Get recent chat history for context
            chat_context = ""
            if hasattr(st.session_state, 'chat_history') and st.session_state.chat_history:
                recent_history = st.session_state.chat_history[-6:]  # Last 6 messages
                for chat in recent_history:
                    role = "Sara" if chat["role"] == "user" else "SpotiBoti"
                    chat_context += f"{role}: {chat['message']}\n"

            prompt = f"""You are SpotiBoti, Sara's helpful AI assistant. Answer her question naturally and conversationally.

Previous conversation context:
{chat_context}

Current Question: {user_query}

IMPORTANT RULES:
- You are SpotiBoti, Sara's AI assistant - do NOT pretend to be Sara or speak as "we"
- NEVER make up or hallucinate any music data, listening patterns, or personal details
- If you don't know something, clearly say "I don't know" - do NOT guess or make things up
- Be helpful, friendly, and conversational but stay within your role as an AI assistant
- Apply any feedback Sara has given you about how to respond
- Do not pretend to have experiences or memories you don't have

Response:"""

            # Use Groq API
            if not self.groq_client:
                return "⚠️ SpotiBoti is not configured. Please contact the administrator to add a Groq API key."

            model = getattr(self, 'selected_model', 'llama-3.3-70b-versatile')
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are SpotiBoti, Sara's helpful AI assistant."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=model,
                temperature=0.7,
                max_tokens=1024
            )

            return chat_completion.choices[0].message.content

        except Exception as e:
            return f"Error connecting to Groq API: {str(e)}"

    def render_chat_interface(self):
        # Set default model (no selector dropdown)
        self.selected_model = 'llama-3.3-70b-versatile'

        # Top controls
        col1, col2 = st.columns([3, 1])
        with col1:
            pass  # Remove the header since it's now on the main page

        with col2:
            # Teaching SpotiBoti info
            with st.expander("💡 Teaching SpotiBoti", expanded=False):
                st.info("💬 **Natural Feedback**: Just use the word 'feedback' in your message to teach SpotiBoti!")
                st.write("Examples:")
                st.code('feedback: I prefer more detailed artist stories')
                st.code('feedback: that response was too short')
                st.code('feedback: I love when you mention my data background')

            # Clear chat button and memory info
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Clear Chat", help="Clear chat history"):
                    st.session_state.chat_history = []
                    st.rerun()

            with col2:
                memory_stats = self.memory.get_memory_stats()
                st.caption(f"🧠 Memory: {memory_stats['total_insights']} insights, {memory_stats['total_feedback']} feedback")

        # Initialize chat history
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        # Display chat history in proper chat containers
        chat_container = st.container()
        with chat_container:
            for chat in st.session_state.chat_history:
                if chat["role"] == "user":
                    with st.chat_message("user"):
                        st.write(chat["message"])
                else:
                    with st.chat_message("assistant"):
                        st.write(f"**SpotiBoti:** {chat['message']}")


        # Simple chat styling - static positioning
        st.markdown("""
        <style>
        /* Remove any fixed positioning and just use normal flow */
        .stChatInputContainer {
            position: static !important;
            bottom: auto !important;
            left: auto !important;
            right: auto !important;
            width: 100% !important;
            z-index: auto !important;
            padding: 10px 0 !important;
        }

        /* Reset any forced padding */
        body, .main, .main .block-container, .stApp > div {
            padding-bottom: 0 !important;
        }

        /* Clean up chat input styling */
        .stChatInput {
            margin-bottom: 20px !important;
        }
        </style>
        """, unsafe_allow_html=True)

        # Chat input at the bottom
        user_input = st.chat_input("Ask about your music or anything else...")


        if user_input:
            # Check if this is feedback
            is_feedback = user_input.lower().startswith('feedback:') or 'feedback:' in user_input.lower()

            # Add user message to history
            st.session_state.chat_history.append({"role": "user", "message": user_input})

            # Show user message immediately
            with st.chat_message("user"):
                st.write(user_input)

            # Show assistant response with streaming effect
            with st.chat_message("assistant"):
                message_placeholder = st.empty()

                if is_feedback:
                    # Handle feedback message
                    feedback_text = user_input.replace('feedback:', '').strip()

                    # Determine feedback type from content
                    feedback_lower = feedback_text.lower()
                    if any(word in feedback_lower for word in ['good', 'great', 'love', 'perfect', 'excellent', 'like']):
                        feedback_type = 'positive'
                    elif any(word in feedback_lower for word in ['wrong', 'incorrect', 'actually', 'correction']):
                        feedback_type = 'correction'
                    elif any(word in feedback_lower for word in ['bad', 'terrible', 'awful', 'hate', 'don\'t like']):
                        feedback_type = 'negative'
                    else:
                        feedback_type = 'suggestion'

                    # Store feedback
                    if len(st.session_state.chat_history) >= 2:
                        last_response = st.session_state.chat_history[-2]["message"] if len(st.session_state.chat_history) >= 2 else ""
                        self.memory.add_user_feedback(
                            query="Previous conversation",
                            response=last_response,
                            feedback_type=feedback_type,
                            feedback_text=feedback_text
                        )

                    bot_response = f"Thanks for the feedback! I'll remember that you {feedback_text.lower()}. This will help me give you better responses in the future! 🧠✨"

                else:
                    # Always try to get relevant data first, then let LLM respond naturally
                    spinner_text = random.choice(self.music_loading_messages)
                    with st.spinner(spinner_text):
                        # Get relevant data for the query
                        analysis_result = self.get_relevant_data_for_query(user_input)
                        if analysis_result and analysis_result.get('data'):
                            # Use constrained LLM with data to prevent hallucination
                            bot_response = self.query_ollama_with_constrained_data(user_input, analysis_result)
                        else:
                            # No relevant data found - general response
                            bot_response = self.query_groq_general(user_input)

                # Display the response
                message_placeholder.write(f"**SpotiBoti:** {bot_response}")

            # Add assistant response to history
            st.session_state.chat_history.append({"role": "assistant", "message": bot_response})

            # Store conversation insight
            response_type = 'music_data' if (not is_feedback and 'analysis_result' in locals() and analysis_result and analysis_result.get('data')) else 'general'
            self.memory.add_conversation_insight(
                query=user_input,
                response_type=response_type,
                key_insights=[f"Answered query about: {user_input[:50]}..."]
            )

            # Force scroll to top to create space
            st.components.v1.html("""
            <script>
            window.parent.scrollTo({top: 0, behavior: 'smooth'});
            </script>
            """, height=0)