"""
Advanced Cache Manager with Size Tracking and LRU Eviction
Stores cached news results with frequency tracking and automatic cleanup
Maximum size: 100MB (configurable)
"""

import json
import time
import os
from pathlib import Path
from typing import Optional, Dict, List, Any

CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

MAX_CACHE_SIZE_MB = int(os.getenv("MAX_CACHE_SIZE_MB", "100"))
MAX_CACHE_SIZE_BYTES = MAX_CACHE_SIZE_MB * 1024 * 1024

class CacheEntry:
    def __init__(self, query: str, results: List[Dict], news_data: str = ""):
        self.query = query
        self.results = results  # SERP results
        self.news_data = news_data  # Combined cached articles text
        self.frequency = 1  # How many times this has been used
        self.created_at = time.time()
        self.last_accessed = time.time()
        self.access_count = 0  # Total accesses
        self.size_bytes = len(json.dumps({"query": query, "results": results, "news_data": news_data}))

    def access(self):
        """Update access stats"""
        self.last_accessed = time.time()
        self.access_count += 1
        self.frequency = min(self.frequency + 0.1, 10.0)  # Cap at 10

    def to_dict(self):
        return {
            "query": self.query,
            "results": self.results,
            "news_data": self.news_data,
            "frequency": self.frequency,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "size_bytes": self.size_bytes,
        }


class CacheManager:
    def __init__(self):
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.total_size = 0
        self._load_persistent_cache()

    def _load_persistent_cache(self):
        """Load cache from disk on startup"""
        cache_file = CACHE_DIR / "news_cache.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
                for query, entry_data in data.items():
                    entry = CacheEntry(
                        query=entry_data["query"],
                        results=entry_data["results"],
                        news_data=entry_data.get("news_data", "")
                    )
                    entry.frequency = entry_data["frequency"]
                    entry.created_at = entry_data["created_at"]
                    entry.last_accessed = entry_data["last_accessed"]
                    entry.access_count = entry_data["access_count"]
                    self.memory_cache[query] = entry
                    self.total_size += entry.size_bytes
            except Exception as e:
                print(f"Failed to load persistent cache: {e}")

    def _save_persistent_cache(self):
        """Save top 50 most frequent cache entries to disk (compact format, no indent)"""
        cache_file = CACHE_DIR / "news_cache.json"
        try:
            # Keep only top 50 by frequency and access
            sorted_entries = sorted(
                self.memory_cache.items(),
                key=lambda x: (x[1].frequency * x[1].access_count),
                reverse=True
            )[:50]
            
            data = {query: entry.to_dict() for query, entry in sorted_entries}
            # OPTIMIZATION: Write compact JSON (no indent) for faster I/O
            cache_file.write_text(json.dumps(data))
        except Exception as e:
            print(f"Failed to save persistent cache: {e}")

    def _check_and_evict(self):
        """Check size and evict LRU entries if over limit"""
        if self.total_size > MAX_CACHE_SIZE_BYTES:
            # Sort by score (frequency * access_count * recency)
            scored = {}
            current_time = time.time()
            for query, entry in self.memory_cache.items():
                age_days = (current_time - entry.created_at) / 86400
                recency_score = 1.0 / (1.0 + age_days)  # Recent = high score
                score = entry.frequency * entry.access_count * recency_score
                scored[query] = (score, entry.size_bytes)
            
            # Remove lowest scoring entries until under limit
            for query, (score, size) in sorted(scored.items(), key=lambda x: x[1][0]):
                if self.total_size <= MAX_CACHE_SIZE_BYTES * 0.8:  # Keep 80% capacity
                    break
                del self.memory_cache[query]
                self.total_size -= size

    def get(self, query: str, normalize: bool = True) -> Optional[Dict]:
        """Get cached results for a query"""
        cache_key = self._normalize_query(query) if normalize else query
        
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            entry.access()
            return {
                "results": entry.results,
                "news_data": entry.news_data,
                "source": "cache",
                "cached_info": {
                    "accessed_count": entry.access_count,
                    "age_seconds": time.time() - entry.created_at,
                }
            }
        return None

    def set(self, query: str, results: List[Dict], news_data: str = "", normalize: bool = True):
        """Cache results for a query"""
        cache_key = self._normalize_query(query) if normalize else query
        
        # Skip if already cached (prevent duplicate storage)
        if cache_key in self.memory_cache:
            self.memory_cache[cache_key].access()
            return
        
        entry = CacheEntry(query, results, news_data)
        old_size = self.memory_cache.get(cache_key, None)
        if old_size:
            self.total_size -= old_size.size_bytes
        
        self.memory_cache[cache_key] = entry
        self.total_size += entry.size_bytes
        
        # Evict if necessary
        self._check_and_evict()
        
        # Save to disk periodically
        if len(self.memory_cache) % 10 == 0:
            self._save_persistent_cache()

    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        total_entries = len(self.memory_cache)
        total_accesses = sum(e.access_count for e in self.memory_cache.values())
        avg_frequency = sum(e.frequency for e in self.memory_cache.values()) / max(total_entries, 1)
        
        return {
            "total_entries": total_entries,
            "total_size_mb": round(self.total_size / 1024 / 1024, 2),
            "max_size_mb": MAX_CACHE_SIZE_MB,
            "usage_percent": round((self.total_size / MAX_CACHE_SIZE_BYTES) * 100, 1),
            "total_accesses": total_accesses,
            "avg_frequency": round(avg_frequency, 2),
        }

    def clear(self):
        """Clear all cache"""
        self.memory_cache.clear()
        self.total_size = 0
        cache_file = CACHE_DIR / "news_cache.json"
        if cache_file.exists():
            cache_file.unlink()

    @staticmethod
    def _normalize_query(query: str) -> str:
        """Normalize query for consistent caching"""
        import re
        # Remove URLs, normalize whitespace, lowercase
        query = re.sub(r"https?://\S+", " ", query)
        query = re.sub(r"\s+", " ", query).strip().lower()
        return query[:200]  # Limit key length


# Global cache instance
_cache_manager: Optional[CacheManager] = None

def get_cache_manager() -> CacheManager:
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
