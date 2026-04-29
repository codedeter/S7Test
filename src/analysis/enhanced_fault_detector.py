import time
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum


class FaultSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class FaultCategory(Enum):
    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    OIL_LEVEL = "oil_level"
    MOTOR = "motor"
    NETWORK = "network"
    SAFETY = "safety"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class FaultCondition:
    bit_position: int
    threshold: Optional[float] = None
    comparison_type: str = 'equal'  # equal, not_equal, greater_than, less_than, between
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    debounce_ms: int = 0
    min_duration_ms: int = 0


@dataclass
class FaultDefinition:
    name: str
    bit_position: int
    severity: FaultSeverity = FaultSeverity.WARNING
    category: FaultCategory = FaultCategory.UNKNOWN
    description: str = ""
    related_variables: List[str] = field(default_factory=list)
    condition: Optional[FaultCondition] = None
    recovery_actions: List[str] = field(default_factory=list)
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'bit_position': self.bit_position,
            'severity': self.severity.value,
            'category': self.category.value,
            'description': self.description,
            'related_variables': self.related_variables,
            'is_active': self.is_active
        }


@dataclass
class ActiveFault:
    definition: FaultDefinition
    device_id: str
    start_time: float
    last_updated: float
    current_value: Any
    duration_ms: int = 0
    acknowledged: bool = False
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.definition.name,
            'bit_position': self.definition.bit_position,
            'severity': self.definition.severity.value,
            'category': self.definition.category.value,
            'description': self.definition.description,
            'device_id': self.device_id,
            'start_time': self.start_time,
            'start_time_str': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.start_time)),
            'duration_ms': self.duration_ms,
            'current_value': self.current_value,
            'acknowledged': self.acknowledged,
            'related_variables': self.definition.related_variables
        }


