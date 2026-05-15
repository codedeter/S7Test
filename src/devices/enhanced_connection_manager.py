"""
增强型设备连接管理器

针对设备可能关机的情况，实现优雅的离线处理、智能重连和数据降级策略。
"""

import time
import threading
import random
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class DeviceStatus(Enum):
    """设备状态枚举"""
    OFFLINE = "offline"
    CONNECTING = "connecting"
    ONLINE = "online"
    ERROR = "error"
    RECONNECTING = "reconnecting"
    SUSPENDED = "suspended"


class OfflineReason(Enum):
    """离线原因枚举"""
    SHUTDOWN = "shutdown"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    AUTHENTICATION_FAILED = "authentication_failed"
    UNKNOWN = "unknown"


@dataclass
class DeviceContext:
    """设备上下文信息"""
    device_id: str
    last_online_time: Optional[float] = None
    last_offline_time: Optional[float] = None
    offline_reason: Optional[OfflineReason] = None
    consecutive_failures: int = 0
    max_consecutive_failures: int = 10
    suspend_threshold: int = 5
    is_suspended: bool = False
    suspend_until: Optional[float] = None
    last_reconnect_attempt: Optional[float] = None
    reconnect_count: int = 0
    total_offline_duration: float = 0.0
    
    def mark_online(self):
        """标记设备上线"""
        self.last_online_time = time.time()
        self.consecutive_failures = 0
        self.is_suspended = False
        self.suspend_until = None
        if self.last_offline_time:
            self.total_offline_duration += time.time() - self.last_offline_time
            self.last_offline_time = None
    
    def mark_offline(self, reason: OfflineReason):
        """标记设备离线"""
        if not self.last_offline_time:
            self.last_offline_time = time.time()
        self.offline_reason = reason
        self.consecutive_failures += 1
        
        if self.consecutive_failures >= self.suspend_threshold:
            self.suspend()
    
    def suspend(self):
        """挂起设备，暂停重连"""
        self.is_suspended = True
        suspend_duration = min(60 * (2 ** (self.consecutive_failures - self.suspend_threshold)), 3600)
        self.suspend_until = time.time() + suspend_duration
    
    def can_reconnect(self) -> bool:
        """检查是否可以尝试重连"""
        if self.is_suspended:
            if self.suspend_until and time.time() >= self.suspend_until:
                self.is_suspended = False
                self.suspend_until = None
                return True
            return False
        return True
    
    def record_reconnect_attempt(self):
        """记录重连尝试"""
        self.last_reconnect_attempt = time.time()
        self.reconnect_count += 1


@dataclass
class ConnectionConfig:
    """连接配置"""
    max_retry_attempts: int = 0  # 0 = infinite
    base_retry_interval: float = 5.0
    max_retry_interval: float = 300.0  # 5分钟最大间隔
    backoff_factor: float = 2.0
    enable_jitter: bool = True
    health_check_interval: float = 30.0
    connection_timeout: float = 15.0
    read_timeout: float = 5.0
    offline_threshold_seconds: float = 60.0  # 超过此时间认为设备关机
    shutdown_detection_threshold: int = 3  # 连续失败次数后认为关机


@dataclass
class ReconnectPolicy:
    """重连策略"""
    policy_type: str = "exponential"  # exponential, linear, fixed
    base_delay: float = 5.0
    max_delay: float = 300.0
    backoff_factor: float = 2.0
    jitter_factor: float = 0.2
    min_delay_between_attempts: float = 1.0


