"""
系统监控指标模块

提供Prometheus格式的指标采集和健康检查功能。
"""

import time
import threading
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import psutil


class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class SystemMetrics:
    """系统指标"""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_total_mb: float = 0.0
    disk_usage_percent: float = 0.0
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    thread_count: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class ApplicationMetrics:
    """应用指标"""
    request_count: int = 0
    error_count: int = 0
    response_time_ms: float = 0.0
    active_connections: int = 0
    data_points_collected: int = 0
    faults_detected: int = 0
    anomalies_detected: int = 0
    timestamp: float = field(default_factory=time.time)


class MetricsCollector:
    """指标采集器"""

    def __init__(self):
        self._lock = threading.RLock()
        self._request_times: list = []
        self._max_request_times = 1000

        self._device_metrics: Dict[str, Dict[str, Any]] = {}
        self._request_count = 0
        self._error_count = 0
        self._total_response_time = 0.0
        self._active_connections = 0
        self._data_points_collected = 0
        self._faults_detected = 0
        self._anomalies_detected = 0

        self._start_time = time.time()

    def record_request(self, response_time_ms: float, success: bool = True):
        """记录请求"""
        with self._lock:
            self._request_count += 1
            self._total_response_time += response_time_ms

            if not success:
                self._error_count += 1

            self._request_times.append(response_time_ms)
            if len(self._request_times) > self._max_request_times:
                self._request_times.pop(0)

    def record_data_collection(self, device_id: str, data_count: int):
        """记录数据采集"""
        with self._lock:
            self._data_points_collected += data_count

            if device_id not in self._device_metrics:
                self._device_metrics[device_id] = {
                    'data_count': 0,
                    'last_collection': 0,
                    'errors': 0
                }

            self._device_metrics[device_id]['data_count'] += data_count
            self._device_metrics[device_id]['last_collection'] = time.time()

    def record_fault(self):
        """记录故障检测"""
        with self._lock:
            self._faults_detected += 1

    def record_anomaly(self):
        """记录异常检测"""
        with self._lock:
            self._anomalies_detected += 1

    def connection_opened(self):
        """记录新连接"""
        with self._lock:
            self._active_connections += 1

    def connection_closed(self):
        """记录连接关闭"""
        with self._lock:
            self._active_connections = max(0, self._active_connections - 1)

    def get_system_metrics(self) -> SystemMetrics:
        """获取系统指标"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            net_io = psutil.net_io_counters()

            return SystemMetrics(
                cpu_percent=psutil.cpu_percent(interval=0.1),
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                memory_total_mb=memory.total / (1024 * 1024),
                disk_usage_percent=disk.percent,
                network_bytes_sent=net_io.bytes_sent,
                network_bytes_recv=net_io.bytes_recv,
                thread_count=threading.active_count(),
                timestamp=time.time()
            )
        except Exception as e:
            print(f"Failed to collect system metrics: {e}")
            return SystemMetrics()

    def get_application_metrics(self) -> ApplicationMetrics:
        """获取应用指标"""
        with self._lock:
            avg_response_time = (
                self._total_response_time / self._request_count
                if self._request_count > 0
                else 0.0
            )

            return ApplicationMetrics(
                request_count=self._request_count,
                error_count=self._error_count,
                response_time_ms=avg_response_time,
                active_connections=self._active_connections,
                data_points_collected=self._data_points_collected,
                faults_detected=self._faults_detected,
                anomalies_detected=self._anomalies_detected,
                timestamp=time.time()
            )

    def get_uptime(self) -> float:
        """获取运行时间（秒）"""
        return time.time() - self._start_time

    def get_device_metrics(self) -> Dict[str, Dict[str, Any]]:
        """获取设备指标"""
        with self._lock:
            return self._device_metrics.copy()

    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        return {
            'system': self.get_system_metrics().__dict__,
            'application': self.get_application_metrics().__dict__,
            'uptime_seconds': self.get_uptime(),
            'devices': self.get_device_metrics()
        }


class HealthChecker:
    """健康检查器"""

    def __init__(self):
        self._checks: Dict[str, callable] = {}
        self._last_check_results: Dict[str, Dict[str, Any]] = {}

    def register_check(self, name: str, check_func: callable):
        """
        注册健康检查。

        Args:
            name: 检查名称
            check_func: 检查函数，返回 {'status': 'healthy'/'degraded'/'unhealthy', 'message': str}
        """
        self._checks[name] = check_func

    def run_checks(self) -> Dict[str, Any]:
        """
        执行所有健康检查。

        Returns:
            健康检查结果
        """
        results = {}
        overall_status = HealthStatus.HEALTHY

        for name, check_func in self._checks.items():
            try:
                result = check_func()
                results[name] = result

                if result['status'] == 'unhealthy':
                    overall_status = HealthStatus.UNHEALTHY
                elif result['status'] == 'degraded' and overall_status == 'healthy':
                    overall_status = HealthStatus.DEGRADED

                self._last_check_results[name] = result

            except Exception as e:
                results[name] = {
                    'status': 'unhealthy',
                    'message': f'Check failed: {str(e)}',
                    'error': str(e)
                }
                overall_status = HealthStatus.UNHEALTHY

        return {
            'status': overall_status.value,
            'checks': results,
            'timestamp': time.time()
        }

    def get_last_results(self) -> Dict[str, Dict[str, Any]]:
        """获取上次检查结果"""
        return self._last_check_results


_metrics_collector: Optional[MetricsCollector] = None
_health_checker: Optional[HealthChecker] = None


def get_metrics_collector() -> MetricsCollector:
    """获取指标采集器单例"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def get_health_checker() -> HealthChecker:
    """获取健康检查器单例"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


def format_prometheus_metrics() -> str:
    """
    格式化Prometheus指标。

    Returns:
        Prometheus格式的指标字符串
    """
    collector = get_metrics_collector()
    system = collector.get_system_metrics()
    app = collector.get_application_metrics()

    lines = [
        "# HELP plc_monitor_cpu_usage_percent CPU使用率",
        "# TYPE plc_monitor_cpu_usage_percent gauge",
        f"plc_monitor_cpu_usage_percent {system.cpu_percent}",
        "",
        "# HELP plc_monitor_memory_usage_percent 内存使用率",
        "# TYPE plc_monitor_memory_usage_percent gauge",
        f"plc_monitor_memory_usage_percent {system.memory_percent}",
        "",
        "# HELP plc_monitor_memory_used_bytes 已使用内存字节数",
        "# TYPE plc_monitor_memory_used_bytes gauge",
        f"plc_monitor_memory_used_bytes {system.memory_used_mb * 1024 * 1024}",
        "",
        "# HELP plc_monitor_request_total 请求总数",
        "# TYPE plc_monitor_request_total counter",
        f"plc_monitor_request_total {app.request_count}",
        "",
        "# HELP plc_monitor_error_total 错误总数",
        "# TYPE plc_monitor_error_total counter",
        f"plc_monitor_error_total {app.error_count}",
        "",
        "# HELP plc_monitor_response_time_ms 平均响应时间（毫秒）",
        "# TYPE plc_monitor_response_time_ms gauge",
        f"plc_monitor_response_time_ms {app.response_time_ms}",
        "",
        "# HELP plc_monitor_active_connections 活动连接数",
        "# TYPE plc_monitor_active_connections gauge",
        f"plc_monitor_active_connections {app.active_connections}",
        "",
        "# HELP plc_monitor_data_points_collected 已采集数据点数",
        "# TYPE plc_monitor_data_points_collected counter",
        f"plc_monitor_data_points_collected {app.data_points_collected}",
        "",
        "# HELP plc_monitor_faults_detected 检测到的故障数",
        "# TYPE plc_monitor_faults_detected counter",
        f"plc_monitor_faults_detected {app.faults_detected}",
        "",
        "# HELP plc_monitor_anomalies_detected 检测到的异常数",
        "# TYPE plc_monitor_anomalies_detected counter",
        f"plc_monitor_anomalies_detected {app.anomalies_detected}",
        "",
        "# HELP plc_monitor_uptime_seconds 运行时间（秒）",
        "# TYPE plc_monitor_uptime_seconds counter",
        f"plc_monitor_uptime_seconds {collector.get_uptime()}",
    ]

    return "\n".join(lines)
