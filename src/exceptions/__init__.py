"""
PLC监控系统 - 统一异常处理模块

本模块提供系统化的异常类体系，用于统一管理和处理系统中的各种错误。
"""

from typing import Optional, Dict, Any


class PLCSystemException(Exception):
    """PLC监控系统基础异常类"""

    ERROR_CODE = "PLC_ERROR"
    DEFAULT_MESSAGE = "PLC系统发生未知错误"

    def __init__(
        self,
        message: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        初始化PLC系统异常。

        Args:
            message: 错误消息
            error_code: 错误码
            details: 额外的错误详情
            cause: 原始异常
        """
        self.message = message or self.DEFAULT_MESSAGE
        self.error_code = error_code or self.ERROR_CODE
        self.details = details or {}
        self.cause = cause

        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """将异常转换为字典格式，便于日志记录和API响应"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "type": self.__class__.__name__
        }

    def __str__(self) -> str:
        """返回异常的字符串表示"""
        if self.details:
            return f"[{self.error_code}] {self.message} | Details: {self.details}"
        return f"[{self.error_code}] {self.message}"


class ConnectionException(PLCSystemException):
    """PLC连接相关异常"""

    ERROR_CODE = "CONNECTION_ERROR"
    DEFAULT_MESSAGE = "PLC连接失败"

    def __init__(
        self,
        message: Optional[str] = None,
        device_id: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        初始化连接异常。

        Args:
            message: 错误消息
            device_id: 设备ID
            host: 主机地址
            port: 端口号
            details: 额外的错误详情
            cause: 原始异常
        """
        details = details or {}
        if device_id:
            details["device_id"] = device_id
        if host:
            details["host"] = host
        if port:
            details["port"] = port

        super().__init__(
            message=message,
            error_code=self.ERROR_CODE,
            details=details,
            cause=cause
        )


class DataReadException(PLCSystemException):
    """PLC数据读取异常"""

    ERROR_CODE = "DATA_READ_ERROR"
    DEFAULT_MESSAGE = "PLC数据读取失败"

    def __init__(
        self,
        message: Optional[str] = None,
        device_id: Optional[str] = None,
        db_number: Optional[int] = None,
        address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        初始化数据读取异常。

        Args:
            message: 错误消息
            device_id: 设备ID
            db_number: 数据块编号
            address: 数据地址
            details: 额外的错误详情
            cause: 原始异常
        """
        details = details or {}
        if device_id:
            details["device_id"] = device_id
        if db_number is not None:
            details["db_number"] = db_number
        if address:
            details["address"] = address

        super().__init__(
            message=message,
            error_code=self.ERROR_CODE,
            details=details,
            cause=cause
        )


class ConfigurationException(PLCSystemException):
    """配置相关异常"""

    ERROR_CODE = "CONFIG_ERROR"
    DEFAULT_MESSAGE = "系统配置错误"

    def __init__(
        self,
        message: Optional[str] = None,
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        初始化配置异常。

        Args:
            message: 错误消息
            config_key: 配置键
            config_value: 配置值
            details: 额外的错误详情
            cause: 原始异常
        """
        details = details or {}
        if config_key:
            details["config_key"] = config_key
        if config_value is not None:
            details["config_value"] = str(config_value)

        super().__init__(
            message=message,
            error_code=self.ERROR_CODE,
            details=details,
            cause=cause
        )


class DataProcessingException(PLCSystemException):
    """数据处理异常"""

    ERROR_CODE = "DATA_PROCESSING_ERROR"
    DEFAULT_MESSAGE = "数据处理失败"

    def __init__(
        self,
        message: Optional[str] = None,
        operation: Optional[str] = None,
        data_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        初始化数据处理异常。

        Args:
            message: 错误消息
            operation: 操作名称
            data_type: 数据类型
            details: 额外的错误详情
            cause: 原始异常
        """
        details = details or {}
        if operation:
            details["operation"] = operation
        if data_type:
            details["data_type"] = data_type

        super().__init__(
            message=message,
            error_code=self.ERROR_CODE,
            details=details,
            cause=cause
        )


class ValidationException(PLCSystemException):
    """数据验证异常"""

    ERROR_CODE = "VALIDATION_ERROR"
    DEFAULT_MESSAGE = "数据验证失败"

    def __init__(
        self,
        message: Optional[str] = None,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        constraint: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        初始化验证异常。

        Args:
            message: 错误消息
            field: 字段名
            value: 字段值
            constraint: 约束条件
            details: 额外的错误详情
            cause: 原始异常
        """
        details = details or {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        if constraint:
            details["constraint"] = constraint

        super().__init__(
            message=message,
            error_code=self.ERROR_CODE,
            details=details,
            cause=cause
        )


ERROR_CODES = {
    "CONNECTION_ERROR": {
        "description": "PLC连接失败",
        "suggestion": "检查网络连接和PLC地址配置"
    },
    "DATA_READ_ERROR": {
        "description": "PLC数据读取失败",
        "suggestion": "检查数据块地址和权限设置"
    },
    "CONFIG_ERROR": {
        "description": "系统配置错误",
        "suggestion": "检查配置文件和环境变量"
    },
    "DATA_PROCESSING_ERROR": {
        "description": "数据处理失败",
        "suggestion": "检查数据格式和业务逻辑"
    },
    "VALIDATION_ERROR": {
        "description": "数据验证失败",
        "suggestion": "检查输入数据的有效性和格式"
    },
    "PLC_ERROR": {
        "description": "PLC系统未知错误",
        "suggestion": "查看详细日志以获取更多信息"
    }
}


def get_error_suggestion(error_code: str) -> str:
    """
    根据错误码获取处理建议。

    Args:
        error_code: 错误码

    Returns:
        错误处理建议
    """
    return ERROR_CODES.get(error_code, {}).get(
        "suggestion",
        "请联系系统管理员"
    )
