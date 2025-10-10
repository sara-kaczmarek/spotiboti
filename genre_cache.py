import json
import os
import pandas as pd
from datetime import datetime

class GenreCache:
    def __init__(self, cache_file='data/artist_genres_cache.json'):
        self.cache_file = cache_file
        self.cache = self.load_cache()

    def load_cache(self):
        """Load genre cache from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_cache(self):
        """Save genre cache to file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving cache: {e}")

    def get_artist_genres(self, artist_name):
        """Get genres for an artist from cache"""
        return self.cache.get(artist_name, None)

    def set_artist_genres(self, artist_name, genres):
        """Set genres for an artist in cache"""
        self.cache[artist_name] = {
            'genres': genres,
            'updated': datetime.now().isoformat()
        }

    def get_cache_stats(self):
        """Get statistics about the cache"""
        return {
            'total_artists': len(self.cache),
            'file_size': os.path.getsize(self.cache_file) if os.path.exists(self.cache_file) else 0
        }

    def cleanup_old_entries(self, days=30):
        """Remove cache entries older than specified days"""
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=days)

        to_remove = []
        for artist, data in self.cache.items():
            try:
                updated = datetime.fromisoformat(data.get('updated', ''))
                if updated < cutoff_date:
                    to_remove.append(artist)
            except:
                to_remove.append(artist)  # Remove invalid entries

        for artist in to_remove:
            del self.cache[artist]

        return len(to_remove)