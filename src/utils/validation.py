import sys
import re
import socket
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class ValidationStatus(Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class ValidationResult:
    status: ValidationStatus
    message: str
    field: Optional[str] = None
    suggestion: Optional[str] = None
    severity: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'message': self.message,
            'field': self.field,
            'suggestion': self.suggestion,
            'severity': self.severity
        }


class ConfigValidator:
    @staticmethod
    def validate_ip_address(ip: str) -> ValidationResult:
        if not ip:
            return ValidationResult(
                status=ValidationStatus.FAIL,
                message="IP地址不能为空",
                field='ip_address',
                suggestion="请提供有效的IP地址",
                severity=5
            )
        
        try:
            socket.inet_aton(ip)
            return ValidationResult(
                status=ValidationStatus.PASS,
                message=f"IP地址 {ip} 有效",
                field='ip_address'
            )
        except socket.error:
            return ValidationResult(
                status=ValidationStatus.FAIL,
                message=f"无效的IP地址: {ip}",
                field='ip_address',
                suggestion="请提供格式正确的IPv4地址",
                severity=5
            )
    
    @staticmethod
    def validate_port(port: int) -> ValidationResult:
        if port is None:
            return ValidationResult(
                status=ValidationStatus.FAIL,
                message="端口号不能为空",
                field='port',
                suggestion="请提供有效的端口号",
                severity=5
            )
        
        if not isinstance(port, int):
            return ValidationResult(
                status=ValidationStatus.FAIL,
                message=f"端口号必须是整数: {port}",
                field='port',
                suggestion="端口号应为1-65535之间的整数",
                severity=5
            )
        
        if 1 <= port <= 65535:
            return ValidationResult(
                status=ValidationStatus.PASS,
                message=f"端口 {port} 有效",
                field='port'
            )
        
        return ValidationResult(
            status=ValidationStatus.FAIL,
            message=f"端口号超出范围: {port}",
            field='port',
            suggestion="端口号应在1-65535之间",
            severity=5
        )
    
    @staticmethod
    def validate_device_id(device_id: str) -> ValidationResult:
        if not device_id:
            return ValidationResult(
                status=ValidationStatus.FAIL,
                message="设备ID不能为空",
                field='device_id',
                suggestion="请提供唯一的设备标识符",
                severity=5
            )
        
        if len(device_id) > 100:
            return ValidationResult(
                status=ValidationStatus.WARN,
                message=f"设备ID过长 ({len(device_id)}字符)",
                field='device_id',
                suggestion="建议设备ID不超过50个字符",
                severity=2
            )
        
        if re.match(r'^[a-zA-Z0-9_-]+$', device_id):
            return ValidationResult(
                status=ValidationStatus.PASS,
                message=f"设备ID {device_id} 有效",
                field='device_id'
            )
        
        return ValidationResult(
            status=ValidationStatus.WARN,
            message=f"设备ID包含特殊字符: {device_id}",
            field='device_id',
            suggestion="建议只使用字母、数字、下划线和连字符",
            severity=3
        )
    
    @staticmethod
    def validate_db_number(db_number: int) -> ValidationResult:
        if db_number is None:
            return ValidationResult(
                status=ValidationStatus.FAIL,
                message="数据块编号不能为空",
                field='db_number',
                suggestion="请提供有效的数据块编号",
                severity=4
            )
        
        if not isinstance(db_number, int):
            return ValidationResult(
                status=ValidationStatus.FAIL,
                message=f"数据块编号必须是整数: {db_number}",
                field='db_number',
                suggestion="数据块编号应为整数",
                severity=4
            )
        
        if 0 <= db_number <= 65535:
            return ValidationResult(
                status=ValidationStatus.PASS,
                message=f"数据块编号 {db_number} 有效",
                field='db_number'
            )
        
        return ValidationResult(
            status=ValidationStatus.FAIL,
            message=f"数据块编号超出范围: {db_number}",
            field='db_number',
            suggestion="数据块编号应在0-65535之间",
            severity=4
        )
    
    @staticmethod
    def validate_address(address: int) -> ValidationResult:
        if address is None:
            return ValidationResult(
                status=ValidationStatus.FAIL,
                message="地址不能为空",
                field='address',
                suggestion="请提供有效的内存地址",
                severity=4
            )
        
        if not isinstance(address, int):
            return ValidationResult(
                status=ValidationStatus.FAIL,
                message=f"地址必须是整数: {address}",
                field='address',
                suggestion="地址应为非负整数",
                severity=4
            )
        
        if address >= 0:
            return ValidationResult(
                status=ValidationStatus.PASS,
                message=f"地址 {address} 有效",
                field='address'
            )
        
        return ValidationResult(
            status=ValidationStatus.FAIL,
            message=f"地址不能为负数: {address}",
            field='address',
            suggestion="地址应为非负整数",
            severity=4
        )
    
    @staticmethod
    def validate_data_type(data_type: str) -> ValidationResult:
        valid_types = {'BOOL', 'INT', 'DINT', 'REAL', 'BYTE', 'WORD', 'DWORD', 'STRING'}
        
        if not data_type:
            return ValidationResult(
                status=ValidationStatus.FAIL,
                message="数据类型不能为空",
                field='data_type',
                suggestion="请提供有效的数据类型",
                severity=4
            )
        
        if data_type.upper() in valid_types:
            return ValidationResult(
                status=ValidationStatus.PASS,
                message=f"数据类型 {data_type} 有效",
                field='data_type'
            )
        
        return ValidationResult(
            status=ValidationStatus.FAIL,
            message=f"无效的数据类型: {data_type}",
            field='data_type',
            suggestion=f"有效类型: {', '.join(sorted(valid_types))}",
            severity=4
        )
    
    @staticmethod
    def validate_timeout(timeout: float, min_value: float = 0.1, max_value: float = 60.0) -> ValidationResult:
        if timeout is None:
            return ValidationResult(
                status=ValidationStatus.WARN,
                message="超时时间未设置，使用默认值",
                field='timeout',
                suggestion="建议设置合理的超时时间",
                severity=2
            )
        
        if not isinstance(timeout, (int, float)):
            return ValidationResult(
                status=ValidationStatus.FAIL,
                message=f"超时时间必须是数值: {timeout}",
                field='timeout',
                suggestion="超时时间应为秒数",
                severity=3
            )
        
        if timeout <= 0:
            return ValidationResult(
                status=ValidationStatus.FAIL,
                message=f"超时时间必须为正数: {timeout}",
                field='timeout',
                suggestion="超时时间应大于0",
                severity=4
            )
        
        if timeout < min_value:
            return ValidationResult(
                status=ValidationStatus.WARN,
                message=f"超时时间过短: {timeout}s",
                field='timeout',
                suggestion=f"建议至少 {min_value}s",
                severity=2
            )
        
        if timeout > max_value:
            return ValidationResult(
                status=ValidationStatus.WARN,
                message=f"超时时间过长: {timeout}s",
                field='timeout',
                suggestion=f"建议不超过 {max_value}s",
                severity=2
            )
        
        return ValidationResult(
            status=ValidationStatus.PASS,
            message=f"超时时间 {timeout}s 有效",
            field='timeout'
        )
    
    @staticmethod
    def validate_config_dict(config: Dict[str, Any], required_fields: List[str]) -> List[ValidationResult]:
        results = []
        
        for field_name in required_fields:
            if field_name not in config:
                results.append(ValidationResult(
                    status=ValidationStatus.FAIL,
                    message=f"缺少必填字段: {field_name}",
                    field=field_name,
                    suggestion=f"请添加 {field_name} 字段",
                    severity=5
                ))
        
        return results


