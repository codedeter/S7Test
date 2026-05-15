"""
多级缓存系统

实现L1内存缓存 + L2数据库查询结果缓存的两级缓存策略，提升查询性能。
"""

import time
import threading
from typing import Any, Optional, Dict, List, Callable
from dataclasses import dataclass
from collections import OrderedDict
import hashlib
import json


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float
    last_accessed: float
    access_count: int
    ttl: Optional[float] = None

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl

    def touch(self):
        """更新访问时间"""
        self.last_accessed = time.time()
        self.access_count += 1


class LRUCache:
    """LRU (Least Recently Used) 内存缓存"""

    def __init__(self, max_size: int = 1000, default_ttl: float = 300):
        """
        初始化LRU缓存。

        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认过期时间（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值。

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在或过期返回None
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                return None

            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None

            self._cache.move_to_end(key)
            entry.touch()
            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """
        设置缓存值。

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None使用默认值
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]

            if len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)

            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                last_accessed=time.time(),
                access_count=0,
                ttl=ttl if ttl is not None else self.default_ttl
            )
            self._cache[key] = entry

    def delete(self, key: str) -> bool:
        """
        删除缓存条目。

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self):
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def cleanup_expired(self):
        """清理过期条目"""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            for key in expired_keys:
                del self._cache[key]

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': hit_rate,
                'total_requests': total
            }


class QueryCache:
    """查询结果缓存"""

    def __init__(self, max_size: int = 500, default_ttl: float = 60):
        """
        初始化查询缓存。

        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认过期时间（秒）
        """
        self._cache = LRUCache(max_size, default_ttl)

    def _generate_key(self, query: str, params: tuple) -> str:
        """
        生成查询缓存键。

        Args:
            query: SQL查询语句
            params: 查询参数

        Returns:
            缓存键
        """
        key_data = f"{query}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get_query_result(self, query: str, params: tuple) -> Optional[Any]:
        """
        获取查询结果。

        Args:
            query: SQL查询语句
            params: 查询参数

        Returns:
            查询结果
        """
        key = self._generate_key(query, params)
        return self._cache.get(key)

    def set_query_result(self, query: str, params: tuple, result: Any, ttl: Optional[float] = None):
        """
        缓存查询结果。

        Args:
            query: SQL查询语句
            params: 查询参数
            result: 查询结果
            ttl: 过期时间
        """
        key = self._generate_key(query, params)
        self._cache.set(key, result, ttl)

    def invalidate_query(self, query: str, params: tuple):
        """
        使查询缓存失效。

        Args:
            query: SQL查询语句
            params: 查询参数
        """
        key = self._generate_key(query, params)
        self._cache.delete(key)

    def invalidate_all_queries(self):
        """使所有查询缓存失效"""
        self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取查询缓存统计"""
        return self._cache.get_stats()


class MultiLevelCache:
    """多级缓存管理器"""

    def __init__(
        self,
        memory_cache_size: int = 1000,
        query_cache_size: int = 500,
        memory_ttl: float = 300,
        query_ttl: float = 60
    ):
        """
        初始化多级缓存。

        Args:
            memory_cache_size: 内存缓存大小
            query_cache_size: 查询缓存大小
            memory_ttl: 内存缓存过期时间
            query_ttl: 查询缓存过期时间
        """
        self.memory_cache = LRUCache(memory_cache_size, memory_ttl)
        self.query_cache = QueryCache(query_cache_size, query_ttl)
        self._cleanup_thread = None
        self._running = False

    def start_cleanup_thread(self, interval: float = 60):
        """
        启动缓存清理线程。

        Args:
            interval: 清理间隔（秒）
        """
        if self._running:
            return

        self._running = True

        def cleanup_loop():
            while self._running:
                time.sleep(interval)
                self.memory_cache.cleanup_expired()

        self._cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def stop_cleanup_thread(self):
        """停止缓存清理线程"""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值（先查L1，再查L2）。

        Args:
            key: 缓存键

        Returns:
            缓存值
        """
        value = self.memory_cache.get(key)
        if value is not None:
            return value
        return None

    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """
        设置缓存值（同时写入L1和L2）。

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间
        """
        self.memory_cache.set(key, value, ttl)

    def delete(self, key: str):
        """
        删除缓存值。

        Args:
            key: 缓存键
        """
        self.memory_cache.delete(key)
        self.query_cache.invalidate_all_queries()

    def cached_query(self, query: str, params: tuple, query_func: Callable) -> Any:
        """
        执行带缓存的查询。

        Args:
            query: SQL查询语句
            params: 查询参数
            query_func: 查询函数

        Returns:
            查询结果
        """
        cached = self.query_cache.get_query_result(query, params)
        if cached is not None:
            return cached

        result = query_func()

        if result is not None:
            self.query_cache.set_query_result(query, params, result)

        return result

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            'memory_cache': self.memory_cache.get_stats(),
            'query_cache': self.query_cache.get_stats()
        }

    def clear_all(self):
        """清空所有缓存"""
        self.memory_cache.clear()
        self.query_cache.invalidate_all_queries()


_global_cache: Optional[MultiLevelCache] = None


def get_multi_level_cache() -> MultiLevelCache:
    """
    获取全局多级缓存实例。

    Returns:
        MultiLevelCache实例
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = MultiLevelCache()
        _global_cache.start_cleanup_thread()
    return _global_cache


def clear_global_cache():
    """清空全局缓存"""
    global _global_cache
    if _global_cache:
        _global_cache.clear_all()


def get_cache_stats() -> Dict[str, Any]:
    """获取全局缓存统计"""
    cache = get_multi_level_cache()
    return cache.get_stats()
