import json
import os
import pandas as pd
from datetime import datetime

class ArtworkCache:
    def __init__(self, cache_file='data/track_artwork_cache.json'):
        self.cache_file = cache_file
        self.cache = self.load_cache()

    def load_cache(self):
        """Load artwork cache from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_cache(self):
        """Save artwork cache to file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving artwork cache: {e}")

    def get_track_key(self, track_name, artist_name):
        """Create a unique key for track + artist combination"""
        return f"{track_name.lower().strip()}|||{artist_name.lower().strip()}"

    def get_track_artwork(self, track_name, artist_name):
        """Get artwork for a track from cache"""
        key = self.get_track_key(track_name, artist_name)
        return self.cache.get(key, None)

    def set_track_artwork(self, track_name, artist_name, artwork_url):
        """Set artwork for a track in cache"""
        key = self.get_track_key(track_name, artist_name)
        self.cache[key] = {
            'artwork_url': artwork_url,
            'track_name': track_name,
            'artist_name': artist_name,
            'updated': datetime.now().isoformat()
        }

    def get_cache_stats(self):
        """Get statistics about the cache"""
        return {
            'total_tracks': len(self.cache),
            'file_size': os.path.getsize(self.cache_file) if os.path.exists(self.cache_file) else 0
        }

    def cleanup_old_entries(self, days=30):
        """Remove cache entries older than specified days"""
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=days)

        to_remove = []
        for key, data in self.cache.items():
            try:
                updated = datetime.fromisoformat(data.get('updated', ''))
                if updated < cutoff_date:
                    to_remove.append(key)
            except:
                to_remove.append(key)  # Remove invalid entries

        for key in to_remove:
            del self.cache[key]

        return len(to_remove)