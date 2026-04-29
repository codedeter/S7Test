import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from src.devices.io_variable_manager import get_io_manager, IOVariableManager
from src.analysis.fault_reasoner import (
    FaultReasoningEngine,
    FaultRelation,
    FaultRelationType,
    InferenceResult,
    create_fault_reasoner
)


@dataclass
class IOFaultMapping:
    io_name: str
    device_id: str
    fault_name: str
    relation_type: FaultRelationType
    confidence: float = 1.0
    description: str = ""


@dataclass
class IOInferenceResult:
    fault_name: str
    device_id: str
    root_cause: Optional[str] = None
    contributing_factors: List[str] = field(default_factory=list)
    affected_systems: List[str] = field(default_factory=list)
    related_ios: List[str] = field(default_factory=list)
    confidence: float = 0.0
    recommended_actions: List[str] = field(default_factory=list)
    explanation: str = ""
    timestamp: float = field(default_factory=lambda: time.time())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'fault_name': self.fault_name,
            'device_id': self.device_id,
            'root_cause': self.root_cause,
            'contributing_factors': self.contributing_factors,
            'affected_systems': self.affected_systems,
            'related_ios': self.related_ios,
            'confidence': self.confidence,
            'recommended_actions': self.recommended_actions,
            'explanation': self.explanation,
            'timestamp': self.timestamp,
            'timestamp_str': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.timestamp))
        }


