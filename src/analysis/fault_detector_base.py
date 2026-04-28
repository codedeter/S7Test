"""
故障检测位基类框架
提供通用的故障检测位管理和推理能力
支持多种设备类型的故障检测规则注册和使用
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class FaultBit:
    """故障位定义"""
    name: str
    bit_position: int
    severity: str = 'warning'
    description: str = ""
    related_variables: List[str] = field(default_factory=list)
    condition_type: str = 'status'  # status, analog, network
    threshold: Optional[float] = None
    normal_range: Optional[tuple] = None
    unit: str = '状态'


@dataclass
class FaultDetectionResult:
    """故障检测结果"""
    fault_name: str
    detected: bool
    severity: str
    description: str
    related_variables: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[float] = None


class BaseFaultDetector(ABC):
    """
    故障检测器基类
    所有设备特定的故障检测器都应继承此类
    """
    
    # 设备类型标识符
    DEVICE_TYPE = "base"
    
    def __init__(self):
        self._fault_bits: Dict[str, FaultBit] = {}
        self._fault_to_var_relations: Dict[str, dict] = {}
        self._init_fault_bits()
        self._init_fault_relations()
    
    @abstractmethod
    def _init_fault_bits(self):
        """
        初始化故障位定义
        子类必须实现此方法来定义设备特定的故障位
        """
        pass
    
    @abstractmethod
    def _init_fault_relations(self):
        """
        初始化故障位与变量的关系映射
        子类必须实现此方法
        """
        pass
    
    def register_fault_bit(self, fault_bit: FaultBit):
        """
        注册故障位
        
        Args:
            fault_bit: 故障位对象
        """
        self._fault_bits[fault_bit.name] = fault_bit
    
    def get_fault_bit(self, fault_name: str) -> Optional[FaultBit]:
        """
        获取故障位定义
        
        Args:
            fault_name: 故障名称
        
        Returns:
            FaultBit对象，如果不存在返回None
        """
        return self._fault_bits.get(fault_name)
    
    def get_all_fault_bits(self) -> Dict[str, FaultBit]:
        """
        获取所有故障位定义
        
        Returns:
            故障位字典 {fault_name: FaultBit}
        """
        return dict(self._fault_bits)
    
    def get_fault_bit_count(self) -> int:
        """
        获取故障位总数
        
        Returns:
            故障位数量
        """
        return len(self._fault_bits)
    
    def detect_faults(self, device_data: Dict[str, Any]) -> List[FaultDetectionResult]:
        """
        检测所有故障位
        
        Args:
            device_data: 设备数据字典，包含故障位值和相关变量
        
        Returns:
            故障检测结果列表
        """
        results = []
        
        for fault_name, fault_bit in self._fault_bits.items():
            detected = self._check_fault_bit(fault_name, device_data)
            
            if detected:
                result = FaultDetectionResult(
                    fault_name=fault_name,
                    detected=True,
                    severity=fault_bit.severity,
                    description=fault_bit.description,
                    related_variables=self._get_related_variables(fault_name, device_data)
                )
                results.append(result)
        
        return results
    
    def _check_fault_bit(self, fault_name: str, device_data: Dict[str, Any]) -> bool:
        """
        检查单个故障位是否触发
        
        Args:
            fault_name: 故障名称
            device_data: 设备数据
        
        Returns:
            True表示故障触发，False表示正常
        """
        fault_bit = self._fault_bits.get(fault_name)
        if not fault_bit:
            return False
        
        # 首先检查故障位状态本身（值为1表示故障触发）
        # 这是最直接的故障指示，由PLC检测并设置
        fault_status = device_data.get(fault_name, 0)
        if fault_status == 1:
            # 故障位状态为1，表示故障已被PLC检测到
            # 直接返回True，不需要进一步检查
            return True
        
        # 如果故障位状态为0，检查是否有模拟量条件满足
        # 这用于在故障位未触发但模拟量值已超出范围的情况（预测性检测）
        if fault_bit.condition_type == 'analog':
            return self._check_analog_condition(fault_name, device_data)
        
        return False
    
    def _check_status_condition(self, fault_name: str, device_data: Dict[str, Any]) -> bool:
        """
        检查状态类型故障位
        
        Args:
            fault_name: 故障名称
            device_data: 设备数据
        
        Returns:
            True表示故障触发
        """
        fault_bit = self._fault_bits.get(fault_name)
        if not fault_bit:
            return False
        
        # 状态类型故障位值为1表示故障触发
        return device_data.get(fault_name, 0) == 1
    
    def _check_analog_condition(self, fault_name: str, device_data: Dict[str, Any]) -> bool:
        """
        检查模拟量类型故障位
        
        Args:
            fault_name: 故障名称
            device_data: 设备数据
        
        Returns:
            True表示故障触发
        """
        fault_bit = self._fault_bits.get(fault_name)
        if not fault_bit:
            return False
        
        # 获取相关变量的值
        related_var = fault_bit.related_variables[0] if fault_bit.related_variables else None
        if related_var and related_var in device_data:
            value = device_data[related_var]
            if fault_bit.normal_range:
                min_val, max_val = fault_bit.normal_range
                
                # 根据故障名称判断检查方向
                if '过低' in fault_name or '低于' in fault_name:
                    # 只检查下限
                    return value < min_val
                elif '过高' in fault_name or '高于' in fault_name:
                    # 只检查上限
                    return value > max_val
                else:
                    # 默认检查两边
                    return value < min_val or value > max_val
        
        return False
    
    def _check_network_condition(self, fault_name: str, device_data: Dict[str, Any]) -> bool:
        """
        检查网络类型故障位
        
        Args:
            fault_name: 故障名称
            device_data: 设备数据
        
        Returns:
            True表示故障触发（网络离线）
        """
        return device_data.get(fault_name, 0) == 1
    
    def _get_related_variables(self, fault_name: str, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取故障相关的变量值
        
        Args:
            fault_name: 故障名称
            device_data: 设备数据
        
        Returns:
            相关变量字典
        """
        fault_bit = self._fault_bits.get(fault_name)
        if not fault_bit:
            return {}
        
        related = {}
        for var_name in fault_bit.related_variables:
            if var_name in device_data:
                related[var_name] = device_data[var_name]
        
        return related
    
    def get_fault_summary(self, device_data: Dict[str, Any], var_values: Dict[str, Any] = None) -> dict:
        """
        获取故障摘要
        
        Args:
            device_data: 设备故障位数据
            var_values: 其他变量值（用于条件过滤）
        
        Returns:
            故障摘要字典
        """
        active_faults = self.get_active_faults(device_data, var_values)
        
        return {
            'total_faults': len(active_faults),
            'active_faults': active_faults,
            'has_critical': self._has_critical_fault(active_faults)
        }
    
    def get_active_faults(self, device_data: Dict[str, Any], var_values: Dict[str, Any] = None) -> List[str]:
        """
        获取活动故障列表
        
        Args:
            device_data: 设备故障位数据
            var_values: 其他变量值（用于条件过滤）
        
        Returns:
            活动故障名称列表
        """
        active_faults = []
        
        for fault_name, fault_bit in self._fault_bits.items():
            if self._check_fault_bit(fault_name, device_data):
                # 应用安全条件过滤
                if not self._should_filter_fault(fault_name, var_values):
                    active_faults.append(fault_name)
        
        return active_faults
    
    def _should_filter_fault(self, fault_name: str, var_values: Dict[str, Any]) -> bool:
        """
        判断是否应该过滤某个故障
        
        Args:
            fault_name: 故障名称
            var_values: 变量值
        
        Returns:
            True表示应该过滤（忽略此故障）
        """
        if not var_values:
            return False
        
        # 默认实现：无过滤
        return False
    
    def _has_critical_fault(self, fault_names: List[str]) -> bool:
        """
        判断是否存在严重故障
        
        Args:
            fault_names: 故障名称列表
        
        Returns:
            True表示存在严重故障
        """
        for fault_name in fault_names:
            fault_bit = self._fault_bits.get(fault_name)
            if fault_bit and fault_bit.severity == 'critical':
                return True
        return False
    
    def analyze_with_rules(self, device_data: Dict[str, Any], var_values: Dict[str, Any]) -> Dict[str, dict]:
        """
        使用规则进行故障分析
        
        Args:
            device_data: 设备故障位数据
            var_values: 其他变量值
        
        Returns:
            分析结果字典
        """
        results = {}
        
        for fault_name, fault_bit in self._fault_bits.items():
            if self._check_fault_bit(fault_name, device_data):
                # 检查是否需要过滤
                if self._should_filter_fault(fault_name, var_values):
                    continue
                
                # 更新结果
                for var_name in fault_bit.related_variables:
                    if var_name not in results:
                        results[var_name] = {
                            'normal': True,
                            'faults': [],
                            'severity': 'normal'
                        }
                    
                    results[var_name]['normal'] = False
                    results[var_name]['faults'].append({
                        'fault_name': fault_name,
                        'severity': fault_bit.severity,
                        'condition': fault_bit.condition_type
                    })
                    
                    # 更新严重程度
                    if fault_bit.severity == 'critical':
                        results[var_name]['severity'] = 'critical'
                    elif fault_bit.severity == 'warning' and results[var_name]['severity'] != 'critical':
                        results[var_name]['severity'] = 'warning'
        
        return results


