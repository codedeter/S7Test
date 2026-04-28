"""
通用可配置的故障检测器
支持通过配置快速创建新设备的故障检测器
"""
from typing import Dict, List, Any, Optional, Set
from src.analysis.fault_detector_base import (
    BaseFaultDetector, FaultBit, FaultDetectionResult
)


class ConfigurableFaultDetector(BaseFaultDetector):
    """
    可配置的故障检测器
    通过故障位配置列表即可创建检测器
    """
    
    # 严重程度常量（与 BaseFaultDetector 保持一致）
    SEVERITY_CRITICAL = 'critical'
    SEVERITY_WARNING = 'warning'
    SEVERITY_INFO = 'info'
    
    def __init__(self, device_type: str, fault_configs: List[Dict], 
                 safety_filtered_faults: Optional[Set[str]] = None):
        """
        初始化可配置故障检测器
        
        Args:
            device_type: 设备类型标识
            fault_configs: 故障配置列表 [{'name': 'xxx', 'bit_position': 0, ...}]
            safety_filtered_faults: 需要安全条件过滤的故障名集合
        """
        self.DEVICE_TYPE = device_type
        self._fault_configs = fault_configs
        self._safety_filtered_faults = safety_filtered_faults or set()
        super().__init__()
    
    def _init_fault_bits(self):
        """根据配置初始化故障位"""
        for cfg in self._fault_configs:
            fault_bit = FaultBit(
                name=cfg['name'],
                bit_position=cfg['bit_position'],
                severity=cfg.get('severity', self.SEVERITY_WARNING),
                description=cfg.get('description', ''),
                related_variables=cfg.get('related_variables', []),
                condition_type=cfg.get('condition_type', 'status'),
                threshold=cfg.get('threshold'),
                normal_range=cfg.get('normal_range'),
                threshold_var=cfg.get('threshold_var'),
                unit=cfg.get('unit', '')
            )
            self.register_fault_bit(fault_bit)
    
    def _init_fault_relations(self):
        """根据配置初始化故障关系"""
        for cfg in self._fault_configs:
            if 'relations' in cfg:
                self._fault_to_var_relations[cfg['name']] = cfg['relations']


class RXFaultDetector(ConfigurableFaultDetector):
    """
    RX 系列设备的基础故障检测器
    提供所有 RX 设备共用的故障位定义
    """
    
    # RX 系列共用的故障位配置（油温等通用故障）
    RX_COMMON_FAULTS = [
        # ===== 油温相关故障 =====
        {
            'name': '上油箱油温过低',
            'bit_position': 0,
            'severity': 'warning',
            'description': '上油箱油温低需开启加热',
            'related_variables': ['上油箱油温'],
            'condition_type': 'analog',
            'threshold_var': '上油需加热温度',
            'unit': '°C'
        },
        {
            'name': '上油箱油需冷却',
            'bit_position': 1,
            'severity': 'warning',
            'description': '上油箱油温需要冷却，冷却循环泵开启',
            'related_variables': ['上油箱油温'],
            'condition_type': 'analog',
            'threshold_var': '油需冷却温度',
            'unit': '°C'
        },
        {
            'name': '上油箱油温过高',
            'bit_position': 2,
            'severity': 'critical',
            'description': '上油箱油温过高，主电机停止运行',
            'related_variables': ['上油箱油温'],
            'condition_type': 'analog',
            'threshold_var': '油超温温度',
            'unit': '°C'
        },
        # ===== 滤油器故障 =====
        {
            'name': '上油箱滤油受阻',
            'bit_position': 3,
            'severity': 'warning',
            'description': '上油箱滤油器受阻'
        },
        {
            'name': '上油箱油空',
            'bit_position': 4,
            'severity': 'critical',
            'description': '上油箱油位为空'
        }
    ]
    
    # RX 系列需要安全条件过滤的故障
    RX_SAFETY_FILTERED_FAULTS = {'左光幕不合格', '右光幕不合格'}
    
    def __init__(self, device_type: str, additional_faults: Optional[List[Dict]] = None,
                 override_faults: bool = False):
        """
        初始化 RX 系列故障检测器
        
        Args:
            device_type: 设备类型 (如 'RXA1300', 'RXB800', 'RXB1000')
            additional_faults: 设备特定的附加故障配置
            override_faults: 是否覆盖基础故障（True则只使用additional_faults）
        """
        if override_faults:
            faults = additional_faults or []
        else:
            faults = self.RX_COMMON_FAULTS.copy()
            if additional_faults:
                faults.extend(additional_faults)
        
        super().__init__(
            device_type=device_type,
            fault_configs=faults,
            safety_filtered_faults=self.RX_SAFETY_FILTERED_FAULTS
        )


def create_rx_detector(device_type: str, additional_faults: Optional[List[Dict]] = None,
                       override_faults: bool = False) -> RXFaultDetector:
    """
    创建 RX 系列设备的故障检测器
    
    Args:
        device_type: 设备类型
        additional_faults: 设备特定的附加故障
        override_faults: 是否覆盖基础故障
        
    Returns:
        RXFaultDetector 实例
    """
    return RXFaultDetector(device_type, additional_faults, override_faults)


def create_detector_from_config(device_type: str, config: Dict[str, Any]) -> ConfigurableFaultDetector:
    """
    通过配置字典创建故障检测器
    
    Args:
        device_type: 设备类型
        config: 配置字典 {
            'faults': [...],           # 故障配置列表
            'safety_filtered': set(),  # 需要安全过滤的故障集合
            'inherit_rx_common': bool  # 是否继承RX系列基础故障
        }
        
    Returns:
        ConfigurableFaultDetector 实例
    """
    if config.get('inherit_rx_common', False):
        # 使用RX系列检测器
        return create_rx_detector(
            device_type,
            config.get('faults'),
            config.get('override_faults', False)
        )
    else:
        # 使用通用配置检测器
        return ConfigurableFaultDetector(
            device_type=device_type,
            fault_configs=config.get('faults', []),
            safety_filtered_faults=config.get('safety_filtered', set())
        )
