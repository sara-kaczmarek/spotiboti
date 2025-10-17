import streamlit as st
import pandas as pd
import plotly.express as px
import json
import glob
import os
from datetime import datetime, timedelta
import numpy as np
import sys
sys.path.append('..')
from spotify_api import SpotifyAPI
from shared_components import render_footer

# Page config
st.set_page_config(
    page_title="Streaming History",
    page_icon="https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/Spotify_logo_without_text.svg/512px-Spotify_logo_without_text.svg.png",
    layout="wide"
)

def load_enriched_data():
    """Load pre-enriched data with genres if available, build if missing"""
    # Use relative path from project root
    enriched_file = 'data/enriched_spotify_data.json'

    # If file doesn't exist, download from GitHub release (no building fallback)
    if not os.path.exists(enriched_file):
        st.info("📥 Enriched data file not found. Downloading from GitHub release...")

        try:
            from data_builder import download_enriched_data_from_release

            # Show progress
            progress_placeholder = st.empty()

            def progress_callback(msg):
                progress_placeholder.info(f"⏳ {msg}")

            # Download from release (no fallback to building)
            success = download_enriched_data_from_release(
                output_file=enriched_file,
                progress_callback=progress_callback
            )

            if success:
                progress_placeholder.success("✅ Enriched data downloaded successfully!")
            else:
                st.error("❌ Failed to download enriched data from GitHub release. Please check your internet connection or try again later.")
                return None

        except Exception as e:
            st.error(f"❌ Failed to download enriched data: {e}")
            return None

    # Load the enriched data
    if os.path.exists(enriched_file):
        with open(enriched_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        df['ts'] = pd.to_datetime(df['ts'], format='mixed')
        df['date'] = df['ts'].dt.date
        df['year'] = df['ts'].dt.year
        df['month'] = df['ts'].dt.month
        df['hour'] = df['ts'].dt.hour
        df['day_of_week'] = df['ts'].dt.day_name()
        df['minutes_played'] = df['ms_played'] / 60000
        df['hours_played'] = df['minutes_played'] / 60
        return df

    return None

def load_spotify_data(use_api=False, _spotify_api=None):
    """Load and process Spotify streaming data from JSON files and optionally API"""
    # Load historical data from JSON files
    data_dir = 'streaming_data'
    audio_files = glob.glob(os.path.join(data_dir, 'Streaming_History_Audio_*.json'))

    all_streams = []
    df_filtered = None

    # Load historical JSON data
    if audio_files:
        with st.sidebar:
            progress_bar = st.progress(0)
            status_text = st.empty()
            status_text.text("Loading data...")

        for i, file in enumerate(audio_files):
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_streams.extend(data)
            progress_bar.progress((i + 1) / len(audio_files))

        progress_bar.empty()
        status_text.empty()

        # Convert to DataFrame and clean
        df = pd.DataFrame(all_streams)
        df['ts'] = pd.to_datetime(df['ts'])
        df['date'] = df['ts'].dt.date
        df['year'] = df['ts'].dt.year
        df['month'] = df['ts'].dt.month
        df['hour'] = df['ts'].dt.hour
        df['day_of_week'] = df['ts'].dt.day_name()
        df['minutes_played'] = df['ms_played'] / 60000
        df['hours_played'] = df['minutes_played'] / 60

        # Filter short plays
        df_filtered = df[df['ms_played'] >= 30000].copy()


    # Load recent data from API if requested and available
    if use_api and _spotify_api and _spotify_api.sp:
        with st.sidebar:
            api_status = st.empty()
            api_status.text("Getting API data...")

        recent_df = _spotify_api.get_recently_played(limit=50)
        if recent_df is not None and not recent_df.empty:
            with st.sidebar:
                api_status.text("✅ API data loaded!")
                st.success(f"✅ +{len(recent_df)} recent")
            # Process API data to match JSON format
            recent_df['ts'] = pd.to_datetime(recent_df['ts'], format='ISO8601')
            recent_df['date'] = recent_df['ts'].dt.date
            recent_df['year'] = recent_df['ts'].dt.year
            recent_df['month'] = recent_df['ts'].dt.month
            recent_df['hour'] = recent_df['ts'].dt.hour
            recent_df['day_of_week'] = recent_df['ts'].dt.day_name()
            recent_df['minutes_played'] = recent_df['ms_played'] / 60000
            recent_df['hours_played'] = recent_df['minutes_played'] / 60

            # Combine with historical data if available
            if df_filtered is not None:
                # Remove duplicates based on timestamp and track name
                combined_df = pd.concat([df_filtered, recent_df], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=['ts', 'master_metadata_track_name'], keep='first')
                df_filtered = combined_df.sort_values('ts').reset_index(drop=True)
            else:
                df_filtered = recent_df

    if df_filtered is None:
        st.error("No Spotify data found! Please check your JSON files or API connection.")
        return None

    return df_filtered

# Create recent activity dashboard from API data only
def create_recent_dashboard(df, time_period, spotify_api=None):
    from datetime import datetime, timedelta

    # Parse time period
    hours_map = {
        "Last 6 hours": 6,
        "Last 12 hours": 12,
        "Last 24 hours": 24,
        "Last 48 hours": 48
    }
    hours = hours_map[time_period]

    # Get recent data from API only
    use_api = spotify_api is not None and spotify_api.sp
    if not use_api:
        st.warning("🔗 Enable Spotify API to see recent activity dashboard")
        st.info("This dashboard shows your real-time listening from the last 50 tracks")
        return

    recent_tracks = spotify_api.get_recently_played(limit=50)
    if recent_tracks is None or recent_tracks.empty:
        st.warning("No recent tracks available from Spotify API")
        return

    # Process the API data
    recent_tracks['ts'] = pd.to_datetime(recent_tracks['ts'], format='ISO8601')
    recent_tracks['hours_played'] = recent_tracks['ms_played'] / (60000 * 60)

    # Show time span info for the last 50 tracks
    oldest_track = recent_tracks['ts'].min()
    newest_track = recent_tracks['ts'].max()
    actual_span_hours = (newest_track - oldest_track).total_seconds() / 3600

    st.info(f"📅 **Your last 50 tracks span:** {actual_span_hours:.1f} hours "
            f"(from {oldest_track.strftime('%m/%d %H:%M')} to {newest_track.strftime('%m/%d %H:%M')})")

    # Filter for the selected time period
    now = datetime.now().replace(tzinfo=recent_tracks['ts'].dt.tz)
    cutoff_time = now - timedelta(hours=hours)
    recent_data = recent_tracks[recent_tracks['ts'] >= cutoff_time]

    if len(recent_data) == 0:
        st.warning(f"❌ No listening activity in the {time_period.lower()} (from your last 50 tracks)")
        st.info(f"💡 Your last 50 tracks only span {actual_span_hours:.1f} hours. Try selecting a shorter time period!")
        return

    # Show how much of the selected period has data
    coverage_pct = min(100, (actual_span_hours / hours) * 100)
    if coverage_pct < 100:
        st.warning(f"⚠️ Only {coverage_pct:.0f}% of the {time_period.lower()} has data from your last 50 tracks")

    # Add genres if available (from cache - should be fast)
    if spotify_api:
        recent_data = spotify_api.enrich_dataframe_with_genres(recent_data, show_progress=False)

    # Calculate historical baselines for all metrics
    def get_historical_baselines(df, hours):
        """Calculate average metrics for this time period historically"""
        # Sample periods of the same duration from historical data
        historical_data = {
            'tracks': [],
            'unique_artists': [],
            'unique_genres': [],
            'unique_songs': []
        }

        # Get last 30 periods of this duration for comparison
        for i in range(30):
            sample_end = df['ts'].max() - timedelta(days=i)
            sample_start = sample_end - timedelta(hours=hours)
            sample_data = df[(df['ts'] >= sample_start) & (df['ts'] <= sample_end)]

            if len(sample_data) > 0:
                historical_data['tracks'].append(len(sample_data))
                historical_data['unique_artists'].append(sample_data['master_metadata_album_artist_name'].nunique())
                historical_data['unique_songs'].append(sample_data['master_metadata_track_name'].nunique())

                # Count unique genres if available
                if 'genres' in sample_data.columns:
                    sample_genres = []
                    for genres_str in sample_data['genres']:
                        if genres_str and genres_str != 'Unknown':
                            sample_genres.extend([g.strip() for g in genres_str.split(',')])
                    historical_data['unique_genres'].append(len(set(sample_genres)) if sample_genres else 0)
                else:
                    historical_data['unique_genres'].append(0)

        # Calculate stats for each metric
        baselines = {}
        for metric, values in historical_data.items():
            if values:
                baselines[metric] = {
                    'avg': np.mean(values),
                    'p75': np.percentile(values, 75),
                    'p90': np.percentile(values, 90)
                }
            else:
                baselines[metric] = {'avg': 0, 'p75': 0, 'p90': 0}

        return baselines

    baselines = get_historical_baselines(df, hours)

    def get_comparison_delta(current_value, baseline_data):
        """Get comparison delta and direction for a metric"""
        if baseline_data['avg'] > 0:
            vs_avg = ((current_value - baseline_data['avg']) / baseline_data['avg']) * 100
            return f"{vs_avg:+.0f}% vs usual"
        return None

    # Calculate metrics
    total_tracks = len(recent_data)
    unique_artists = recent_data['master_metadata_album_artist_name'].nunique()
    unique_tracks = recent_data['master_metadata_track_name'].nunique()

    # Top song
    top_song = recent_data['master_metadata_track_name'].value_counts().head(1)
    if len(top_song) > 0:
        top_song_name = top_song.index[0]
        top_song_count = top_song.iloc[0]
        top_song_artist = recent_data[recent_data['master_metadata_track_name'] == top_song_name]['master_metadata_album_artist_name'].iloc[0]
    else:
        top_song_name = "No songs"
        top_song_count = 0
        top_song_artist = ""

    # Top artist
    top_artist = recent_data['master_metadata_album_artist_name'].value_counts().head(1)
    if len(top_artist) > 0:
        top_artist_name = top_artist.index[0]
        top_artist_count = top_artist.iloc[0]
    else:
        top_artist_name = "No artists"
        top_artist_count = 0

    # Top genre (if available)
    top_genre = "Unknown"
    if 'genres' in recent_data.columns:
        all_genres = []
        for genres_str in recent_data['genres']:
            if genres_str and genres_str != 'Unknown':
                all_genres.extend([g.strip() for g in genres_str.split(',')])
        if all_genres:
            top_genre = pd.Series(all_genres).value_counts().index[0]

    # Top items summary - Show first!
    st.subheader("🏆 Your Top Picks")
    topcol1, topcol2, topcol3 = st.columns(3)

    with topcol1:
        # Get album artwork for top song if available from API data
        top_song_image = None
        if use_api and spotify_api and spotify_api.sp and 'album_image_url' in recent_data.columns:
            top_song_with_image = recent_data[recent_data['master_metadata_track_name'] == top_song_name]
            if not top_song_with_image.empty and pd.notna(top_song_with_image['album_image_url'].iloc[0]):
                top_song_image = top_song_with_image['album_image_url'].iloc[0]

        if top_song_image:
            # Display image and text side by side
            img_col, text_col = st.columns([1, 4])
            with img_col:
                st.image(top_song_image, width=80)
            with text_col:
                if top_song_artist:
                    st.write(f"**Top Song:** {top_song_name} *by {top_song_artist}*")
                else:
                    st.write(f"**Top Song:** {top_song_name}")
                if top_song_count > 1:
                    st.write(f"🔁 **{top_song_count}** replays")
                else:
                    st.write(f"Played once")
        else:
            # No image available, display text only
            if top_song_artist:
                st.write(f"**Top Song:** {top_song_name} *by {top_song_artist}*")
            else:
                st.write(f"**Top Song:** {top_song_name}")
            if top_song_count > 1:
                st.write(f"🔁 **{top_song_count}** replays")
            else:
                st.write(f"Played once")

    with topcol2:
        st.write(f"**🎸 Top Artist:** {top_artist_name}")
        st.write(f"**{top_artist_count}** tracks played")

    with topcol3:
        st.write(f"**🎭 Top Genre:** {top_genre}")
        # Count tracks from the top genre
        if 'genres' in recent_data.columns and len(all_genres) > 0 and top_genre != "Unknown":
            top_genre_count = 0
            for genres_str in recent_data['genres']:
                if genres_str and top_genre in genres_str:
                    top_genre_count += 1
            st.write(f"**{top_genre_count}** tracks played")

    # Display metrics in one clean row with historical comparisons
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        tracks_delta = get_comparison_delta(total_tracks, baselines['tracks'])
        st.metric("🎵 Total Tracks", f"{total_tracks}", delta=tracks_delta)

    with col2:
        artists_delta = get_comparison_delta(unique_artists, baselines['unique_artists'])
        st.metric("🎤 Unique Artists", f"{unique_artists}", delta=artists_delta)

    with col3:
        # Count unique genres
        unique_genre_count = 0
        if 'genres' in recent_data.columns and len(all_genres) > 0:
            unique_genre_count = len(set(all_genres))
        genres_delta = get_comparison_delta(unique_genre_count, baselines['unique_genres'])
        st.metric("🎭 Unique Genres", f"{unique_genre_count}", delta=genres_delta)

    with col4:
        songs_delta = get_comparison_delta(unique_tracks, baselines['unique_songs'])
        st.metric("🔄 Unique Songs", f"{unique_tracks}", delta=songs_delta)

    with col5:
        # Smart activity level based on historical comparison
        if baselines['tracks']['avg'] > 0:
            vs_avg = ((total_tracks - baselines['tracks']['avg']) / baselines['tracks']['avg']) * 100
            if total_tracks >= baselines['tracks']['p90']:
                activity_level = "🔥 Very High"
            elif total_tracks >= baselines['tracks']['p75']:
                activity_level = "⚡ High"
            elif total_tracks >= baselines['tracks']['avg']:
                activity_level = "📈 Above Avg"
            else:
                activity_level = "😴 Below Avg"
            activity_delta = f"{vs_avg:+.0f}% vs usual"
            st.metric("⚡ Activity Level", activity_level, delta=activity_delta)
        else:
            st.metric("⚡ Activity Level", "📊 Building baseline...")

    # Mini visualization
    if len(recent_data) > 1:
        st.subheader("📈 Recent Listening Pattern")

        # Create timeline showing when tracks were played
        if hours <= 12:
            # Show by hour for short periods
            time_data = recent_data.groupby(recent_data['ts'].dt.floor('H')).size().reset_index()
            time_data.columns = ['time', 'tracks']
            time_data['hour'] = time_data['time'].dt.strftime('%H:%M')
            fig = px.bar(time_data, x='hour', y='tracks',
                       title=f'Listening Activity by Hour ({time_period})')
            fig.update_xaxes(title="Hour")
        else:
            # Show by hour for longer periods too, but group by larger intervals
            if hours <= 24:
                # 24 hours: group by 2-hour intervals
                time_data = recent_data.groupby(recent_data['ts'].dt.floor('2H')).size().reset_index()
                time_data.columns = ['time', 'tracks']
                time_data['hour'] = time_data['time'].dt.strftime('%m/%d %H:%M')
            else:
                # 48 hours: group by 4-hour intervals
                time_data = recent_data.groupby(recent_data['ts'].dt.floor('4H')).size().reset_index()
                time_data.columns = ['time', 'tracks']
                time_data['hour'] = time_data['time'].dt.strftime('%m/%d %H:%M')

            fig = px.bar(time_data, x='hour', y='tracks',
                       title=f'Listening Activity ({time_period})')
            fig.update_xaxes(title="Time")

        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

    # Complete track log - show all 50 tracks from API
    st.subheader("🎵 Complete Recent Track Log")

    # Get all 50 tracks from API (not just the filtered period)
    recent_tracks = spotify_api.get_recently_played(limit=50) if (use_api and spotify_api and spotify_api.sp) else None

    if recent_tracks is not None and not recent_tracks.empty:
        # Process and format the track log
        track_log = recent_tracks.copy()
        track_log['ts'] = pd.to_datetime(track_log['ts'], format='ISO8601')
        track_log = track_log.sort_values('ts', ascending=False)  # Most recent first

        # Create display dataframe with timezone conversion
        display_log = track_log[['master_metadata_track_name', 'master_metadata_album_artist_name', 'ts']].copy()

        # Convert to European timezone (add 2 hours)
        display_log['ts_local'] = display_log['ts'] + pd.Timedelta(hours=2)

        # Format date as "9th Sept" and time
        def format_ordinal_date(dt):
            day = dt.day
            if 4 <= day <= 20 or 24 <= day <= 30:
                suffix = "th"
            else:
                suffix = ["st", "nd", "rd"][day % 10 - 1]
            return f"{day}{suffix} {dt.strftime('%b').lower()}"

        display_log['Date'] = display_log['ts_local'].apply(format_ordinal_date)
        display_log['Time'] = display_log['ts_local'].dt.strftime('%H:%M')
        display_log['DateTime'] = display_log['Date'] + ' ' + display_log['Time']

        # Final display columns
        final_log = display_log[['master_metadata_track_name', 'master_metadata_album_artist_name', 'DateTime']].copy()
        final_log.columns = ['Track', 'Artist', 'Played At']
        final_log.index = range(1, len(final_log) + 1)  # Number from 1 to 50

        st.dataframe(final_log, use_container_width=True, height=400)
        st.caption(f"Showing your last {len(final_log)} tracks from Spotify API")
    else:
        st.info("Enable Spotify API to see your complete recent track log")

def streaming_history_app():
    st.header('📊 Streaming History Analysis')

    # Sidebar for API settings
    st.sidebar.header('🔗 API Integration')

    use_api = st.sidebar.checkbox('Enable Spotify API for recent data', value=False,
                                 help='Fetch your last 50 played tracks from Spotify API')

    spotify_api = None
    if use_api:
        # Try to get credentials from secrets
        try:
            client_id = st.secrets["SPOTIFY_CLIENT_ID"]
            client_secret = st.secrets["SPOTIFY_CLIENT_SECRET"]
            spotify_api = SpotifyAPI(client_id=client_id, client_secret=client_secret)

            st.sidebar.info('🔑 Credentials loaded')

            # Check if already authenticated from cache
            if spotify_api.authenticate():
                st.sidebar.success('✅ Connected')
                user_profile = spotify_api.get_user_profile()
                if user_profile:
                    st.sidebar.write(f"👋 {user_profile.get('display_name', 'User')}")
            else:
                st.sidebar.warning('⚠️ Authentication required')

        except KeyError:
            st.sidebar.error('❌ Spotify credentials not found in secrets.toml')
            st.sidebar.markdown("""
            Please add your credentials to `.streamlit/secrets.toml`:
            ```
            SPOTIFY_CLIENT_ID = "your_client_id"
            SPOTIFY_CLIENT_SECRET = "your_client_secret"
            ```
            """)

    # Load data (show spinner only in sidebar)
    # Try to load enriched data first, fall back to regular data
    df = load_enriched_data()
    if df is None:
        df = load_spotify_data(use_api=use_api, _spotify_api=spotify_api)
    else:
        # If we have enriched data, still add recent API data if enabled
        if use_api and spotify_api and spotify_api.sp:
            with st.sidebar:
                api_status = st.empty()
                api_status.text("Getting API data...")

            recent_df = spotify_api.get_recently_played(limit=50)
            if recent_df is not None and not recent_df.empty:
                with st.sidebar:
                    api_status.text("✅ API data loaded!")
                    st.success(f"✅ +{len(recent_df)} recent")

                # Process and combine with enriched data
                recent_df['ts'] = pd.to_datetime(recent_df['ts'], format='ISO8601')
                recent_df['date'] = recent_df['ts'].dt.date
                recent_df['year'] = recent_df['ts'].dt.year
                recent_df['month'] = recent_df['ts'].dt.month
                recent_df['hour'] = recent_df['ts'].dt.hour
                recent_df['day_of_week'] = recent_df['ts'].dt.day_name()
                recent_df['minutes_played'] = recent_df['ms_played'] / 60000
                recent_df['hours_played'] = recent_df['minutes_played'] / 60

                # Add genres for new tracks (fast since cached)
                if spotify_api:
                    recent_df = spotify_api.enrich_dataframe_with_genres(recent_df, show_progress=False)

                # Combine with enriched data
                combined_df = pd.concat([df, recent_df], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=['ts', 'master_metadata_track_name'], keep='first')
                df = combined_df.sort_values('ts').reset_index(drop=True)

    if df is None:
        return

    # Move success message to sidebar
    with st.sidebar:
        st.success(f'✅ Loaded {len(df):,} streams from {df["ts"].min().date()} to {df["ts"].max().date()}')

    # Sidebar filters
    st.sidebar.header('🎛️ Filters')

    # Year filter
    years = sorted(df['year'].unique())
    selected_years = st.sidebar.multiselect(
        'Select Years',
        years,
        default=years  # Default to all years
    )

    # Filter data
    if selected_years:
        df_display = df[df['year'].isin(selected_years)]
    else:
        df_display = df

    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(['Recent Activity', 'Overview', 'Artists', 'Tracks', 'Playlists', 'Genre'])

    with tab1:
        st.header('🔥 Recent Activity')

        # Time period selector - only in this tab
        time_period = st.selectbox(
            "Show activity for:",
            ["Last 6 hours", "Last 12 hours", "Last 24 hours", "Last 48 hours"],
            index=2,  # Default to 24 hours
            key="recent_activity_time_selector"
        )

        # Show the dynamic dashboard in the first tab
        with st.container():
            create_recent_dashboard(df, time_period, spotify_api)

    with tab2:
        st.header('📊 Listening Overview')

        # Main metrics for historical data
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Streams", f"{len(df_display):,}")
        with col2:
            st.metric("Total Hours", f"{df_display['hours_played'].sum():,.1f}")
        with col3:
            st.metric("Unique Artists", f"{df_display['master_metadata_album_artist_name'].nunique():,}")
        with col4:
            st.metric("Unique Tracks", f"{df_display['master_metadata_track_name'].nunique():,}")

        col1, col2 = st.columns(2)

        with col1:
            # Daily listening over time
            daily_data = df_display.groupby('date')['hours_played'].sum().reset_index()
            daily_data['date'] = pd.to_datetime(daily_data['date'])

            fig = px.line(daily_data, x='date', y='hours_played',
                         title='Daily Listening Hours Over Time')
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Listening by hour
            hourly_data = df_display.groupby('hour').size().reset_index()
            hourly_data.columns = ['hour', 'streams']

            fig = px.bar(hourly_data, x='hour', y='streams',
                        title='Streams by Hour of Day')
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

        # Time Analysis graphs
        col1, col2 = st.columns(2)

        with col1:
            # Yearly trends
            yearly_data = df_display.groupby('year')['hours_played'].sum().reset_index()
            fig = px.bar(yearly_data, x='year', y='hours_played', title='Yearly Listening Hours')
            st.plotly_chart(fig, use_container_width=True)

            # Day of week
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            dow_data = df_display.groupby('day_of_week')['hours_played'].sum().reindex(day_order)
            fig = px.bar(x=day_order, y=dow_data.values, title='Listening Hours by Day of Week')
            fig.update_xaxes(title="day")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Monthly trends
            monthly_data = df_display.groupby('month')['hours_played'].sum().reset_index()
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            monthly_data['month_name'] = monthly_data['month'].map({i+1: name for i, name in enumerate(month_names)})
            fig = px.bar(monthly_data, x='month_name', y='hours_played', title='Listening Hours by Month')
            fig.update_xaxes(title="month")
            st.plotly_chart(fig, use_container_width=True)

            # Countries
            if 'conn_country' in df_display.columns:
                country_data = df_display['conn_country'].value_counts().head(10)
                fig = px.pie(values=country_data.values, names=country_data.index, title='Listening by Country')
                st.plotly_chart(fig, use_container_width=True)

        # Daily Analysis Section
        st.subheader("📅 Date Range Listening Analysis")

        # Get available dates with data
        available_dates = sorted(df_display['date'].unique())
        min_date = available_dates[0]
        max_date = available_dates[-1]

        # Date range selector
        col1, col2 = st.columns(2)

        with col1:
            start_date = st.date_input(
                "Start Date:",
                value=available_dates[-7] if len(available_dates) >= 7 else min_date,  # Default to 7 days ago
                min_value=min_date,
                max_value=max_date,
                key="analysis_start_date"
            )

        with col2:
            end_date = st.date_input(
                "End Date:",
                value=max_date,  # Default to latest available
                min_value=start_date,
                max_value=max_date,
                key="analysis_end_date"
            )

        # Analyze selected date range
        range_data = df_display[(df_display['date'] >= start_date) & (df_display['date'] <= end_date)]

        if len(range_data) > 0:
            # Show date range info
            if start_date == end_date:
                date_range_text = start_date.strftime('%B %d, %Y')
            else:
                date_range_text = f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"

            st.info(f"📊 Analyzing data for: **{date_range_text}** ({len(range_data):,} tracks)")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                total_tracks = len(range_data)
                st.metric("Tracks Played", f"{total_tracks:,}")

            with col2:
                total_hours = range_data['hours_played'].sum()
                st.metric("Hours Listened", f"{total_hours:.1f}")

            with col3:
                unique_artists = range_data['master_metadata_album_artist_name'].nunique()
                st.metric("Unique Artists", f"{unique_artists:,}")

            with col4:
                # Country info
                countries = range_data['conn_country'].value_counts()
                if len(countries) > 0 and countries.index[0] != 'Unknown':
                    main_country = countries.index[0]
                    country_count = countries.iloc[0]
                    st.metric("Main Location", f"{main_country}")
                    st.caption(f"{country_count} tracks from {main_country}")
                else:
                    st.metric("Location", "Unknown")

            # Top picks for the date range
            st.subheader(f"🏆 Top Picks for Selected Period")

            topcol1, topcol2, topcol3 = st.columns(3)

            with topcol1:
                # Top song
                top_songs = range_data['master_metadata_track_name'].value_counts()
                if len(top_songs) > 0:
                    top_song = top_songs.index[0]
                    top_song_count = top_songs.iloc[0]
                    top_song_artist = range_data[range_data['master_metadata_track_name'] == top_song]['master_metadata_album_artist_name'].iloc[0]

                    # Try to get artwork from cache
                    album_image = None
                    try:
                        from artwork_cache import ArtworkCache
                        artwork_cache = ArtworkCache()
                        if len(artwork_cache.cache) > 0:
                            cached_artwork = artwork_cache.get_track_artwork(top_song, top_song_artist)
                            if cached_artwork and cached_artwork.get('artwork_url'):
                                album_image = cached_artwork['artwork_url']
                    except Exception:
                        album_image = None

                    if album_image:
                        # Display with artwork
                        img_col, text_col = st.columns([1, 2])
                        with img_col:
                            st.image(album_image, width=80)
                        with text_col:
                            st.write(f"**Top Song:**")
                            st.write(f"{top_song} *by {top_song_artist}*")
                            if top_song_count > 1:
                                st.write(f"🔁 {top_song_count} plays")
                            else:
                                st.write("Played once")
                    else:
                        # Display without artwork
                        st.write(f"**Top Song:**")
                        st.write(f"{top_song} *by {top_song_artist}*")
                        if top_song_count > 1:
                            st.write(f"🔁 {top_song_count} plays")
                        else:
                            st.write("Played once")
                else:
                    st.write("**Top Song:** No data")

            with topcol2:
                # Top artist
                top_artists = range_data['master_metadata_album_artist_name'].value_counts()
                if len(top_artists) > 0:
                    top_artist = top_artists.index[0]
                    top_artist_count = top_artists.iloc[0]
                    st.write(f"**🎸 Top Artist:**")
                    st.write(f"{top_artist}")
                    st.write(f"{top_artist_count} tracks played")
                else:
                    st.write("**🎸 Top Artist:** No data")

            with topcol3:
                # Top genre
                if 'genres' in range_data.columns:
                    all_genres = []
                    for genres_str in range_data['genres']:
                        if genres_str and genres_str != 'Unknown':
                            all_genres.extend([g.strip() for g in genres_str.split(',')])

                    if all_genres:
                        top_genre_counts = pd.Series(all_genres).value_counts()
                        top_genre = top_genre_counts.index[0]
                        top_genre_count = top_genre_counts.iloc[0]
                        st.write(f"**🎭 Top Genre:**")
                        st.write(f"{top_genre}")
                        st.write(f"{top_genre_count} tracks")
                    else:
                        st.write("**🎭 Top Genre:** Unknown")
                else:
                    st.write("**🎭 Top Genre:** No genre data")
        else:
            st.info(f"No listening data found for the selected date range")

    with tab3:
        st.header('🎤 Artist Analysis')

        # Top artists selector
        top_n = st.slider('Show top N artists', 5, 50, 20)

        col1, col2 = st.columns(2)

        with col1:
            # Top artists by hours
            top_artists_hours = df_display.groupby('master_metadata_album_artist_name')['hours_played'].sum().nlargest(top_n)

            fig = px.bar(x=top_artists_hours.values, y=top_artists_hours.index,
                        orientation='h', title=f'Top {top_n} Artists by Hours')
            fig.update_layout(height=600, yaxis={'categoryorder':'total ascending'})
            fig.update_xaxes(title="hours")
            fig.update_yaxes(title="")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Top artists by stream count
            top_artists_streams = df_display['master_metadata_album_artist_name'].value_counts().head(top_n)

            fig = px.bar(x=top_artists_streams.values, y=top_artists_streams.index,
                        orientation='h', title=f'Top {top_n} Artists by Stream Count')
            fig.update_layout(height=600, yaxis={'categoryorder':'total ascending'})
            fig.update_xaxes(title="count")
            fig.update_yaxes(title="")
            st.plotly_chart(fig, use_container_width=True)

        # Artist search
        st.subheader('🔍 Search Artist')
        artist_search = st.text_input('Enter artist name:')
        if artist_search:
            artist_data = df_display[df_display['master_metadata_album_artist_name'].str.contains(artist_search, case=False, na=False)]
            if len(artist_data) > 0:
                st.write(f"**{artist_search}** stats:")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Streams", len(artist_data))
                with col2:
                    st.metric("Total Hours", f"{artist_data['hours_played'].sum():.1f}")
                with col3:
                    st.metric("Unique Tracks", artist_data['master_metadata_track_name'].nunique())

                # Top tracks for this artist
                top_tracks = artist_data['master_metadata_track_name'].value_counts().head(10)
                st.write("**Top tracks:**")
                st.bar_chart(top_tracks)

    with tab4:
        st.header('🎵 Track Analysis')

        # Top tracks
        top_tracks = df_display['master_metadata_track_name'].value_counts().head(20)

        fig = px.bar(x=top_tracks.values, y=top_tracks.index,
                    orientation='h', title='Top 20 Most Played Tracks')
        fig.update_layout(height=600, yaxis={'categoryorder':'total ascending'})
        fig.update_xaxes(title="plays")
        fig.update_yaxes(title="")
        st.plotly_chart(fig, use_container_width=True)

        # Track details
        st.subheader('📋 Track Details')

        # Try to load artwork cache
        try:
            from artwork_cache import ArtworkCache
            artwork_cache = ArtworkCache()
            has_artwork_cache = True
        except:
            has_artwork_cache = False

        if has_artwork_cache and len(artwork_cache.cache) > 0:
            # Display tracks with cached artwork
            for i, track in enumerate(top_tracks.head(10).index):
                artist = df_display[df_display['master_metadata_track_name'] == track]['master_metadata_album_artist_name'].iloc[0]
                plays = top_tracks[track]
                hours = df_display[df_display['master_metadata_track_name'] == track]['hours_played'].sum()

                # Get artwork from cache
                cached_artwork = artwork_cache.get_track_artwork(track, artist)
                album_image = cached_artwork.get('artwork_url') if cached_artwork else None

                if album_image:
                    # Display with artwork
                    img_col, text_col = st.columns([0.5, 16])
                    with img_col:
                        st.image(album_image, width=60)
                    with text_col:
                        st.write(f"**{i+1}. {track}** *by {artist}*")
                        st.write(f"🔁 **{plays}** plays • ⏱️ **{hours:.1f}** hours")
                else:
                    # Display without artwork
                    st.write(f"**{i+1}. {track}** *by {artist}*")
                    st.write(f"🔁 **{plays}** plays • ⏱️ **{hours:.1f}** hours")

                if i < 9:  # Don't add divider after last item
                    st.divider()

            # Show cache info
            if st.sidebar.checkbox("Show artwork cache info"):
                stats = artwork_cache.get_cache_stats()
                st.sidebar.write(f"🎨 Artwork cache: {stats['total_tracks']} tracks")

        else:
            # Fallback to table format when no artwork cache
            track_details = []
            for i, track in enumerate(top_tracks.head(10).index):
                artist = df_display[df_display['master_metadata_track_name'] == track]['master_metadata_album_artist_name'].iloc[0]
                plays = top_tracks[track]
                hours = df_display[df_display['master_metadata_track_name'] == track]['hours_played'].sum()
                track_details.append({
                    '#': i+1,
                    'Track': track,
                    'Artist': artist,
                    'Plays': plays,
                    'Hours': f"{hours:.1f}"
                })

            st.dataframe(pd.DataFrame(track_details), use_container_width=True, hide_index=True)

            # Show info about artwork enrichment
            if not has_artwork_cache:
                st.info("💡 Run `python enrich_all_artwork.py` to add album artwork to your track details!")

    with tab5:
        st.header('Playlists')

        if use_api and spotify_api and spotify_api.sp:
            # Get user playlists
            playlists_df = spotify_api.get_user_playlists()

            if playlists_df is not None and not playlists_df.empty:
                # Playlist overview metrics
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    total_playlists = len(playlists_df)
                    st.metric("Total Playlists", f"{total_playlists:,}")

                with col2:
                    total_tracks = playlists_df['tracks_total'].sum()
                    st.metric("Total Tracks", f"{total_tracks:,}")

                with col3:
                    public_playlists = playlists_df['public'].sum()
                    st.metric("Public Playlists", f"{public_playlists:,}")

                with col4:
                    collaborative_playlists = playlists_df['collaborative'].sum()
                    st.metric("Collaborative", f"{collaborative_playlists:,}")

                # Playlist selector
                st.subheader("Analyze Your Playlists")

                # Single search/select bar
                playlist_names = playlists_df['name'].tolist()

                # Set default to "Personal Diary" if it exists, otherwise first playlist
                default_index = 0
                if "Personal Diary" in playlist_names:
                    default_index = playlist_names.index("Personal Diary")

                selected_playlist_name = st.selectbox(
                    "Search and select playlist to analyze:",
                    options=playlist_names,
                    index=default_index,
                    key="playlist_selector"
                )

                # Get the selected playlist data and immediately analyze
                if selected_playlist_name:
                    selected_playlist_data = playlists_df[playlists_df['name'] == selected_playlist_name].iloc[0]

                    # Automatically set for analysis
                    st.session_state.selected_playlist = selected_playlist_data['playlist_id']
                    st.session_state.selected_playlist_name = selected_playlist_data['name']

                    # Display selected playlist info
                    col1, col2 = st.columns([1, 3])

                    with col1:
                        if selected_playlist_data['image_url']:
                            st.image(selected_playlist_data['image_url'], width=150)

                    with col2:
                        st.write(f"**{selected_playlist_data['name']}**")
                        st.write(f"🎵 {selected_playlist_data['tracks_total']} tracks")

                        if selected_playlist_data['description']:
                            st.write(f"*{selected_playlist_data['description']}*")

                # Show detailed analysis if a playlist is selected
                if 'selected_playlist' in st.session_state:
                    st.divider()
                    st.subheader(f"Analysis: {st.session_state.selected_playlist_name}")

                    # Get playlist tracks
                    with st.spinner("Loading playlist tracks..."):
                        tracks_df = spotify_api.get_playlist_tracks(st.session_state.selected_playlist)

                    if tracks_df is not None and not tracks_df.empty:
                        # Playlist analytics
                        col1, col2 = st.columns(2)

                        with col1:
                            # Basic stats
                            st.write("**Playlist Statistics:**")
                            # Use actual total from playlist metadata, not fetched tracks count
                            actual_total = selected_playlist_data['tracks_total']
                            st.metric("Total Tracks", actual_total)

                            if 'duration_ms' in tracks_df.columns:
                                total_duration = tracks_df['duration_ms'].sum() / (1000 * 60)  # minutes
                                st.metric("Total Duration", f"{total_duration:.0f} minutes")

                            # Top artists in playlist
                            if 'artist' in tracks_df.columns:
                                top_artists = tracks_df['artist'].value_counts().head(5)
                                st.write("**Top Artists:**")
                                for artist, count in top_artists.items():
                                    st.write(f"• {artist}: {count} tracks")

                        with col2:
                            # Audio features analysis (if available)
                            audio_features = ['danceability', 'energy', 'valence', 'acousticness']
                            available_features = [f for f in audio_features if f in tracks_df.columns]

                            if available_features:
                                st.write("**Audio Characteristics:**")
                                for feature in available_features:
                                    avg_value = tracks_df[feature].mean()
                                    if pd.notna(avg_value):
                                        st.metric(feature.title(), f"{avg_value:.2f}")

                        # Show recent tracks from playlist
                        st.write("**Recent Tracks:**")

                        # Sort by added date if available
                        if 'added_at' in tracks_df.columns:
                            tracks_df['added_at'] = pd.to_datetime(tracks_df['added_at'])
                            recent_tracks = tracks_df.sort_values('added_at', ascending=False).head(10)
                        else:
                            recent_tracks = tracks_df.head(10)

                        for i, track in recent_tracks.iterrows():
                            if track.get('album_image_url'):
                                img_col, text_col = st.columns([1, 20])
                                with img_col:
                                    st.image(track['album_image_url'], width=50)
                                with text_col:
                                    st.write(f"**{track['name']}** *by {track['artist']}*")
                                    if 'added_at' in track and pd.notna(track['added_at']):
                                        st.caption(f"Added: {track['added_at'].strftime('%Y-%m-%d')}")
                            else:
                                st.write(f"**{track['name']}** *by {track['artist']}*")

                    if st.button("Clear Selection"):
                        del st.session_state.selected_playlist
                        del st.session_state.selected_playlist_name
                        st.rerun()

            else:
                st.info("No playlists found or unable to fetch playlists.")

        else:
            st.info("Please authenticate with Spotify API to view your playlists.")

    with tab6:
        st.header('Genre Analysis')

        # Check if enriched data exists
        enriched_df = load_enriched_data()

        if enriched_df is not None:
            # Filter enriched data by selected years
            if selected_years:
                enriched_display = enriched_df[enriched_df['year'].isin(selected_years)]
            else:
                enriched_display = enriched_df

            # Full historical analysis (no button needed!)
            st.subheader("📈 Complete Genre Evolution Over Time")

            # Group by year and analyze genres
            yearly_data = []
            for year in sorted(enriched_display['year'].unique()):
                year_tracks = enriched_display[enriched_display['year'] == year]
                year_genres = []
                for genres_str in year_tracks['genres']:
                    if genres_str and genres_str != 'Unknown':
                        year_genres.extend([g.strip() for g in genres_str.split(',')])

                # Get top genres for this year
                if year_genres:
                    year_genre_counts = pd.Series(year_genres).value_counts()
                    total_year_genres = len(year_genres)

                    # Get overall top genres to maintain consistency
                    all_historical_genres = []
                    for genres_str in enriched_display['genres']:
                        if genres_str and genres_str != 'Unknown':
                            all_historical_genres.extend([g.strip() for g in genres_str.split(',')])

                    top_genres = pd.Series(all_historical_genres).value_counts().head(8).index

                    for genre in top_genres:
                        percentage = (year_genre_counts.get(genre, 0) / total_year_genres * 100) if total_year_genres > 0 else 0
                        yearly_data.append({
                            'year': year,
                            'genre': genre,
                            'percentage': percentage,
                            'count': year_genre_counts.get(genre, 0)
                        })

            if yearly_data:
                timeline_df = pd.DataFrame(yearly_data)

                # Time series line chart
                fig = px.line(timeline_df, x='year', y='percentage', color='genre',
                            title='Your Genre Evolution Over Time (% of total listening)',
                            labels={'percentage': 'Percentage of Listening', 'year': 'Year'})
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)

                # Summary stats
                col1, col2 = st.columns(2)

                with col1:
                    # Overall genre distribution
                    all_historical_genres = []
                    for genres_str in enriched_display['genres']:
                        if genres_str and genres_str != 'Unknown':
                            all_historical_genres.extend([g.strip() for g in genres_str.split(',')])

                    genre_counts = pd.Series(all_historical_genres).value_counts().head(10)
                    fig2 = px.pie(values=genre_counts.values, names=genre_counts.index,
                                title='Overall Genre Distribution')
                    st.plotly_chart(fig2, use_container_width=True)

                with col2:
                    # Genre diversity by year
                    diversity_data = []
                    for year in sorted(enriched_display['year'].unique()):
                        year_tracks = enriched_display[enriched_display['year'] == year]
                        year_genres = []
                        for genres_str in year_tracks['genres']:
                            if genres_str and genres_str != 'Unknown':
                                year_genres.extend([g.strip() for g in genres_str.split(',')])

                        unique_genres = len(set(year_genres))
                        diversity_data.append({'year': year, 'unique_genres': unique_genres})

                    diversity_df = pd.DataFrame(diversity_data)
                    fig3 = px.bar(diversity_df, x='year', y='unique_genres',
                                title='Genre Diversity by Year')
                    st.plotly_chart(fig3, use_container_width=True)


        else:
            st.warning("🎭 No enriched data found.")
            st.info("To get genre analysis for your complete history:")
            st.code("python enrich_all_genres.py", language="bash")
            st.markdown("This will fetch genres for **all** your tracks once and save them permanently!")

            if use_api and spotify_api and spotify_api.sp:
                st.info("Or enable the API above for recent tracks analysis only.")

if __name__ == "__main__":
    streaming_history_app()
    render_footer()