#%%
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json
import glob
import warnings
warnings.filterwarnings('ignore')

# Set style for better plots
plt.style.use('dark_background')
sns.set_palette("husl")


# Load all audio streaming history files
import os
os.chdir('/Users/sarakaczmarek/Desktop/Spotify/streaming_data')
audio_files = glob.glob('Streaming_History_Audio_*.json')
print(f"Found {len(audio_files)} audio history files")

all_streams = []
for file in sorted(audio_files):
    print(f"Loading {file}...")
    with open(file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        all_streams.extend(data)

print(f"Total streams loaded: {len(all_streams):,}")

df = pd.DataFrame(all_streams)
print(f"DataFrame shape: {df.shape}")

display(df)

#%%
# Clean and prepare data
df['ts'] = pd.to_datetime(df['ts'])
df['date'] = df['ts'].dt.date
df['year'] = df['ts'].dt.year
df['month'] = df['ts'].dt.month
df['hour'] = df['ts'].dt.hour
df['day_of_week'] = df['ts'].dt.day_name()

df['minutes_played'] = df['ms_played'] / 60000
df['hours_played'] = df['minutes_played'] / 60

df = df.drop(columns=['platform','ip_addr','spotify_track_uri','episode_name','episode_show_name',
                      'spotify_episode_uri','audiobook_title','audiobook_uri','audiobook_chapter_uri',
                      'audiobook_chapter_title','offline_timestamp','incognito_mode'])


df = df.rename(columns ={'conn_country':'country','master_metadata_track_name':'song',
                         'master_metadata_album_artist_name':'artist','master_metadata_album_album_name':'album'})

display(df)
#%%

#%%

# Filter out very short plays (less than 30 seconds)
df_filtered = df[df['ms_played'] >= 30000].copy()

print(f"\\nAfter filtering short plays: {len(df_filtered):,} streams")
print(f"Total hours listened: {df_filtered['hours_played'].sum():,.1f}")
print(f"Date range: {df_filtered['ts'].min()} to {df_filtered['ts'].max()}")

# Basic statistics
print("\\n=== STREAMING OVERVIEW ===")
print(f"Total streams: {len(df_filtered):,}")
print(f"Total hours: {df_filtered['hours_played'].sum():,.1f}")
print(f"Total days: {(df_filtered['ts'].max() - df_filtered['ts'].min()).days:,}")
print(f"Average hours per day: {df_filtered['hours_played'].sum() / (df_filtered['ts'].max() - df_filtered['ts'].min()).days:.1f}")
print(f"Unique artists: {df_filtered['artist'].nunique():,}")
print(f"Unique tracks: {df_filtered['song'].nunique():,}")

# Create visualizations
fig = plt.figure(figsize=(20, 15))

# 1. Daily listening hours over time
plt.subplot(3, 2, 1)
daily_hours = df_filtered.groupby('date')['hours_played'].sum().reset_index()
daily_hours['date'] = pd.to_datetime(daily_hours['date'])
plt.plot(daily_hours['date'], daily_hours['hours_played'], alpha=0.7, linewidth=0.8)
plt.title('Daily Listening Hours Over Time', fontsize=14)
plt.ylabel('Hours')
plt.xticks(rotation=45)

# 2. Top 15 artists by hours
plt.subplot(3, 2, 2)
top_artists_hours = df_filtered.groupby('artist')['hours_played'].sum().sort_values(ascending=False).head(15)
plt.barh(range(len(top_artists_hours)), top_artists_hours.values)
plt.yticks(range(len(top_artists_hours)), top_artists_hours.index, fontsize=9)
plt.title('Top 15 Artists by Hours Played', fontsize=14)
plt.xlabel('Hours')
plt.gca().invert_yaxis()

# 3. Listening by day of week
plt.subplot(3, 2, 3)
day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
dow_hours = df_filtered.groupby('day_of_week')['hours_played'].sum().reindex(day_order)
plt.bar(dow_hours.index, dow_hours.values)
plt.title('Listening Hours by Day of Week', fontsize=14)
plt.ylabel('Hours')
plt.xticks(rotation=45)

# 4. Listening by hour of day
plt.subplot(3, 2, 4)
hourly_streams = df_filtered.groupby('hour').size()
plt.bar(hourly_streams.index, hourly_streams.values)
plt.title('Streams by Hour of Day', fontsize=14)
plt.xlabel('Hour')
plt.ylabel('Number of Streams')

# 5. Yearly listening trends
plt.subplot(3, 2, 5)
yearly_hours = df_filtered.groupby('year')['hours_played'].sum()
plt.bar(yearly_hours.index, yearly_hours.values)
plt.title('Yearly Listening Hours', fontsize=14)
plt.xlabel('Year')
plt.ylabel('Hours')

# 6. Top 15 tracks
plt.subplot(3, 2, 6)
top_tracks = df_filtered['song'].value_counts().head(15)
plt.barh(range(len(top_tracks)), top_tracks.values)
plt.yticks(range(len(top_tracks)), [t[:30] + '...' if len(t) > 30 else t for t in top_tracks.index], fontsize=8)
plt.title('Top 15 Most Played Tracks', fontsize=14)
plt.xlabel('Play Count')
plt.gca().invert_yaxis()

plt.tight_layout()
plt.show()

# Top artists and tracks summary
print("\\n=== TOP 10 ARTISTS BY HOURS ===")
top_10_artists = df_filtered.groupby('artist')['hours_played'].sum().sort_values(ascending=False).head(10)
for i, (artist, hours) in enumerate(top_10_artists.items(), 1):
    print(f"{i:2d}. {artist}: {hours:.1f} hours")

print("\\n=== TOP 10 MOST PLAYED TRACKS ===")
top_10_tracks = df_filtered['song'].value_counts().head(10)
for i, (track, count) in enumerate(top_10_tracks.items(), 1):
    artist = df_filtered[df_filtered['song'] == track]['artist'].iloc[0]
    print(f"{i:2d}. {track} by {artist}: {count} plays")

# Countries analysis
print(f"\\n=== COUNTRIES LISTENED FROM ===")
country_stats = df_filtered['country'].value_counts()
print(f"Total countries: {len(country_stats)}")
for country, count in country_stats.items():
    percentage = (count / len(df_filtered)) * 100
    print(f"{country}: {count:,} streams ({percentage:.1f}%)")
# %%