class FaultDetectorRegistry:
    """
    故障检测器注册中心
    管理所有设备类型的故障检测器
    """
    
    _detectors: Dict[str, BaseFaultDetector] = {}
    
    @classmethod
    def register_detector(cls, detector: BaseFaultDetector):
        """
        注册故障检测器
        
        Args:
            detector: 故障检测器实例
        """
        cls._detectors[detector.DEVICE_TYPE] = detector
    
    @classmethod
    def get_detector(cls, device_type: str) -> Optional[BaseFaultDetector]:
        """
        获取故障检测器
        
        Args:
            device_type: 设备类型
        
        Returns:
            故障检测器实例，如果不存在返回None
        """
        return cls._detectors.get(device_type)
    
    @classmethod
    def get_all_detectors(cls) -> Dict[str, BaseFaultDetector]:
        """
        获取所有注册的故障检测器
        
        Returns:
            检测器字典
        """
        return dict(cls._detectors)
    
    @classmethod
    def has_detector(cls, device_type: str) -> bool:
        """
        检查是否存在指定类型的检测器
        
        Args:
            device_type: 设备类型
        
        Returns:
            True表示存在
        """
        return device_type in cls._detectors
    
    @classmethod
    def detect_faults(cls, device_type: str, device_data: Dict[str, Any]) -> List[FaultDetectionResult]:
        """
        使用指定类型的检测器检测故障
        
        Args:
            device_type: 设备类型
            device_data: 设备数据
        
        Returns:
            故障检测结果列表
        """
        detector = cls.get_detector(device_type)
        if detector:
            return detector.detect_faults(device_data)
        return []
    
    @classmethod
    def get_fault_summary(cls, device_type: str, device_data: Dict[str, Any], 
                          var_values: Dict[str, Any] = None) -> dict:
        """
        获取故障摘要
        
        Args:
            device_type: 设备类型
            device_data: 设备数据
            var_values: 其他变量值
        
        Returns:
            故障摘要字典
        """
        detector = cls.get_detector(device_type)
        if detector:
            return detector.get_fault_summary(device_data, var_values)
        return {'total_faults': 0, 'active_faults': [], 'has_critical': False}


def create_detector(device_type: str) -> Optional[BaseFaultDetector]:
    """
    创建指定类型的故障检测器
    
    Args:
        device_type: 设备类型
    
    Returns:
        故障检测器实例，如果不支持该类型返回None
    """
    # 动态导入设备特定的检测器
    try:
        if device_type == 'RXB800':
            from src.analysis.rxb800_fault_detector import RXB800FaultDetector
            detector = RXB800FaultDetector()
            FaultDetectorRegistry.register_detector(detector)
            return detector
        # 可以在这里添加更多设备类型
    except ImportError:
        pass
    
    return None