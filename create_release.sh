#!/bin/bash
# Script to create a GitHub release with enriched data file

set -e

echo "📦 Creating GitHub Release with Enriched Data"
echo "=============================================="
echo ""

# Check if enriched data file exists
if [ ! -f "data/enriched_spotify_data.json" ]; then
    echo "❌ Error: data/enriched_spotify_data.json not found"
    echo "   Run 'python data_builder.py' first to create it"
    exit 1
fi

# Get file size
SIZE=$(du -h data/enriched_spotify_data.json | cut -f1)
echo "📊 Enriched data file size: $SIZE"
echo ""

# Get current date for version
VERSION=$(date +"%Y.%m.%d")
TAG="v$VERSION"

echo "🏷️  Creating release: $TAG"
echo ""

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo "⚠️  GitHub CLI (gh) is not installed"
    echo ""
    echo "📋 Manual steps to create release:"
    echo ""
    echo "1. Go to: https://github.com/sara-kaczmarek/spotiboti/releases/new"
    echo "2. Set tag: $TAG"
    echo "3. Set title: Enriched Data Release - $VERSION"
    echo "4. Description:"
    echo "   📊 Enriched Spotify streaming history dataset"
    echo "   - Contains $(python3 -c "import json; print(len(json.load(open('data/enriched_spotify_data.json'))))"  ) listening records"
    echo "   - Includes genre enrichment for artists"
    echo "   - File size: $SIZE"
    echo ""
    echo "   This release contains the pre-processed enriched data file that can be"
    echo "   downloaded automatically by the Streamlit app to avoid the 15-minute"
    echo "   build time on first load."
    echo ""
    echo "5. Upload asset: data/enriched_spotify_data.json"
    echo "6. Click 'Publish release'"
    echo ""
    exit 0
fi

# Create release using GitHub CLI
echo "✅ GitHub CLI found, creating release..."

# Get record count
RECORD_COUNT=$(python3 -c "import json; print(len(json.load(open('data/enriched_spotify_data.json'))))" 2>/dev/null || echo "unknown")

# Create release
gh release create "$TAG" \
    --title "Enriched Data Release - $VERSION" \
    --notes "📊 Enriched Spotify streaming history dataset

- Contains $RECORD_COUNT listening records
- Includes genre enrichment for artists
- File size: $SIZE

This release contains the pre-processed enriched data file that can be downloaded automatically by the Streamlit app to avoid the 15-minute build time on first load.

**For developers:** The app will automatically download this file on first load. No action needed." \
    data/enriched_spotify_data.json

echo ""
echo "✅ Release created successfully!"
echo "🔗 View at: https://github.com/sara-kaczmarek/spotiboti/releases"