class EnhancedConnectionManager:
    """增强型连接管理器"""
    
    def __init__(self, config: ConnectionConfig = None):
        self._config = config or ConnectionConfig()
        self._connections: Dict[str, Any] = {}
        self._states: Dict[str, DeviceStatus] = {}
        self._device_contexts: Dict[str, DeviceContext] = {}
        self._lock = threading.RLock()
        self._reconnect_threads: Dict[str, threading.Thread] = {}
        self._state_callbacks: List[Callable[[str, DeviceStatus, str], None]] = []
        self._shutdown_detection_enabled = True
        self._running = True
        
        self._start_health_monitor()
    
    def _start_health_monitor(self):
        """启动健康监控线程"""
        def health_monitor_loop():
            while self._running:
                try:
                    self._monitor_device_health()
                except Exception as e:
                    print(f"[ConnectionManager] Health monitor error: {e}")
                time.sleep(self._config.health_check_interval)
        
        self._health_thread = threading.Thread(target=health_monitor_loop, daemon=True)
        self._health_thread.start()
    
    def add_device(self, device_id: str, connection: Any):
        """添加设备连接"""
        with self._lock:
            self._connections[device_id] = connection
            self._states[device_id] = DeviceStatus.OFFLINE
            self._device_contexts[device_id] = DeviceContext(device_id=device_id)
    
    def remove_device(self, device_id: str):
        """移除设备"""
        with self._lock:
            if device_id in self._connections:
                self._stop_reconnect_thread(device_id)
                del self._connections[device_id]
                del self._states[device_id]
                del self._device_contexts[device_id]
    
    def get_connection(self, device_id: str) -> Optional[Any]:
        """获取设备连接"""
        return self._connections.get(device_id)
    
    def get_status(self, device_id: str) -> DeviceStatus:
        """获取设备状态"""
        return self._states.get(device_id, DeviceStatus.OFFLINE)
    
    def set_status(self, device_id: str, status: DeviceStatus, reason: str = ""):
        """设置设备状态"""
        with self._lock:
            old_status = self._states.get(device_id)
            self._states[device_id] = status
        
        self._notify_state_change(device_id, status, reason)
        
        context = self._device_contexts.get(device_id)
        if context:
            if status == DeviceStatus.ONLINE:
                context.mark_online()
            elif status in (DeviceStatus.OFFLINE, DeviceStatus.ERROR):
                context.mark_offline(OfflineReason.UNKNOWN)
    
    def connect_device(self, device_id: str) -> bool:
        """连接设备"""
        context = self._device_contexts.get(device_id)
        if context and not context.can_reconnect():
            print(f"[ConnectionManager] {device_id} is suspended, skipping connect")
            return False
        
        try:
            self.set_status(device_id, DeviceStatus.CONNECTING, "Connecting")
            conn = self._connections.get(device_id)
            
            if conn and hasattr(conn, 'connect'):
                conn.connect()
                self.set_status(device_id, DeviceStatus.ONLINE, "Connected successfully")
                self._stop_reconnect_thread(device_id)
                return True
            else:
                self._handle_connection_failure(device_id, "No connection object")
                return False
        except Exception as e:
            self._handle_connection_failure(device_id, str(e))
            return False
    
    def disconnect_device(self, device_id: str, reason: str = "Manual disconnect"):
        """断开设备连接"""
        try:
            conn = self._connections.get(device_id)
            if conn and hasattr(conn, 'disconnect'):
                conn.disconnect()
        except Exception as e:
            print(f"[ConnectionManager] Error disconnecting {device_id}: {e}")
        
        self.set_status(device_id, DeviceStatus.OFFLINE, reason)
        self._stop_reconnect_thread(device_id)
    
    def _handle_connection_failure(self, device_id: str, error_message: str):
        """处理连接失败"""
        context = self._device_contexts.get(device_id)
        if not context:
            return
        
        # 检测是否为设备关机
        if self._shutdown_detection_enabled:
            if context.consecutive_failures >= self._config.shutdown_detection_threshold:
                self._detect_shutdown(device_id)
                return
        
        # 设置错误状态
        self.set_status(device_id, DeviceStatus.ERROR, error_message)
        
        # 启动或继续重连
        self._start_reconnect_thread(device_id)
    
    def _detect_shutdown(self, device_id: str):
        """检测设备是否关机"""
        context = self._device_contexts.get(device_id)
        if not context:
            return
        
        print(f"[ConnectionManager] Detected potential shutdown for {device_id}")
        context.mark_offline(OfflineReason.SHUTDOWN)
        self.set_status(device_id, DeviceStatus.OFFLINE, "Device shutdown detected")
        
        # 使用更长的重连间隔
        self._start_reconnect_thread(device_id, is_shutdown=True)
    
    def _start_reconnect_thread(self, device_id: str, is_shutdown: bool = False):
        """启动重连线程"""
        with self._lock:
            if device_id in self._reconnect_threads:
                return
            
            context = self._device_contexts.get(device_id)
            if context and not context.can_reconnect():
                return
        
        def reconnect_loop():
            attempt = 0
            while self._running:
                with self._lock:
                    status = self._states.get(device_id)
                    if status == DeviceStatus.ONLINE:
                        break
                    
                    context = self._device_contexts.get(device_id)
                    if context and not context.can_reconnect():
                        time.sleep(5)
                        continue
                
                # 计算重连间隔
                interval = self._calculate_reconnect_interval(attempt, is_shutdown)
                print(f"[ConnectionManager] {device_id} reconnect attempt {attempt}, waiting {interval:.2f}s")
                
                time.sleep(interval)
                
                if not self._running:
                    break
                
                # 尝试重连
                context.record_reconnect_attempt()
                if self.connect_device(device_id):
                    break
                
                attempt += 1
                
                with self._lock:
                    if device_id in self._reconnect_threads:
                        del self._reconnect_threads[device_id]
        
        thread = threading.Thread(target=reconnect_loop, daemon=True)
        with self._lock:
            self._reconnect_threads[device_id] = thread
        thread.start()
    
    def _stop_reconnect_thread(self, device_id: str):
        """停止重连线程"""
        with self._lock:
            if device_id in self._reconnect_threads:
                del self._reconnect_threads[device_id]
    
    def _calculate_reconnect_interval(self, attempt: int, is_shutdown: bool = False) -> float:
        """计算重连间隔"""
        base_interval = self._config.base_retry_interval
        
        if is_shutdown:
            # 设备关机时使用更长的基础间隔
            base_interval *= 3
        
        if attempt == 0:
            return base_interval
        
        # 指数退避
        interval = base_interval * (self._config.backoff_factor ** min(attempt, 10))
        interval = min(interval, self._config.max_retry_interval)
        
        # 添加抖动
        if self._config.enable_jitter:
            jitter = interval * 0.2 * (random.random() * 2 - 1)
            interval = max(self._config.base_retry_interval, interval + jitter)
        
        return interval
    
    def _monitor_device_health(self):
        """监控设备健康状态"""
        with self._lock:
            devices = list(self._connections.keys())
        
        for device_id in devices:
            status = self.get_status(device_id)
            
            if status == DeviceStatus.ONLINE:
                self._check_connection_health(device_id)
            elif status == DeviceStatus.OFFLINE:
                self._check_offline_duration(device_id)
    
    def _check_connection_health(self, device_id: str):
        """检查在线设备的健康状态"""
        conn = self._connections.get(device_id)
        if conn and hasattr(conn, 'check_connection'):
            try:
                if not conn.check_connection():
                    print(f"[ConnectionManager] Health check failed for {device_id}")
                    self._handle_connection_failure(device_id, "Health check failed")
            except Exception as e:
                print(f"[ConnectionManager] Health check exception for {device_id}: {e}")
                self._handle_connection_failure(device_id, f"Health check exception: {e}")
    
    def _check_offline_duration(self, device_id: str):
        """检查离线设备的离线时长"""
        context = self._device_contexts.get(device_id)
        if not context or not context.last_offline_time:
            return
        
        offline_duration = time.time() - context.last_offline_time
        if offline_duration > self._config.offline_threshold_seconds:
            if context.offline_reason != OfflineReason.SHUTDOWN:
                print(f"[ConnectionManager] {device_id} offline for {offline_duration:.1f}s, marking as shutdown")
                context.mark_offline(OfflineReason.SHUTDOWN)
                self.set_status(device_id, DeviceStatus.OFFLINE, "Long offline - assumed shutdown")
    
    def add_state_callback(self, callback: Callable[[str, DeviceStatus, str], None]):
        """添加状态变更回调"""
        self._state_callbacks.append(callback)
    
    def _notify_state_change(self, device_id: str, status: DeviceStatus, reason: str):
        """通知状态变更"""
        for callback in self._state_callbacks:
            try:
                callback(device_id, status, reason)
            except Exception as e:
                print(f"[ConnectionManager] Error in state callback: {e}")
    
    def get_device_context(self, device_id: str) -> Optional[DeviceContext]:
        """获取设备上下文"""
        return self._device_contexts.get(device_id)
    
    def get_status_summary(self) -> Dict[str, Any]:
        """获取状态摘要"""
        with self._lock:
            total = len(self._connections)
            online = sum(1 for s in self._states.values() if s == DeviceStatus.ONLINE)
            connecting = sum(1 for s in self._states.values() if s == DeviceStatus.CONNECTING)
            reconnecting = sum(1 for s in self._states.values() if s == DeviceStatus.RECONNECTING)
            error = sum(1 for s in self._states.values() if s == DeviceStatus.ERROR)
            offline = sum(1 for s in self._states.values() if s == DeviceStatus.OFFLINE)
            suspended = sum(1 for ctx in self._device_contexts.values() if ctx.is_suspended)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_devices': total,
            'online': online,
            'connecting': connecting,
            'reconnecting': reconnecting,
            'error': error,
            'offline': offline,
            'suspended': suspended,
            'health_score': self._calculate_health_score(online, total)
        }
    
    def _calculate_health_score(self, online: int, total: int) -> float:
        """计算健康评分"""
        if total == 0:
            return 100.0
        return (online / total) * 100
    
    def get_device_status_detail(self, device_id: str) -> Dict[str, Any]:
        """获取设备状态详情"""
        context = self._device_contexts.get(device_id)
        if not context:
            return {}
        
        return {
            'device_id': device_id,
            'status': self.get_status(device_id).value,
            'last_online_time': context.last_online_time,
            'last_offline_time': context.last_offline_time,
            'offline_reason': context.offline_reason.value if context.offline_reason else None,
            'consecutive_failures': context.consecutive_failures,
            'is_suspended': context.is_suspended,
            'suspend_until': context.suspend_until,
            'reconnect_count': context.reconnect_count,
            'total_offline_duration': context.total_offline_duration
        }
    
    def reset_device_state(self, device_id: str):
        """重置设备状态"""
        context = self._device_contexts.get(device_id)
        if context:
            context.consecutive_failures = 0
            context.is_suspended = False
            context.suspend_until = None
            context.reconnect_count = 0
    
    def enable_shutdown_detection(self, enabled: bool):
        """启用/禁用关机检测"""
        self._shutdown_detection_enabled = enabled
    
    def stop(self):
        """停止管理器"""
        self._running = False
        if hasattr(self, '_health_thread'):
            self._health_thread.join(timeout=5)


def create_enhanced_connection_manager(config: ConnectionConfig = None) -> EnhancedConnectionManager:
    """创建增强型连接管理器"""
    return EnhancedConnectionManager(config)
