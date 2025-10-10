# 🎵 Sara's Spotify

An interactive web application showcasing my personal Spotify listening history with AI-powered insights.

## Features

- **📊 Streaming History**: Comprehensive visualizations of listening patterns, top artists, and songs
- **🤖 SpotiBoti**: AI chatbot (powered by Groq) that answers questions about my music taste
- **🎵 Song Analysis**: Detailed analysis of individual tracks with audio features
- **🎯 Recommendations**: Personalized music recommendations based on listening history

## Tech Stack

- **Frontend**: Streamlit
- **Data Visualization**: Plotly, Matplotlib, Seaborn
- **AI/ML**: Groq API (Mixtral model)
- **APIs**: Spotify Web API

## Live Demo

🌐 [Visit the live app](#) _(link will be added after deployment)_

## Local Development

### Prerequisites
- Python 3.8+
- Groq API key (get from [console.groq.com](https://console.groq.com))

### Installation

1. Clone the repository
```bash
git clone <your-repo-url>
cd Spotify
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Set up secrets
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml and add your Groq API key
```

4. Run the app
```bash
streamlit run spotify_app.py
```

## Data

This app uses my personal Spotify streaming history data. The data has been enriched with:
- Artist genres
- Album artwork
- Audio features (danceability, energy, valence, etc.)

## Deployment

Deployed on Streamlit Community Cloud. To deploy your own version:

1. Fork this repository
2. Sign up at [share.streamlit.io](https://share.streamlit.io)
3. Add your Groq API key to Streamlit secrets
4. Deploy!

## License

Personal project - feel free to fork and adapt for your own Spotify data!

---

Made with ❤️ and 🎵
