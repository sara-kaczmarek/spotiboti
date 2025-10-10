# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
- **Main app**: `streamlit run spotify_app.py` - Starts the main Streamlit application on port 8501
- **SpotiBoti chatbot**: `streamlit run pages/spotiboti.py` - Direct access to the AI chatbot interface
- **Auto-start setup**: `./setup_autostart.sh` - Configures the app to start automatically on macOS login

### Dependencies
- Install dependencies: `pip install -r requirements.txt`
- Core dependencies: pandas, matplotlib, seaborn, numpy, streamlit, plotly, spotipy
- External dependency: Ollama (for AI chatbot functionality) - start with `ollama serve`

### Data Enrichment Scripts
- **Enrich genres**: `python enrich_all_genres.py` - Adds genre data to tracks
- **Enrich artwork**: `python enrich_all_artwork.py` - Downloads and caches album artwork
- **Enrich audio features**: `python enrich_audio_features.py` - Adds Spotify audio features

## High-Level Architecture

### Core Application Structure
This is a Streamlit-based Spotify data visualization and analysis application with four main sections:

1. **Main Dashboard** (`spotify_app.py`) - Landing page with navigation to features
2. **SpotiBoti AI Chatbot** (`pages/spotiboti.py`) - AI assistant for music data queries
3. **Streaming History Analysis** (`pages/streaming_history.py`) - Comprehensive data visualization
4. **Song Analysis & Recommendations** (`pages/song_analysis.py`, `pages/recommender_system.py`)

### Key Components

#### Data Layer
- **Raw Data**: `streaming_data/` directory contains JSON files with Spotify streaming history
- **Enriched Data**: `enriched_spotify_data.json` - Main dataset with genres, artwork, and audio features
- **Caches**: Multiple JSON cache files for artwork, genres, and API responses

#### AI/ML Components
- **SpotifyDataAnalyzer** (`spotify_data_analyzer.py`) - Intelligent query analysis and data retrieval
- **SpotifyChatbot** (`spotify_chatbot.py`) - Natural language interface using Ollama LLM
- **SpotiBotiMemory** (`spotiboti_memory.py`) - Conversation context and learning system

#### API Integration
- **SpotifyAPI** (`spotify_api.py`) - Spotify Web API wrapper with authentication
- **GenreCache** (`genre_cache.py`) - Caches artist genre lookups
- **ArtworkCache** (`artwork_cache.py`) - Manages album artwork downloads

### Data Flow Architecture
1. Raw Spotify streaming data → Enrichment scripts → `enriched_spotify_data.json`
2. User queries → SpotifyDataAnalyzer → Relevant data extraction → Ollama LLM → Natural language response
3. Spotify API calls are cached to avoid rate limiting
4. AI responses are stored in memory for context awareness

### Authentication & Configuration
- Spotify API credentials required: `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`
- OAuth cache stored in `.spotify_cache`
- Personal profile data in `sara_profile.json`
- Launch configuration in `com.sara.spotify.plist` for macOS auto-start

### Page Architecture
All pages inherit from the main app structure and use `shared_components.py` for consistent UI elements. The application uses Streamlit's multipage app functionality with pages in the `pages/` directory.

### AI System Design
The chatbot uses a hybrid approach:
- Structured data queries through SpotifyDataAnalyzer
- Constrained LLM responses to prevent hallucination
- Memory system for learning user preferences and maintaining context
- Support for multiple Ollama models with llama3.2:latest as default