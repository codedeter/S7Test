import time
import threading
import random
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


@dataclass
class ConnectionStats:
    total_connections: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    total_data_reads: int = 0
    successful_reads: int = 0
    failed_reads: int = 0
    bytes_read: int = 0
    bytes_written: int = 0
    last_connection_time: Optional[float] = None
    last_disconnection_time: Optional[float] = None
    total_disconnection_duration: float = 0.0
    current_disconnection_start: Optional[float] = None
    
    def record_connection_success(self):
        self.total_connections += 1
        self.successful_connections += 1
        self.last_connection_time = time.time()
        if self.current_disconnection_start:
            duration = time.time() - self.current_disconnection_start
            self.total_disconnection_duration += duration
            self.current_disconnection_start = None
    
    def record_connection_failure(self):
        self.total_connections += 1
        self.failed_connections += 1
        if not self.current_disconnection_start:
            self.current_disconnection_start = time.time()
    
    def record_disconnection(self):
        self.last_disconnection_time = time.time()
        if not self.current_disconnection_start:
            self.current_disconnection_start = time.time()
    
    def record_read(self, success: bool, bytes_count: int = 0):
        self.total_data_reads += 1
        if success:
            self.successful_reads += 1
            self.bytes_read += bytes_count
        else:
            self.failed_reads += 1
    
    def get_connection_rate(self) -> float:
        if self.total_connections == 0:
            return 0.0
        return (self.successful_connections / self.total_connections) * 100
    
    def get_read_success_rate(self) -> float:
        if self.total_data_reads == 0:
            return 0.0
        return (self.successful_reads / self.total_data_reads) * 100


@dataclass
class ConnectionConfig:
    max_retry_attempts: int = 0  # 0 = infinite
    base_retry_interval: float = 5.0
    max_retry_interval: float = 120.0
    backoff_factor: float = 1.5
    enable_jitter: bool = True
    health_check_interval: float = 30.0
    connection_timeout: float = 15.0
    read_timeout: float = 5.0


