import functools
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

class CacheEntry:
    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.created_at = datetime.now()
        self.ttl = ttl
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl)

class SimpleCache:
    def __init__(self, maxsize: int = 128, ttl: int = 3600):
        self.cache = {}
        self.maxsize = maxsize
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self.cache:
            entry = self.cache[key]
            if not entry.is_expired():
                return entry.value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Set value in cache."""
        if len(self.cache) >= self.maxsize:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k].created_at)
            del self.cache[oldest_key]
        
        self.cache[key] = CacheEntry(value, self.ttl)
    
    def clear(self):
        """Clear entire cache."""
        self.cache.clear()

# Global cache instance
_cache = SimpleCache(maxsize=256, ttl=3600)

def cached(ttl: int = 3600):
    """Decorator to cache function results."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Generate cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Check cache
            cached_result = _cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            _cache.set(cache_key, result)
            
            return result
        return wrapper
    return decorator

# Usage example:
@cached(ttl=3600)  # Cache for 1 hour
def scrape_word(word: str):
    """Scrape Reddit for word usage."""
    # Implementation
    pass