class IOFaultIntegrator:
    def __init__(self):
        self.io_manager: IOVariableManager = get_io_manager()
        self.fault_reasoner: FaultReasoningEngine = create_fault_reasoner()
        self._io_fault_mappings: List[IOFaultMapping] = []
        
        self._load_default_mappings()
    
    def _load_default_mappings(self):
        """加载默认的IO-故障映射关系"""
        mappings = [
            # 输入点与故障的映射
            IOFaultMapping("急停按钮", "*", "紧急停止", FaultRelationType.TRIGGER, 0.95, "急停按钮触发紧急停止"),
            IOFaultMapping("安全门状态", "*", "安全门打开", FaultRelationType.TRIGGER, 0.9, "安全门打开触发故障"),
            IOFaultMapping("光幕信号", "*", "安全门打开", FaultRelationType.SYMPTOM, 0.8, "光幕异常可能伴随安全门打开"),
            IOFaultMapping("电机过载信号", "*", "电机过载", FaultRelationType.CAUSE, 0.95, "电机过载信号指示过载"),
            IOFaultMapping("电机温度高", "*", "电机过热", FaultRelationType.CAUSE, 0.9, "温度高指示电机过热"),
            IOFaultMapping("压力传感器", "*", "压力过高", FaultRelationType.SYMPTOM, 0.85, "压力传感器异常可能指示压力过高"),
            IOFaultMapping("油温传感器", "*", "上油箱油温过高", FaultRelationType.SYMPTOM, 0.9, "油温传感器指示油温"),
            IOFaultMapping("油位传感器", "*", "上油箱油空", FaultRelationType.CAUSE, 0.95, "油位低触发油空故障"),
            IOFaultMapping("过滤器压差", "*", "上油箱滤油受阻", FaultRelationType.CAUSE, 0.85, "压差高指示过滤器堵塞"),
            IOFaultMapping("通信状态", "*", "通信故障", FaultRelationType.CAUSE, 0.95, "通信状态异常"),
            
            # 输出点与故障的映射
            IOFaultMapping("冷却泵控制", "*", "上油箱油温过高", FaultRelationType.PRECONDITION, 0.8, "冷却泵故障可能导致油温过高"),
            IOFaultMapping("润滑泵控制", "*", "润滑泵滤油器堵塞", FaultRelationType.CAUSE, 0.85, "润滑泵运行状态"),
            IOFaultMapping("电机接触器", "*", "电机过载", FaultRelationType.SYMPTOM, 0.7, "接触器状态反映电机状态"),
        ]
        
        for mapping in mappings:
            self.add_io_fault_mapping(mapping)
    
    def add_io_fault_mapping(self, mapping: IOFaultMapping):
        """添加IO-故障映射"""
        self._io_fault_mappings.append(mapping)
        
        if mapping.device_id == "*":
            self.io_manager.register_io_fault_mapping(mapping.io_name, [mapping.fault_name])
    
    def add_io_fault_mappings(self, mappings: List[IOFaultMapping]):
        """批量添加IO-故障映射"""
        for mapping in mappings:
            self.add_io_fault_mapping(mapping)
    
    def infer_with_io_context(self, device_id: str, active_faults: List[str], io_states: Dict[str, bool] = None) -> List[IOInferenceResult]:
        """结合IO状态进行故障推理"""
        results = []
        
        if not active_faults:
            return results
        
        io_manager = self.io_manager
        config = io_manager.get_device_io_config(device_id)
        
        if not config:
            return self._fallback_inference(device_id, active_faults)
        
        io_states = io_states or {}
        
        io_influenced_faults = self._find_io_influenced_faults(device_id, io_states)
        
        enhanced_faults = list(set(active_faults + io_influenced_faults))
        
        reasoner_results = self.fault_reasoner.infer_root_cause(device_id, enhanced_faults)
        
        for result in reasoner_results:
            if result.fault_name in active_faults:
                related_ios = self._find_related_ios(device_id, result.fault_name, io_states)
                
                io_result = IOInferenceResult(
                    fault_name=result.fault_name,
                    device_id=device_id,
                    root_cause=result.root_cause,
                    contributing_factors=result.contributing_factors,
                    affected_systems=result.affected_systems,
                    related_ios=related_ios,
                    confidence=result.confidence_score,
                    recommended_actions=self._enhance_actions_with_io(result, related_ios),
                    explanation=self._enhance_explanation_with_io(result, related_ios)
                )
                
                results.append(io_result)
        
        results.sort(key=lambda x: -x.confidence)
        return results
    
    def _fallback_inference(self, device_id: str, active_faults: List[str]) -> List[IOInferenceResult]:
        """没有IO配置时的回退推理"""
        reasoner_results = self.fault_reasoner.infer_root_cause(device_id, active_faults)
        
        results = []
        for result in reasoner_results:
            io_result = IOInferenceResult(
                fault_name=result.fault_name,
                device_id=device_id,
                root_cause=result.root_cause,
                contributing_factors=result.contributing_factors,
                affected_systems=result.affected_systems,
                related_ios=[],
                confidence=result.confidence_score,
                recommended_actions=result.recommended_actions,
                explanation=result.explanation
            )
            results.append(io_result)
        
        return results
    
    def _find_io_influenced_faults(self, device_id: str, io_states: Dict[str, bool]) -> List[str]:
        """根据IO状态推断可能的故障"""
        influenced_faults = []
        
        for mapping in self._io_fault_mappings:
            if mapping.device_id != "*" and mapping.device_id != device_id:
                continue
            
            if mapping.io_name in io_states:
                io_state = io_states[mapping.io_name]
                
                if io_state and mapping.relation_type in (FaultRelationType.CAUSE, FaultRelationType.TRIGGER):
                    influenced_faults.append(mapping.fault_name)
        
        return list(set(influenced_faults))
    
    def _find_related_ios(self, device_id: str, fault_name: str, io_states: Dict[str, bool]) -> List[str]:
        """找到与故障相关的IO变量"""
        related_ios = []
        
        io_names = self.io_manager.get_ios_for_fault(fault_name)
        related_ios.extend(io_names)
        
        for mapping in self._io_fault_mappings:
            if mapping.device_id != "*" and mapping.device_id != device_id:
                continue
            
            if mapping.fault_name == fault_name:
                related_ios.append(mapping.io_name)
        
        related_ios = list(set(related_ios))
        
        result = []
        for io_name in related_ios:
            if self.io_manager.is_io_available(device_id, io_name):
                state = io_states.get(io_name, "unknown")
                result.append(f"{io_name}: {state}")
        
        return result
    
    def _enhance_actions_with_io(self, result: InferenceResult, related_ios: List[str]) -> List[str]:
        """结合IO信息增强建议操作"""
        actions = list(result.recommended_actions)
        
        if related_ios:
            io_list = [io.split(':')[0] for io in related_ios]
            actions.append(f"检查相关IO点: {', '.join(io_list)}")
        
        return actions
    
    def _enhance_explanation_with_io(self, result: InferenceResult, related_ios: List[str]) -> str:
        """结合IO信息增强解释"""
        explanation = result.explanation
        
        if related_ios:
            io_info = ", ".join(related_ios)
            explanation += f"。相关IO点状态: {io_info}"
        
        return explanation
    
    def analyze_io_contribution(self, device_id: str, fault_name: str) -> Dict[str, Any]:
        """分析IO变量对故障的贡献"""
        config = self.io_manager.get_device_io_config(device_id)
        if not config:
            return {
                'device_id': device_id,
                'fault_name': fault_name,
                'has_io_config': False,
                'related_ios': []
            }
        
        related_ios = self.io_manager.get_ios_for_fault(fault_name)
        
        io_details = []
        for io_name in related_ios:
            var = self.io_manager.get_io_variable(device_id, io_name)
            if var:
                io_details.append({
                    'name': var.name,
                    'address': var.logical_address,
                    'type': var.data_type,
                    'area': var.area,
                    'description': var.description
                })
        
        return {
            'device_id': device_id,
            'fault_name': fault_name,
            'has_io_config': True,
            'related_ios': io_details,
            'io_count': len(io_details)
        }
    
    def get_io_fault_mappings(self, device_id: str = None) -> List[Dict[str, Any]]:
        """获取IO-故障映射列表"""
        result = []
        for mapping in self._io_fault_mappings:
            if device_id and mapping.device_id != "*" and mapping.device_id != device_id:
                continue
            
            result.append({
                'io_name': mapping.io_name,
                'device_id': mapping.device_id,
                'fault_name': mapping.fault_name,
                'relation_type': mapping.relation_type.value,
                'confidence': mapping.confidence,
                'description': mapping.description
            })
        
        return result
    
    def add_dynamic_mapping(self, device_id: str, io_name: str, fault_name: str, relation_type: FaultRelationType, confidence: float = 1.0):
        """动态添加IO-故障映射"""
        mapping = IOFaultMapping(
            io_name=io_name,
            device_id=device_id,
            fault_name=fault_name,
            relation_type=relation_type,
            confidence=confidence
        )
        self.add_io_fault_mapping(mapping)


def create_io_fault_integrator() -> IOFaultIntegrator:
    """创建IO故障集成器"""
    return IOFaultIntegrator()