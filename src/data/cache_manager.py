import threading
import time
from collections import OrderedDict
from typing import Any, Optional, Callable


class CacheItem:
    def __init__(self, value: Any, ttl: float = None):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
    
    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return (time.time() - self.created_at) > self.ttl


class CacheManager:
    def __init__(self, max_size: int = 10000, default_ttl: float = 300.0):
        self._cache = OrderedDict()
        self._lock = threading.Lock()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'sets': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                item = self._cache[key]
                if not item.is_expired():
                    self._cache.move_to_end(key)
                    self._stats['hits'] += 1
                    return item.value
                else:
                    del self._cache[key]
                    self._stats['evictions'] += 1
            self._stats['misses'] += 1
            return None
    
    def set(self, key: str, value: Any, ttl: float = None) -> None:
        with self._lock:
            ttl = ttl if ttl is not None else self._default_ttl
            
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
                self._stats['evictions'] += 1
            
            self._cache[key] = CacheItem(value, ttl)
            self._stats['sets'] += 1
    
    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if pattern in k]
            for k in keys_to_delete:
                del self._cache[k]
            return len(keys_to_delete)
    
    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
    
    def get_stats(self) -> dict:
        with self._lock:
            stats = self._stats.copy()
            stats['size'] = len(self._cache)
            stats['max_size'] = self._max_size
            return stats
    
    def get_or_set(self, key: str, loader: Callable[[], Any], ttl: float = None) -> Any:
        value = self.get(key)
        if value is not None:
            return value
        
        value = loader()
        self.set(key, value, ttl)
        return value


_global_cache_manager = None
_cache_manager_lock = threading.Lock()


def get_cache_manager() -> CacheManager:
    global _global_cache_manager
    with _cache_manager_lock:
        if _global_cache_manager is None:
            _global_cache_manager = CacheManager()
        return _global_cache_manager
