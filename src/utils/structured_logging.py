import sys
import structlog
import logging
import os
from typing import Any, Dict
from datetime import datetime

def setup_structured_logging(log_level: str = None) -> structlog.BoundLogger:
    """
    配置结构化日志系统，使用structlog替代简单的print语句。

    Args:
        log_level: 日志级别，默认为环境变量LOGGING_LEVEL或INFO

    Returns:
        配置好的structlog logger实例
    """
    if log_level is None:
        log_level = os.environ.get('LOGGING_LEVEL', 'INFO').upper()

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level, logging.INFO),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level, logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger()


class StructuredLogger:
    """结构化日志包装器，提供统一的日志接口"""

    def __init__(self, name: str = None):
        """
        初始化结构化日志器。

        Args:
            name: 日志器名称，用于标识日志来源
        """
        self.logger = structlog.get_logger(name)

    def info(self, message: str, **kwargs: Any) -> None:
        """记录信息日志"""
        self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """记录警告日志"""
        self.logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """记录错误日志"""
        self.logger.error(message, **kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        """记录调试日志"""
        self.logger.debug(message, **kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        """记录异常日志（自动包含堆栈跟踪）"""
        self.logger.exception(message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """记录严重错误日志"""
        self.logger.critical(message, **kwargs)

    def log_device_connection(self, device_id: str, status: str, **kwargs: Any) -> None:
        """
        记录设备连接日志。

        Args:
            device_id: 设备ID
            status: 连接状态 (connected/disconnected/error)
            **kwargs: 其他参数
        """
        self.logger.info(
            "device_connection",
            device_id=device_id,
            status=status,
            timestamp=datetime.now().isoformat(),
            **kwargs
        )

    def log_data_collection(self, device_id: str, data_count: int, **kwargs: Any) -> None:
        """
        记录数据采集日志。

        Args:
            device_id: 设备ID
            data_count: 采集的数据点数量
            **kwargs: 其他参数
        """
        self.logger.info(
            "data_collection",
            device_id=device_id,
            data_count=data_count,
            timestamp=datetime.now().isoformat(),
            **kwargs
        )

    def log_fault_detection(self, fault_name: str, severity: str, **kwargs: Any) -> None:
        """
        记录故障检测日志。

        Args:
            fault_name: 故障名称
            severity: 严重程度
            **kwargs: 其他参数
        """
        self.logger.warning(
            "fault_detection",
            fault_name=fault_name,
            severity=severity,
            timestamp=datetime.now().isoformat(),
            **kwargs
        )

    def log_api_request(self, endpoint: str, method: str, status_code: int, **kwargs: Any) -> None:
        """
        记录API请求日志。

        Args:
            endpoint: API端点
            method: HTTP方法
            status_code: 状态码
            **kwargs: 其他参数
        """
        self.logger.info(
            "api_request",
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            timestamp=datetime.now().isoformat(),
            **kwargs
        )

    def log_performance(self, operation: str, duration_ms: float, **kwargs: Any) -> None:
        """
        记录性能指标日志。

        Args:
            operation: 操作名称
            duration_ms: 持续时间（毫秒）
            **kwargs: 其他参数
        """
        self.logger.info(
            "performance_metric",
            operation=operation,
            duration_ms=duration_ms,
            timestamp=datetime.now().isoformat(),
            **kwargs
        )


logger = StructuredLogger("plc_monitor")


def get_logger(name: str = None) -> StructuredLogger:
    """
    获取结构化日志器实例。

    Args:
        name: 日志器名称

    Returns:
        StructuredLogger实例
    """
    return StructuredLogger(name)