class EnhancedFaultDetector:
    def __init__(self):
        self._fault_definitions: Dict[str, FaultDefinition] = {}
        self._active_faults: Dict[str, ActiveFault] = {}
        self._device_faults: Dict[str, Dict[str, ActiveFault]] = {}
        self._bit_position_map: Dict[int, FaultDefinition] = {}
        self._lock = threading.Lock()
        self._debounce_timers: Dict[str, float] = {}
        self._fault_callbacks: List[Callable[[ActiveFault, bool], None]] = []
        self._fault_history: List[Dict[str, Any]] = []
        self._max_history_size = 500
    
    def register_fault(self, definition: FaultDefinition):
        with self._lock:
            key = f"{definition.name}"
            self._fault_definitions[key] = definition
            self._bit_position_map[definition.bit_position] = definition
    
    def register_faults(self, definitions: List[FaultDefinition]):
        for definition in definitions:
            self.register_fault(definition)
    
    def get_fault_definition(self, fault_name: str) -> Optional[FaultDefinition]:
        return self._fault_definitions.get(fault_name)
    
    def get_fault_by_bit_position(self, bit_position: int) -> Optional[FaultDefinition]:
        return self._bit_position_map.get(bit_position)
    
    def detect_faults(self, device_id: str, device_data: Dict[int, bool], var_values: Dict[str, Any] = None) -> List[ActiveFault]:
        detected_faults = []
        current_time = time.time()
        
        with self._lock:
            for bit_pos, is_set in device_data.items():
                definition = self._bit_position_map.get(bit_pos)
                
                if not definition or not definition.is_active:
                    continue
                
                fault_key = f"{device_id}:{definition.name}"
                
                if is_set:
                    if fault_key not in self._active_faults:
                        if self._check_debounce(device_id, definition.name, current_time):
                            continue
                        
                        active_fault = ActiveFault(
                            definition=definition,
                            device_id=device_id,
                            start_time=current_time,
                            last_updated=current_time,
                            current_value=var_values.get(definition.related_variables[0]) if definition.related_variables else None
                        )
                        
                        self._active_faults[fault_key] = active_fault
                        
                        if device_id not in self._device_faults:
                            self._device_faults[device_id] = {}
                        self._device_faults[device_id][definition.name] = active_fault
                        
                        self._notify_callbacks(active_fault, True)
                        self._record_history(active_fault, True)
                    
                    else:
                        existing = self._active_faults[fault_key]
                        existing.last_updated = current_time
                        existing.duration_ms = int((current_time - existing.start_time) * 1000)
                        if var_values and definition.related_variables:
                            existing.current_value = var_values.get(definition.related_variables[0])
                    
                    detected_faults.append(self._active_faults[fault_key])
                else:
                    if fault_key in self._active_faults:
                        resolved_fault = self._active_faults.pop(fault_key)
                        resolved_fault.duration_ms = int((current_time - resolved_fault.start_time) * 1000)
                        
                        if device_id in self._device_faults and definition.name in self._device_faults[device_id]:
                            del self._device_faults[device_id][definition.name]
                        
                        self._notify_callbacks(resolved_fault, False)
                        self._record_history(resolved_fault, False)
        
        return detected_faults
    
    def _check_debounce(self, device_id: str, fault_name: str, current_time: float) -> bool:
        key = f"debounce:{device_id}:{fault_name}"
        definition = self._fault_definitions.get(fault_name)
        
        if not definition or not definition.condition or definition.condition.debounce_ms == 0:
            return False
        
        last_trigger = self._debounce_timers.get(key, 0)
        if current_time - last_trigger < definition.condition.debounce_ms / 1000:
            return True
        
        self._debounce_timers[key] = current_time
        return False
    
    def _notify_callbacks(self, fault: ActiveFault, activated: bool):
        for callback in self._fault_callbacks:
            try:
                callback(fault, activated)
            except Exception as e:
                print(f"Fault callback error: {e}")
    
    def _record_history(self, fault: ActiveFault, activated: bool):
        history_entry = {
            'timestamp': time.time(),
            'device_id': fault.device_id,
            'fault_name': fault.definition.name,
            'severity': fault.definition.severity.value,
            'category': fault.definition.category.value,
            'activated': activated,
            'duration_ms': fault.duration_ms,
            'start_time': fault.start_time
        }
        
        self._fault_history.append(history_entry)
        
        if len(self._fault_history) > self._max_history_size:
            self._fault_history = self._fault_history[-self._max_history_size:]
    
    def add_fault_callback(self, callback: Callable[[ActiveFault, bool], None]):
        self._fault_callbacks.append(callback)
    
    def get_active_faults(self, device_id: str = None, severity: FaultSeverity = None) -> List[ActiveFault]:
        with self._lock:
            if device_id:
                device_faults = self._device_faults.get(device_id, {})
                faults = list(device_faults.values())
            else:
                faults = list(self._active_faults.values())
            
            if severity:
                severity_order = {FaultSeverity.INFO: 0, FaultSeverity.WARNING: 1, FaultSeverity.CRITICAL: 2, FaultSeverity.EMERGENCY: 3}
                target_level = severity_order.get(severity, 0)
                faults = [f for f in faults if severity_order.get(f.definition.severity, 0) >= target_level]
            
            faults.sort(key=lambda x: (severity_order.get(x.definition.severity, 0), x.start_time))
            return faults
    
    def get_fault_summary(self, device_id: str = None) -> Dict[str, Any]:
        active_faults = self.get_active_faults(device_id)
        
        severity_counts = {s.value: 0 for s in FaultSeverity}
        category_counts = {c.value: 0 for c in FaultCategory}
        devices_affected = set()
        
        for fault in active_faults:
            severity_counts[fault.definition.severity.value] += 1
            category_counts[fault.definition.category.value] += 1
            devices_affected.add(fault.device_id)
        
        return {
            'total_active': len(active_faults),
            'severity_counts': severity_counts,
            'category_counts': category_counts,
            'devices_affected': len(devices_affected),
            'has_critical': severity_counts[FaultSeverity.CRITICAL.value] > 0 or severity_counts[FaultSeverity.EMERGENCY.value] > 0
        }
    
    def acknowledge_fault(self, device_id: str, fault_name: str):
        key = f"{device_id}:{fault_name}"
        with self._lock:
            if key in self._active_faults:
                self._active_faults[key].acknowledged = True
    
    def add_fault_note(self, device_id: str, fault_name: str, note: str):
        key = f"{device_id}:{fault_name}"
        with self._lock:
            if key in self._active_faults:
                self._active_faults[key].notes.append({
                    'timestamp': time.time(),
                    'note': note
                })
    
    def resolve_fault(self, device_id: str, fault_name: str):
        key = f"{device_id}:{fault_name}"
        with self._lock:
            if key in self._active_faults:
                fault = self._active_faults.pop(key)
                if device_id in self._device_faults and fault_name in self._device_faults[device_id]:
                    del self._device_faults[device_id][fault_name]
                self._notify_callbacks(fault, False)
    
    def get_fault_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return list(reversed(self._fault_history[-limit:]))
    
    def get_fault_definitions(self) -> List[FaultDefinition]:
        with self._lock:
            return list(self._fault_definitions.values())
    
    def is_fault_active(self, device_id: str, fault_name: str) -> bool:
        key = f"{device_id}:{fault_name}"
        return key in self._active_faults
    
    def get_fault_duration(self, device_id: str, fault_name: str) -> Optional[int]:
        key = f"{device_id}:{fault_name}"
        with self._lock:
            if key in self._active_faults:
                return int((time.time() - self._active_faults[key].start_time) * 1000)
        return None
    
    def clear_all(self):
        with self._lock:
            self._active_faults.clear()
            self._device_faults.clear()
            self._debounce_timers.clear()