class RuntimeChecker:
    @staticmethod
    def check_network_connectivity(host: str, port: int = 80, timeout: float = 2.0) -> Tuple[bool, str]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                if result == 0:
                    return True, f"连接成功到 {host}:{port}"
                return False, f"连接失败到 {host}:{port} (错误码: {result})"
        except Exception as e:
            return False, f"连接检查失败: {str(e)}"
    
    @staticmethod
    def check_port_available(port: int) -> Tuple[bool, str]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                result = sock.bind(('0.0.0.0', port))
                return True, f"端口 {port} 可用"
        except OSError as e:
            return False, f"端口 {port} 已被占用: {str(e)}"
        except Exception as e:
            return False, f"端口检查失败: {str(e)}"
    
    @staticmethod
    def check_disk_space(path: str = '.', min_free_mb: int = 100) -> Tuple[bool, str]:
        try:
            import shutil
            total, used, free = shutil.disk_usage(path)
            free_mb = free // (1024 * 1024)
            
            if free_mb >= min_free_mb:
                return True, f"磁盘空间充足: {free_mb}MB 可用"
            return False, f"磁盘空间不足: 仅 {free_mb}MB 可用 (需要至少 {min_free_mb}MB)"
        except Exception as e:
            return False, f"磁盘空间检查失败: {str(e)}"
    
    @staticmethod
    def check_python_version(min_version: Tuple[int, int] = (3, 8)) -> Tuple[bool, str]:
        current_version = sys.version_info[:2]
        if current_version >= min_version:
            return True, f"Python版本符合要求: {current_version[0]}.{current_version[1]}"
        return False, f"Python版本过低: 当前 {current_version[0]}.{current_version[1]}, 需要至少 {min_version[0]}.{min_version[1]}"
    
    @staticmethod
    def check_module_available(module_name: str) -> Tuple[bool, str]:
        try:
            __import__(module_name)
            return True, f"模块 {module_name} 已安装"
        except ImportError:
            return False, f"模块 {module_name} 未安装"


def get_validator() -> ConfigValidator:
    return ConfigValidator()


def get_runtime_checker() -> RuntimeChecker:
    return RuntimeChecker()