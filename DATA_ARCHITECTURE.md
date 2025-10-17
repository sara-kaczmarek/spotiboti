# Data Architecture Overview

## Problem We Solved

Previously, the `enriched_spotify_data.json` file (220MB) was tracked in Git using Git LFS, which caused several issues:

- ❌ GitHub repository exceeded its LFS storage quota
- ❌ GitHub Actions workflow couldn't fetch/update the file
- ❌ Local development couldn't pull LFS objects
- ❌ Streamlit Cloud deployment would fail with LFS bandwidth limits
- ❌ Expensive ($5/month for GitHub Pro with 50GB LFS)

## New Architecture

Instead of tracking the large enriched data file in Git, we now **build it dynamically from raw streaming history files**:

```
Raw Streaming Data (in Git)
    ↓
data_builder.py (builds on-demand)
    ↓
enriched_spotify_data.json (local only, gitignored)
```

### What's in Git

✅ **Tracked in Git:**
- `streaming_data/Streaming_History_Audio_*.json` - Raw Spotify streaming history files
- `data/artist_genres_cache.json` - Cached genre lookups (small, ~20KB)
- `data_builder.py` - Utility to build enriched dataset
- All application code

❌ **NOT in Git (ignored):**
- `data/enriched_spotify_data.json` - Large enriched dataset (183MB)
- Built locally on-demand from raw files

### How It Works

1. **First Load:** When you run the Streamlit app or update script:
   - Checks if `enriched_spotify_data.json` exists
   - If not, automatically builds it from raw `streaming_data/*.json` files
   - Enriches with genre data from Spotify API
   - Saves locally for subsequent loads
   - Takes 5-15 minutes on first build

2. **Subsequent Loads:**
   - File exists locally → loads instantly
   - No rebuild needed

3. **GitHub Actions Workflow:**
   - Checks out code (no LFS needed)
   - Builds enriched data from raw files if missing
   - Fetches new tracks from Spotify API
   - Appends to existing data
   - Only commits genre cache (not the large data file)

4. **Streamlit Cloud Deployment:**
   - Deploys from Git (raw files included)
   - On first run, builds enriched data from raw files
   - Subsequent container restarts reuse the built file

## File Structure

```
Spotify/
├── streaming_data/          # Raw Spotify data (in Git)
│   ├── Streaming_History_Audio_2023-2024_15.json
│   ├── Streaming_History_Audio_2024-2025_18.json
│   └── ... (20 files total, ~12MB each)
│
├── data/
│   ├── enriched_spotify_data.json     # Built file (NOT in Git)
│   ├── artist_genres_cache.json       # Genre cache (in Git)
│   └── track_artwork_cache.json       # Artwork cache
│
├── data_builder.py                    # Builds enriched data
├── update_recent_tracks.py            # Fetches new tracks
└── pages/streaming_history.py         # Streamlit app
```

## Benefits

✅ No Git LFS costs or quota issues
✅ Works perfectly on Streamlit Cloud
✅ Works in GitHub Actions without special config
✅ Works for local development
✅ Smaller Git repository
✅ Each environment builds data independently from source

## Trade-offs

⚠️ **First load takes time:** 5-15 minutes to build enriched dataset with genre data
✅ **But:** Subsequent loads are instant (file cached locally)
✅ **And:** Genre cache prevents redundant API calls

## For Developers

### Local Development

First time setup:
```bash
git clone https://github.com/sara-kaczmarek/spotiboti.git
cd spotiboti
pip install -r requirements.txt

# Data file will be built automatically on first app run
streamlit run spotify_app.py
```

### Forcing a Rebuild

If you want to rebuild the enriched data:
```bash
# Delete the file
rm data/enriched_spotify_data.json

# Run the builder
python data_builder.py

# Or just run the app - it will rebuild automatically
streamlit run spotify_app.py
```

### Updating with Recent Tracks

```bash
# Fetches last 50 tracks and appends to enriched data
python update_recent_tracks.py
```

## How the Auto-Update Workflow Works

The GitHub Actions workflow (`.github/workflows/update_tracks.yml`) runs every 6 hours:

1. Checks out the repository (gets raw streaming data)
2. Builds enriched data from raw files (if missing)
3. Runs `update_recent_tracks.py` to fetch new tracks from Spotify API
4. Appends new tracks to the enriched dataset
5. Commits only the updated genre cache to Git
6. The enriched data file stays local (not pushed)

This means:
- GitHub Actions has its own copy of the enriched data
- Your local machine has its own copy
- Streamlit Cloud has its own copy
- All built from the same source of truth: raw streaming data files

## Monitoring

- Workflow runs: Check `.github/workflows/update_tracks.yml` runs in GitHub Actions
- Local updates: Check `spotify_app.log` and `spotify_app_error.log`
- Data freshness: Check the timestamp of latest entry in enriched dataset
