"""
异步数据采集和请求优化模块

解决请求超时和连接不稳定问题。
"""

import asyncio
import time
import threading
import concurrent.futures
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed


class TaskPriority(Enum):
    """任务优先级"""
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


@dataclass
class AsyncTask:
    """异步任务"""
    task_id: str
    coroutine: Callable
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: float = 30.0
    retries: int = 3
    delay_between_retries: float = 1.0
    result: Optional[Any] = None
    error: Optional[Exception] = None
    completed: bool = False
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    def execute(self):
        """执行任务"""
        self.started_at = time.time()
        attempts = 0
        
        while attempts < self.retries:
            try:
                self.result = self.coroutine()
                self.completed = True
                break
            except Exception as e:
                attempts += 1
                self.error = e
                if attempts < self.retries:
                    time.sleep(self.delay_between_retries * (2 ** attempts))
        
        self.completed_at = time.time()


class AsyncTaskManager:
    """异步任务管理器"""
    
    def __init__(self, max_workers: int = 20):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: Dict[str, AsyncTask] = {}
        self._futures: Dict[str, concurrent.futures.Future] = {}
        self._lock = threading.RLock()
        self._running = True
        
    def submit_task(self, task_id: str, coroutine: Callable, 
                   priority: TaskPriority = TaskPriority.NORMAL,
                   timeout: float = 30.0, retries: int = 3) -> str:
        """提交异步任务"""
        with self._lock:
            if task_id in self._tasks:
                return task_id
            
            task = AsyncTask(
                task_id=task_id,
                coroutine=coroutine,
                priority=priority,
                timeout=timeout,
                retries=retries
            )
            self._tasks[task_id] = task
            
            future = self._executor.submit(task.execute)
            self._futures[task_id] = future
            
            future.add_done_callback(lambda f, tid=task_id: self._on_task_complete(tid))
        
        return task_id
    
    def _on_task_complete(self, task_id: str):
        """任务完成回调"""
        with self._lock:
            if task_id in self._futures:
                del self._futures[task_id]
    
    def get_task_result(self, task_id: str) -> Optional[Any]:
        """获取任务结果"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.completed:
                return task.result
            return None
    
    def get_task_error(self, task_id: str) -> Optional[Exception]:
        """获取任务错误"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task and not task.completed:
                return task.error
            return None
    
    def is_task_completed(self, task_id: str) -> bool:
        """检查任务是否完成"""
        with self._lock:
            task = self._tasks.get(task_id)
            return task is not None and task.completed
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            if task_id in self._futures:
                self._futures[task_id].cancel()
                del self._futures[task_id]
                if task_id in self._tasks:
                    del self._tasks[task_id]
                return True
        return False
    
    def shutdown(self, wait: bool = True):
        """关闭任务管理器"""
        self._running = False
        self._executor.shutdown(wait=wait)


