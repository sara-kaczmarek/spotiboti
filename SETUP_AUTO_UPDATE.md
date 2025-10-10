# Auto-Update Setup Guide

This guide explains how to set up automatic fetching of your recent Spotify tracks every 6 hours using GitHub Actions.

## How It Works

1. **GitHub Actions** runs every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)
2. **Fetches your last 50 played tracks** from Spotify API
3. **Enriches them** with genres and artwork
4. **Appends to** `enriched_spotify_data.json` (removing duplicates)
5. **Commits and pushes** the update to GitHub
6. **Streamlit Cloud** automatically redeploys with new data

## Setup Steps

### Step 1: Get Spotify Refresh Token

The tricky part is that GitHub Actions needs a way to authenticate as YOU to fetch YOUR recent tracks. We need a refresh token.

**Run this locally to get your refresh token:**

```bash
python3 << 'EOF'
from spotify_api import SpotifyAPI
import json

api = SpotifyAPI()
api.authenticate()  # This will use your cached token

# Get the token info
token_info = api.sp_oauth.get_cached_token()

if token_info and 'refresh_token' in token_info:
    print("\n✅ Your Spotify Refresh Token:")
    print(token_info['refresh_token'])
    print("\n⚠️ Keep this secret! Add it to GitHub Secrets.")
else:
    print("❌ No refresh token found. Make sure you're authenticated.")
EOF
```

### Step 2: Add GitHub Secrets

Go to your GitHub repository settings and add these secrets:

1. Go to `https://github.com/sara-kaczmarek/spotiboti/settings/secrets/actions`
2. Click "New repository secret"
3. Add these three secrets:

| Name | Value |
|------|-------|
| `SPOTIFY_CLIENT_ID` | Your Spotify Client ID |
| `SPOTIFY_CLIENT_SECRET` | Your Spotify Client Secret |
| `SPOTIFY_REFRESH_TOKEN` | The refresh token from Step 1 |

### Step 3: Update GitHub Actions Workflow

The workflow is already configured in `.github/workflows/update_tracks.yml`

It will run:
- **Every 6 hours** automatically
- **Manually** when you trigger it from GitHub Actions tab

### Step 4: Test It Manually

1. Go to your GitHub repository
2. Click the "Actions" tab
3. Click "Update Recent Tracks" workflow
4. Click "Run workflow" button
5. Watch the logs to see if it works!

## What Gets Updated

- `data/enriched_spotify_data.json` - Your main dataset with new tracks appended
- `data/artist_genres_cache.json` - Genre cache updated with new artists

## Limitations

- Spotify API returns max 50 tracks per request
- Running every 6 hours = 4 times per day = 200 tracks max per day
- If you listen to more than 200 tracks per day, some might be missed
- **Important**: ALL your listens are kept! If you play the same song 10 times, all 10 plays are recorded
- Only exact duplicate API fetches (same timestamp from re-running the script) are filtered

## Troubleshooting

**If the workflow fails:**

1. Check GitHub Actions logs for errors
2. Verify all three secrets are set correctly
3. Make sure your refresh token is valid (re-run Step 1)
4. Check that your Spotify app has the right scopes:
   - `user-read-recently-played`
   - `user-read-playback-state`
   - `user-library-read`
   - `user-top-read`

**If no new tracks are added:**

- This is normal if you haven't listened to anything new
- The script filters out duplicates automatically

## Manual Update

You can also run the update script manually on your local machine:

```bash
python update_recent_tracks.py
```

This will fetch recent tracks and append them to your local enriched data file.

## Future Improvements

- Add email notifications when update fails
- Support for multiple users
- Webhook to trigger update after X tracks instead of time-based
- Better handling of rate limits
