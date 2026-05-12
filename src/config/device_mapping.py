from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class DeviceMapping:
    device_id: str
    device_type: str
    description: str = ""


DEVICE_TYPE_MAP: Dict[str, DeviceMapping] = {
    'plc_002': DeviceMapping('plc_002', 'RXB800', 'RXB800 PLC Device'),
    'plc_rxa800': DeviceMapping('plc_rxa800', 'RXA800', 'RXA800 PLC Device'),
    'plc_rxa630_1': DeviceMapping('plc_rxa630_1', 'RXA630', 'RXA630 PLC Device #1'),
    'plc_rxa630_2': DeviceMapping('plc_rxa630_2', 'RXA630', 'RXA630 PLC Device #2'),
    'plc_rxa630_3': DeviceMapping('plc_rxa630_3', 'RXA630', 'RXA630 PLC Device #3'),
    'plc_001': DeviceMapping('plc_001', 'RXA1300', 'RXA1300 PLC Device'),
}


def get_device_type(device_id: str) -> Optional[str]:
    """
    根据设备ID获取设备类型
    
    Args:
        device_id: 设备ID
        
    Returns:
        设备类型字符串，如果无法确定返回None
    """
    mapping = DEVICE_TYPE_MAP.get(device_id)
    return mapping.device_type if mapping else None


def get_device_mapping(device_id: str) -> Optional[DeviceMapping]:
    """
    获取完整的设备映射信息
    
    Args:
        device_id: 设备ID
        
    Returns:
        DeviceMapping对象，如果不存在返回None
    """
    return DEVICE_TYPE_MAP.get(device_id)


def register_device_mapping(device_id: str, device_type: str, description: str = ""):
    """
    注册新的设备映射
    
    Args:
        device_id: 设备ID
        device_type: 设备类型
        description: 设备描述
    """
    DEVICE_TYPE_MAP[device_id] = DeviceMapping(device_id, device_type, description)


def get_all_device_ids() -> List[str]:
    """
    获取所有已注册的设备ID列表
    
    Returns:
        设备ID列表
    """
    return list(DEVICE_TYPE_MAP.keys())


def get_device_ids_by_type(device_type: str) -> List[str]:
    """
    根据设备类型获取设备ID列表
    
    Args:
        device_type: 设备类型
        
    Returns:
        设备ID列表
    """
    return [
        device_id for device_id, mapping in DEVICE_TYPE_MAP.items()
        if mapping.device_type == device_type
    ]


def has_device(device_id: str) -> bool:
    """
    检查设备ID是否已注册
    
    Args:
        device_id: 设备ID
        
    Returns:
        如果已注册返回True，否则返回False
    """
    return device_id in DEVICE_TYPE_MAP
