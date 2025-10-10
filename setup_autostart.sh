#!/bin/bash

# Setup script for Sara's Spotify app auto-start

echo "Setting up Sara's Spotify app to start automatically on login..."

# Create LaunchAgents directory if it doesn't exist
mkdir -p ~/Library/LaunchAgents

# Copy the plist file to LaunchAgents
cp com.sara.spotify.plist ~/Library/LaunchAgents/

# Load the launch agent
launchctl load ~/Library/LaunchAgents/com.sara.spotify.plist

echo "✅ Setup complete! Your Spotify app will now start automatically when you log in."
echo "The app will be available at: http://localhost:8501"
echo ""
echo "To manually start: launchctl start com.sara.spotify"
echo "To stop: launchctl stop com.sara.spotify"
echo "To disable auto-start: launchctl unload ~/Library/LaunchAgents/com.sara.spotify.plist"