class RXSeriesFaultDefinitions:
    COMMON_FAULTS = [
        FaultDefinition(
            name="上油箱油温过低",
            bit_position=0,
            severity=FaultSeverity.WARNING,
            category=FaultCategory.TEMPERATURE,
            description="上油箱油温低于设定阈值",
            related_variables=["上油箱油温"],
            recovery_actions=["检查加热系统", "检查油温传感器"]
        ),
        FaultDefinition(
            name="上油箱油需冷却",
            bit_position=1,
            severity=FaultSeverity.WARNING,
            category=FaultCategory.TEMPERATURE,
            description="上油箱油温需要冷却",
            related_variables=["上油箱油温"]
        ),
        FaultDefinition(
            name="上油箱油温过高",
            bit_position=2,
            severity=FaultSeverity.CRITICAL,
            category=FaultCategory.TEMPERATURE,
            description="上油箱油温超过安全阈值",
            related_variables=["上油箱油温"],
            recovery_actions=["启动冷却系统", "检查油路", "降低负载"]
        ),
        FaultDefinition(
            name="上油箱滤油受阻",
            bit_position=3,
            severity=FaultSeverity.WARNING,
            category=FaultCategory.SYSTEM,
            description="上油箱滤油器堵塞或受阻",
            related_variables=["过滤器压差"],
            recovery_actions=["更换滤油器"]
        ),
        FaultDefinition(
            name="上油箱油空",
            bit_position=4,
            severity=FaultSeverity.CRITICAL,
            category=FaultCategory.OIL_LEVEL,
            description="上油箱油位过低",
            related_variables=["上油箱油位"],
            recovery_actions=["补充润滑油"]
        ),
        FaultDefinition(
            name="下油箱油温过低",
            bit_position=5,
            severity=FaultSeverity.WARNING,
            category=FaultCategory.TEMPERATURE,
            description="下油箱油温低于设定阈值",
            related_variables=["下油箱油温"]
        ),
        FaultDefinition(
            name="下油箱油需冷却",
            bit_position=6,
            severity=FaultSeverity.WARNING,
            category=FaultCategory.TEMPERATURE,
            description="下油箱油温需要冷却",
            related_variables=["下油箱油温"]
        ),
        FaultDefinition(
            name="下油箱油温过高",
            bit_position=7,
            severity=FaultSeverity.CRITICAL,
            category=FaultCategory.TEMPERATURE,
            description="下油箱油温超过安全阈值",
            related_variables=["下油箱油温"],
            recovery_actions=["启动冷却系统", "检查油路"]
        ),
        FaultDefinition(
            name="下油箱滤油受阻",
            bit_position=8,
            severity=FaultSeverity.WARNING,
            category=FaultCategory.SYSTEM,
            description="下油箱滤油器堵塞或受阻",
            related_variables=["下油箱过滤器压差"],
            recovery_actions=["更换滤油器"]
        ),
        FaultDefinition(
            name="下油箱油空",
            bit_position=9,
            severity=FaultSeverity.CRITICAL,
            category=FaultCategory.OIL_LEVEL,
            description="下油箱油位过低",
            related_variables=["下油箱油位"],
            recovery_actions=["补充润滑油"]
        ),
        FaultDefinition(
            name="电机过热",
            bit_position=10,
            severity=FaultSeverity.CRITICAL,
            category=FaultCategory.MOTOR,
            description="电机温度过高",
            related_variables=["电机温度"],
            recovery_actions=["停机冷却", "检查电机"]
        ),
        FaultDefinition(
            name="电机过载",
            bit_position=11,
            severity=FaultSeverity.CRITICAL,
            category=FaultCategory.MOTOR,
            description="电机负载超过额定值",
            related_variables=["电机电流"],
            recovery_actions=["降低负载", "检查电机"]
        ),
        FaultDefinition(
            name="通信故障",
            bit_position=12,
            severity=FaultSeverity.WARNING,
            category=FaultCategory.NETWORK,
            description="PLC通信异常",
            related_variables=["通信状态"],
            recovery_actions=["检查网络连接"]
        ),
        FaultDefinition(
            name="紧急停止",
            bit_position=13,
            severity=FaultSeverity.EMERGENCY,
            category=FaultCategory.SAFETY,
            description="紧急停止按钮被触发",
            related_variables=["急停状态"],
            recovery_actions=["检查急停按钮", "复位急停"]
        ),
        FaultDefinition(
            name="安全门打开",
            bit_position=14,
            severity=FaultSeverity.CRITICAL,
            category=FaultCategory.SAFETY,
            description="安全门未关闭",
            related_variables=["安全门状态"],
            recovery_actions=["关闭安全门"]
        ),
        FaultDefinition(
            name="压力过高",
            bit_position=15,
            severity=FaultSeverity.CRITICAL,
            category=FaultCategory.PRESSURE,
            description="系统压力超过安全阈值",
            related_variables=["系统压力"],
            recovery_actions=["释放压力", "检查减压阀"]
        ),
        FaultDefinition(
            name="压力过低",
            bit_position=16,
            severity=FaultSeverity.WARNING,
            category=FaultCategory.PRESSURE,
            description="系统压力低于正常范围",
            related_variables=["系统压力"],
            recovery_actions=["检查泄漏", "启动补压"]
        ),
        FaultDefinition(
            name="滑块异常",
            bit_position=17,
            severity=FaultSeverity.CRITICAL,
            category=FaultCategory.SYSTEM,
            description="滑块位置或运动异常",
            related_variables=["滑块位置", "滑块速度"],
            recovery_actions=["检查机械结构", "校准传感器"]
        ),
        FaultDefinition(
            name="液压油污染",
            bit_position=18,
            severity=FaultSeverity.WARNING,
            category=FaultCategory.SYSTEM,
            description="液压油污染度超标",
            related_variables=["油污染度"],
            recovery_actions=["更换液压油"]
        ),
        FaultDefinition(
            name="油温传感器故障",
            bit_position=19,
            severity=FaultSeverity.WARNING,
            category=FaultCategory.SYSTEM,
            description="油温传感器读数异常",
            related_variables=["油温传感器状态"],
            recovery_actions=["检查传感器"]
        )
    ]


def create_enhanced_fault_detector() -> EnhancedFaultDetector:
    detector = EnhancedFaultDetector()
    detector.register_faults(RXSeriesFaultDefinitions.COMMON_FAULTS)
    return detector