class ConnectionPool:
    def __init__(self, config: ConnectionConfig = None):
        self._config = config or ConnectionConfig()
        self._connections: Dict[str, Any] = {}
        self._states: Dict[str, ConnectionState] = {}
        self._stats: Dict[str, ConnectionStats] = {}
        self._lock = threading.Lock()
        self._health_check_thread = None
        self._health_check_running = False
        self._state_callbacks: List[Callable[[str, ConnectionState, str], None]] = []
    
    def add_connection(self, device_id: str, connection: Any):
        with self._lock:
            self._connections[device_id] = connection
            self._states[device_id] = ConnectionState.DISCONNECTED
            self._stats[device_id] = ConnectionStats()
    
    def remove_connection(self, device_id: str):
        with self._lock:
            if device_id in self._connections:
                del self._connections[device_id]
                del self._states[device_id]
                del self._stats[device_id]
    
    def get_connection(self, device_id: str) -> Optional[Any]:
        with self._lock:
            return self._connections.get(device_id)
    
    def get_state(self, device_id: str) -> ConnectionState:
        with self._lock:
            return self._states.get(device_id, ConnectionState.DISCONNECTED)
    
    def set_state(self, device_id: str, state: ConnectionState, reason: str = ""):
        with self._lock:
            old_state = self._states.get(device_id)
            self._states[device_id] = state
        
        self._notify_state_change(device_id, state, reason)
        
        if state == ConnectionState.CONNECTED:
            self._stats[device_id].record_connection_success()
        elif state in (ConnectionState.ERROR, ConnectionState.DISCONNECTED):
            self._stats[device_id].record_disconnection()
        elif state == ConnectionState.RECONNECTING:
            self._stats[device_id].record_connection_failure()
    
    def get_stats(self, device_id: str) -> Optional[ConnectionStats]:
        with self._lock:
            return self._stats.get(device_id)
    
    def get_all_stats(self) -> Dict[str, ConnectionStats]:
        with self._lock:
            return self._stats.copy()
    
    def get_retry_interval(self, attempt: int) -> float:
        if attempt == 0:
            return self._config.base_retry_interval
        
        # 指数退避，但增长更平缓
        interval = self._config.base_retry_interval * (self._config.backoff_factor ** min(attempt - 1, 10))
        interval = min(interval, self._config.max_retry_interval)
        
        if self._config.enable_jitter:
            # 添加抖动来避免多个设备同时重连
            jitter = interval * 0.2 * (random.random() * 2 - 1)
            interval = max(self._config.base_retry_interval, interval + jitter)
        
        print(f"[ConnectionPool] Retry attempt {attempt}, interval: {interval:.2f}s")
        return interval
    
    def add_state_callback(self, callback: Callable[[str, ConnectionState, str], None]):
        self._state_callbacks.append(callback)
    
    def _notify_state_change(self, device_id: str, state: ConnectionState, reason: str):
        for callback in self._state_callbacks:
            try:
                callback(device_id, state, reason)
            except Exception as e:
                print(f"[ConnectionPool] Error in state callback: {e}")
    
    def start_health_check(self):
        if self._health_check_running:
            return
        
        self._health_check_running = True
        
        def health_check_loop():
            while self._health_check_running:
                try:
                    self._perform_health_check()
                except Exception as e:
                    print(f"[ConnectionPool] Health check error: {e}")
                time.sleep(self._config.health_check_interval)
        
        self._health_check_thread = threading.Thread(target=health_check_loop, daemon=True)
        self._health_check_thread.start()
    
    def stop_health_check(self):
        self._health_check_running = False
        if self._health_check_thread:
            self._health_check_thread.join(timeout=2)
    
    def _perform_health_check(self):
        with self._lock:
            for device_id, conn in self._connections.items():
                current_state = self._states[device_id]
                
                if current_state == ConnectionState.CONNECTED:
                    try:
                        if hasattr(conn, 'check_connection'):
                            if not conn.check_connection():
                                print(f"[ConnectionPool] Health check failed for {device_id}, marking as reconnecting")
                                self.set_state(device_id, ConnectionState.RECONNECTING, "Health check failed")
                    except Exception as e:
                        print(f"[ConnectionPool] Health check error for {device_id}: {e}")
                        self.set_state(device_id, ConnectionState.RECONNECTING, f"Health check exception: {e}")
                elif current_state in (ConnectionState.DISCONNECTED, ConnectionState.ERROR):
                    # 自动启动重连
                    print(f"[ConnectionPool] Health check detected {device_id} in {current_state}, triggering reconnect")
                    self.set_state(device_id, ConnectionState.RECONNECTING, "Health check triggered reconnect")
    
    def warm_up_connections(self, device_ids: List[str] = None):
        devices_to_warm = device_ids or list(self._connections.keys())
        
        def warm_up_device(device_id):
            conn = self.get_connection(device_id)
            if conn and hasattr(conn, 'connect'):
                print(f"[ConnectionPool] Warming up connection for {device_id}")
                try:
                    conn.connect()
                except Exception as e:
                    print(f"[ConnectionPool] Warm up failed for {device_id}: {e}")
        
        threads = []
        for device_id in devices_to_warm:
            thread = threading.Thread(target=warm_up_device, args=(device_id,), daemon=True)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join(timeout=self._config.connection_timeout)
    
    def get_pool_summary(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._connections)
            connected = sum(1 for s in self._states.values() if s == ConnectionState.CONNECTED)
            connecting = sum(1 for s in self._states.values() if s == ConnectionState.CONNECTING)
            reconnecting = sum(1 for s in self._states.values() if s == ConnectionState.RECONNECTING)
            error = sum(1 for s in self._states.values() if s == ConnectionState.ERROR)
            disconnected = sum(1 for s in self._states.values() if s == ConnectionState.DISCONNECTED)
        
        return {
            'total_devices': total,
            'connected': connected,
            'connecting': connecting,
            'reconnecting': reconnecting,
            'error': error,
            'disconnected': disconnected,
            'health': {
                'overall_connection_rate': self._calculate_overall_connection_rate(),
                'overall_read_success_rate': self._calculate_overall_read_rate()
            }
        }
    
    def _calculate_overall_connection_rate(self) -> float:
        total_connections = 0
        successful = 0
        for stats in self._stats.values():
            total_connections += stats.total_connections
            successful += stats.successful_connections
        return (successful / total_connections) * 100 if total_connections > 0 else 0.0
    
    def _calculate_overall_read_rate(self) -> float:
        total_reads = 0
        successful = 0
        for stats in self._stats.values():
            total_reads += stats.total_data_reads
            successful += stats.successful_reads
        return (successful / total_reads) * 100 if total_reads > 0 else 0.0


def create_connection_pool(config: ConnectionConfig = None) -> ConnectionPool:
    return ConnectionPool(config)