class DeviceDataFetcher:
    """设备数据采集器"""
    
    def __init__(self, device_manager):
        self._device_manager = device_manager
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._last_fetch_time: Dict[str, float] = {}
        self._fetch_lock = threading.RLock()
        self._cache: Dict[str, Any] = {}
        self._cache_timeout = 5.0  # 缓存5秒
    
    def fetch_device_data(self, device_id: str, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """异步获取设备数据"""
        def fetch_task():
            try:
                collector = self._device_manager.collectors.get(device_id)
                if not collector:
                    return None
                
                client = self._device_manager.clients.get(device_id)
                if not client or not client.connected:
                    return collector.get_cached_data()
                
                return collector.collect_all_data()
            except Exception as e:
                print(f"[DataFetcher] Error fetching {device_id}: {e}")
                collector = self._device_manager.collectors.get(device_id)
                if collector:
                    return collector.get_cached_data()
                return None
        
        future = self._executor.submit(fetch_task)
        
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            print(f"[DataFetcher] Timeout fetching {device_id}")
            future.cancel()
            collector = self._device_manager.collectors.get(device_id)
            if collector:
                return collector.get_cached_data()
            return None
        except Exception as e:
            print(f"[DataFetcher] Exception fetching {device_id}: {e}")
            collector = self._device_manager.collectors.get(device_id)
            if collector:
                return collector.get_cached_data()
            return None
    
    def fetch_all_devices_data(self, timeout_per_device: float = 3.0) -> Dict[str, Any]:
        """并行获取所有设备数据"""
        results = {}
        futures = {}
        
        with self._fetch_lock:
            for device_id in self._device_manager.devices:
                futures[device_id] = self._executor.submit(
                    self.fetch_device_data, device_id, timeout_per_device
                )
        
        for device_id, future in futures.items():
            try:
                data = future.result(timeout=timeout_per_device + 2.0)
                if data:
                    results[device_id] = data
            except Exception as e:
                print(f"[DataFetcher] Failed to fetch {device_id}: {e}")
                collector = self._device_manager.collectors.get(device_id)
                if collector:
                    results[device_id] = collector.get_cached_data()
        
        return results
    
    def shutdown(self):
        """关闭采集器"""
        self._executor.shutdown(wait=True)


class RequestTimeoutManager:
    """请求超时管理器"""
    
    def __init__(self):
        self._timeouts = {
            'plc_connection': 15.0,
            'data_read': 5.0,
            'api_request': 30.0,
            'socket_io': 10.0,
            'database_query': 10.0
        }
        self._pending_requests: Dict[str, float] = {}
        self._lock = threading.RLock()
    
    def get_timeout(self, request_type: str) -> float:
        """获取超时时间"""
        return self._timeouts.get(request_type, 30.0)
    
    def set_timeout(self, request_type: str, timeout: float):
        """设置超时时间"""
        with self._lock:
            self._timeouts[request_type] = timeout
    
    def track_request(self, request_id: str):
        """追踪请求开始"""
        with self._lock:
            self._pending_requests[request_id] = time.time()
    
    def complete_request(self, request_id: str) -> Optional[float]:
        """完成请求并返回耗时"""
        with self._lock:
            if request_id in self._pending_requests:
                start_time = self._pending_requests[request_id]
                del self._pending_requests[request_id]
                return time.time() - start_time
        return None
    
    def get_slow_requests(self, threshold: float = 5.0) -> List[Tuple[str, float]]:
        """获取慢请求列表"""
        slow_requests = []
        now = time.time()
        
        with self._lock:
            for request_id, start_time in self._pending_requests.items():
                elapsed = now - start_time
                if elapsed > threshold:
                    slow_requests.append((request_id, elapsed))
        
        return slow_requests


class RateLimiter:
    """请求速率限制器"""
    
    def __init__(self, max_requests: int, time_window: float):
        self._max_requests = max_requests
        self._time_window = time_window
        self._requests: List[float] = []
        self._lock = threading.Lock()
    
    def acquire(self) -> bool:
        """获取请求许可"""
        with self._lock:
            now = time.time()
            
            # 移除过期的请求记录
            self._requests = [r for r in self._requests if now - r < self._time_window]
            
            if len(self._requests) < self._max_requests:
                self._requests.append(now)
                return True
            
            return False
    
    def get_rate(self) -> float:
        """获取当前请求速率"""
        with self._lock:
            now = time.time()
            recent_requests = [r for r in self._requests if now - r < self._time_window]
            return len(recent_requests) / self._time_window


class OptimizedDataCollection:
    """优化的数据采集器"""
    
    def __init__(self, device_manager):
        self._device_manager = device_manager
        self._data_fetcher = DeviceDataFetcher(device_manager)
        self._timeout_manager = RequestTimeoutManager()
        self._rate_limiter = RateLimiter(max_requests=100, time_window=1.0)
        self._running = False
        self._collection_thread = None
        self._interval = 100  # ms
        self._data_callback = None
        self._shutdown_event = threading.Event()
    
    def set_collection_interval(self, interval_ms: int):
        """设置采集间隔"""
        self._interval = interval_ms
    
    def set_data_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """设置数据回调"""
        self._data_callback = callback
    
    def start(self):
        """启动采集"""
        self._running = True
        self._shutdown_event.clear()
        
        def collection_loop():
            while self._running and not self._shutdown_event.is_set():
                try:
                    if not self._rate_limiter.acquire():
                        time.sleep(0.01)
                        continue
                    
                    data = self._data_fetcher.fetch_all_devices_data(timeout_per_device=2.0)
                    
                    if self._data_callback:
                        try:
                            self._data_callback(data)
                        except Exception as e:
                            print(f"[OptimizedCollection] Callback error: {e}")
                    
                except Exception as e:
                    print(f"[OptimizedCollection] Collection error: {e}")
                
                time.sleep(self._interval / 1000)
        
        self._collection_thread = threading.Thread(target=collection_loop, daemon=True)
        self._collection_thread.start()
        print("[OptimizedCollection] Optimized data collection started")
    
    def stop(self):
        """停止采集"""
        self._running = False
        self._shutdown_event.set()
        if self._collection_thread:
            self._collection_thread.join(timeout=5)
        self._data_fetcher.shutdown()
        print("[OptimizedCollection] Optimized data collection stopped")


def create_optimized_collector(device_manager) -> OptimizedDataCollection:
    """创建优化的数据采集器"""
    return OptimizedDataCollection(device_manager)


def create_task_manager(max_workers: int = 20) -> AsyncTaskManager:
    """创建异步任务管理器"""
    return AsyncTaskManager(max_workers=max_workers)


def create_timeout_manager() -> RequestTimeoutManager:
    """创建超时管理器"""
    return RequestTimeoutManager()
