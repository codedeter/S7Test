import time
import threading
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class ReasoningConfidence(Enum):
    CERTAIN = "certain"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class FaultRelationType(Enum):
    CAUSE = "cause"           # 直接原因
    TRIGGER = "trigger"       # 触发关系
    SYMPTOM = "symptom"       # 症状关系
    CONCURRENT = "concurrent" # 并发发生
    PRECONDITION = "precondition" # 前置条件


@dataclass
class FaultRelation:
    source_fault: str
    target_fault: str
    relation_type: FaultRelationType
    confidence: float = 1.0
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'source_fault': self.source_fault,
            'target_fault': self.target_fault,
            'relation_type': self.relation_type.value,
            'confidence': self.confidence,
            'description': self.description
        }


@dataclass
class InferenceResult:
    fault_name: str
    device_id: str
    root_cause: Optional[str] = None
    contributing_factors: List[str] = field(default_factory=list)
    affected_systems: List[str] = field(default_factory=list)
    confidence: ReasoningConfidence = ReasoningConfidence.UNKNOWN
    confidence_score: float = 0.0
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
            'confidence': self.confidence.value,
            'confidence_score': self.confidence_score,
            'recommended_actions': self.recommended_actions,
            'explanation': self.explanation,
            'timestamp': self.timestamp,
            'timestamp_str': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.timestamp))
        }


@dataclass
class FaultRule:
    name: str
    conditions: List[Tuple[str, Any]]
    conclusions: List[str]
    priority: int = 1
    enabled: bool = True
    description: str = ""
    
    def matches(self, active_faults: List[str]) -> bool:
        for condition, value in self.conditions:
            if value:
                if condition not in active_faults:
                    return False
            else:
                if condition in active_faults:
                    return False
        return True


class FaultReasoningEngine:
    def __init__(self):
        self._fault_relations: List[FaultRelation] = []
        self._inference_rules: List[FaultRule] = []
        self._fault_descriptions: Dict[str, Dict[str, Any]] = {}
        self._system_dependencies: Dict[str, List[str]] = {}
        self._lock = threading.Lock()
        
        self._load_default_relations()
    
    def _load_default_relations(self):
        self._fault_relations = [
            FaultRelation("电机过热", "电机过载", FaultRelationType.CAUSE, 0.9, "电机过载会导致电机过热"),
            FaultRelation("电机过载", "系统压力过高", FaultRelationType.SYMPTOM, 0.7, "系统压力过高可能是电机过载的症状"),
            FaultRelation("上油箱油温过高", "下油箱油温过高", FaultRelationType.CONCURRENT, 0.8, "上下油箱油温通常同时变化"),
            FaultRelation("上油箱油空", "上油箱滤油受阻", FaultRelationType.CAUSE, 0.85, "油位过低可能导致滤油器故障"),
            FaultRelation("通信故障", "数据采集异常", FaultRelationType.CAUSE, 0.95, "通信故障会导致数据采集异常"),
            FaultRelation("紧急停止", "安全门打开", FaultRelationType.TRIGGER, 0.9, "安全门打开会触发紧急停止"),
            FaultRelation("液压油污染", "上油箱滤油受阻", FaultRelationType.CAUSE, 0.8, "油污染会导致滤油器堵塞"),
            FaultRelation("电机过热", "滑块异常", FaultRelationType.CAUSE, 0.6, "电机问题可能影响滑块运动"),
            FaultRelation("压力过高", "滑块异常", FaultRelationType.SYMPTOM, 0.75, "滑块异常可能伴随压力过高"),
            FaultRelation("油温传感器故障", "油温过高", FaultRelationType.SYMPTOM, 0.65, "传感器故障可能误报油温过高"),
            FaultRelation("下油箱油空", "电机过热", FaultRelationType.CAUSE, 0.7, "润滑不足会导致电机过热"),
            FaultRelation("滑块异常", "安全门打开", FaultRelationType.PRECONDITION, 0.85, "滑块异常处理前需确认安全门关闭"),
            FaultRelation("系统压力过高", "压力过高", FaultRelationType.CAUSE, 0.9, "系统压力过高会触发压力过高报警"),
            FaultRelation("液压油污染", "电机过热", FaultRelationType.CAUSE, 0.5, "污染油液会增加电机负担"),
            FaultRelation("通信故障", "紧急停止", FaultRelationType.SYMPTOM, 0.4, "通信中断可能被误认为紧急停止"),
        ]
    
    def add_fault_relation(self, relation: FaultRelation):
        with self._lock:
            self._fault_relations.append(relation)
    
    def add_inference_rule(self, rule: FaultRule):
        with self._lock:
            self._inference_rules.append(rule)
            self._inference_rules.sort(key=lambda x: -x.priority)
    
    def add_fault_description(self, fault_name: str, description: str, category: str = "system", actions: List[str] = None):
        with self._lock:
            self._fault_descriptions[fault_name] = {
                'description': description,
                'category': category,
                'actions': actions or []
            }
    
    def add_system_dependency(self, component: str, depends_on: List[str]):
        with self._lock:
            self._system_dependencies[component] = depends_on
    
    def infer_root_cause(self, device_id: str, active_faults: List[str]) -> List[InferenceResult]:
        results = []
        
        if not active_faults:
            return results
        
        with self._lock:
            for fault in active_faults:
                result = self._analyze_fault(device_id, fault, active_faults)
                if result:
                    results.append(result)
        
        results.sort(key=lambda x: (-self._get_confidence_score(x.confidence), -x.confidence_score))
        return results
    
    def _analyze_fault(self, device_id: str, fault_name: str, active_faults: List[str]) -> Optional[InferenceResult]:
        root_cause = None
        contributing_factors = []
        affected_systems = []
        confidence = ReasoningConfidence.UNKNOWN
        confidence_score = 0.0
        recommended_actions = []
        explanation = []
        
        potential_causes = self._find_potential_causes(fault_name, active_faults)
        potential_effects = self._find_potential_effects(fault_name, active_faults)
        
        if potential_causes:
            root_cause = self._select_most_likely_cause(potential_causes)
            confidence_score = max(c[1] for c in potential_causes)
            contributing_factors = [c[0] for c in potential_causes if c[0] != root_cause]
            
            explanation.append(f"检测到 {fault_name}，可能的根因是 {root_cause}")
            if contributing_factors:
                explanation.append(f"相关因素: {', '.join(contributing_factors)}")
        
        if potential_effects:
            affected_systems = [e[0] for e in potential_effects]
            explanation.append(f"可能影响: {', '.join(affected_systems)}")
        
        if root_cause:
            if confidence_score >= 0.85:
                confidence = ReasoningConfidence.CERTAIN
            elif confidence_score >= 0.7:
                confidence = ReasoningConfidence.HIGH
            elif confidence_score >= 0.5:
                confidence = ReasoningConfidence.MEDIUM
            else:
                confidence = ReasoningConfidence.LOW
        else:
            confidence = ReasoningConfidence.UNKNOWN
            explanation.append(f"无法确定 {fault_name} 的直接原因，建议检查相关系统")
        
        desc = self._fault_descriptions.get(fault_name)
        if desc:
            recommended_actions.extend(desc.get('actions', []))
        
        if root_cause:
            root_desc = self._fault_descriptions.get(root_cause)
            if root_desc:
                recommended_actions.extend(root_desc.get('actions', []))
        
        recommended_actions = list(dict.fromkeys(recommended_actions))
        
        return InferenceResult(
            fault_name=fault_name,
            device_id=device_id,
            root_cause=root_cause,
            contributing_factors=contributing_factors,
            affected_systems=affected_systems,
            confidence=confidence,
            confidence_score=confidence_score,
            recommended_actions=recommended_actions,
            explanation='. '.join(explanation)
        )
    
    def _find_potential_causes(self, fault_name: str, active_faults: List[str]) -> List[Tuple[str, float]]:
        causes = []
        
        for relation in self._fault_relations:
            if relation.target_fault == fault_name and relation.relation_type in (FaultRelationType.CAUSE, FaultRelationType.TRIGGER):
                if relation.source_fault in active_faults:
                    causes.append((relation.source_fault, relation.confidence))
        
        return sorted(causes, key=lambda x: -x[1])
    
    def _find_potential_effects(self, fault_name: str, active_faults: List[str]) -> List[Tuple[str, float]]:
        effects = []
        
        for relation in self._fault_relations:
            if relation.source_fault == fault_name and relation.relation_type in (FaultRelationType.SYMPTOM, FaultRelationType.CAUSE):
                if relation.target_fault in active_faults:
                    effects.append((relation.target_fault, relation.confidence))
        
        return sorted(effects, key=lambda x: -x[1])
    
    def _select_most_likely_cause(self, causes: List[Tuple[str, float]]) -> Optional[str]:
        if not causes:
            return None
        
        max_confidence = max(c[1] for c in causes)
        top_causes = [c for c in causes if c[1] == max_confidence]
        
        if len(top_causes) == 1:
            return top_causes[0][0]
        
        for cause, _ in top_causes:
            if self._is_independent_cause(cause, [c[0] for c in top_causes if c[0] != cause]):
                return cause
        
        return top_causes[0][0]
    
    def _is_independent_cause(self, cause: str, other_causes: List[str]) -> bool:
        for other in other_causes:
            for relation in self._fault_relations:
                if relation.source_fault == other and relation.target_fault == cause:
                    return False
        return True
    
    def _get_confidence_score(self, confidence: ReasoningConfidence) -> int:
        scores = {
            ReasoningConfidence.CERTAIN: 4,
            ReasoningConfidence.HIGH: 3,
            ReasoningConfidence.MEDIUM: 2,
            ReasoningConfidence.LOW: 1,
            ReasoningConfidence.UNKNOWN: 0
        }
        return scores.get(confidence, 0)
    
    def analyze_fault_pattern(self, device_id: str, active_faults: List[str]) -> Dict[str, Any]:
        results = self.infer_root_cause(device_id, active_faults)
        
        summary = {
            'device_id': device_id,
            'total_faults': len(active_faults),
            'active_faults': active_faults,
            'inferences': [r.to_dict() for r in results],
            'has_critical': any(r.confidence in (ReasoningConfidence.CERTAIN, ReasoningConfidence.HIGH) for r in results),
            'recommendations': self._generate_recommendations(results)
        }
        
        return summary
    
    def _generate_recommendations(self, inferences: List[InferenceResult]) -> List[str]:
        recommendations = []
        seen_actions = set()
        
        for inference in sorted(inferences, key=lambda x: -self._get_confidence_score(x.confidence)):
            for action in inference.recommended_actions:
                if action not in seen_actions:
                    recommendations.append(action)
                    seen_actions.add(action)
        
        return recommendations[:10]
    
    def get_fault_graph(self, device_id: str, active_faults: List[str]) -> Dict[str, Any]:
        nodes = []
        edges = []
        node_ids = set()
        
        for fault in active_faults:
            node_ids.add(fault)
            nodes.append({
                'id': fault,
                'label': fault,
                'category': self._fault_descriptions.get(fault, {}).get('category', 'system'),
                'is_active': True
            })
        
        for relation in self._fault_relations:
            if relation.source_fault in node_ids and relation.target_fault in node_ids:
                edges.append({
                    'source': relation.source_fault,
                    'target': relation.target_fault,
                    'relation_type': relation.relation_type.value,
                    'confidence': relation.confidence,
                    'description': relation.description
                })
        
        return {
            'nodes': nodes,
            'edges': edges,
            'device_id': device_id
        }
    
    def get_fault_relations(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._fault_relations]
    
    def load_rules_from_file(self, file_path: str):
        try:
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'relations' in data:
                for rel_data in data['relations']:
                    relation = FaultRelation(
                        source_fault=rel_data['source_fault'],
                        target_fault=rel_data['target_fault'],
                        relation_type=FaultRelationType(rel_data['relation_type']),
                        confidence=rel_data.get('confidence', 1.0),
                        description=rel_data.get('description', '')
                    )
                    self.add_fault_relation(relation)
            
            if 'descriptions' in data:
                for fault_name, desc_data in data['descriptions'].items():
                    self.add_fault_description(
                        fault_name,
                        desc_data.get('description', ''),
                        desc_data.get('category', 'system'),
                        desc_data.get('actions', [])
                    )
            
            print(f"Loaded {len(data.get('relations', []))} relations and {len(data.get('descriptions', {}))} descriptions")
        except Exception as e:
            print(f"Failed to load rules from {file_path}: {e}")


def create_fault_reasoner() -> FaultReasoningEngine:
    reasoner = FaultReasoningEngine()
    
    reasoner.add_fault_description(
        "电机过热",
        "电机温度超过安全阈值，可能导致设备损坏",
        "motor",
        ["立即停机冷却", "检查散热系统", "检查负载情况", "联系维修人员"]
    )
    
    reasoner.add_fault_description(
        "电机过载",
        "电机负载超过额定值",
        "motor",
        ["降低设备负载", "检查传动系统", "检查电机参数"]
    )
    
    reasoner.add_fault_description(
        "上油箱油温过高",
        "上油箱油温超过安全阈值",
        "temperature",
        ["启动冷却系统", "检查油路", "检查油温传感器"]
    )
    
    reasoner.add_fault_description(
        "下油箱油温过高",
        "下油箱油温超过安全阈值",
        "temperature",
        ["启动冷却系统", "检查油路"]
    )
    
    reasoner.add_fault_description(
        "上油箱油空",
        "上油箱油位过低",
        "oil_level",
        ["补充润滑油", "检查油位传感器", "检查是否有泄漏"]
    )
    
    reasoner.add_fault_description(
        "下油箱油空",
        "下油箱油位过低",
        "oil_level",
        ["补充润滑油", "检查油位传感器"]
    )
    
    reasoner.add_fault_description(
        "紧急停止",
        "紧急停止按钮被触发",
        "safety",
        ["确认现场安全", "复位急停按钮", "检查急停原因"]
    )
    
    reasoner.add_fault_description(
        "安全门打开",
        "安全门未关闭",
        "safety",
        ["关闭安全门", "检查门开关"]
    )
    
    reasoner.add_fault_description(
        "压力过高",
        "系统压力超过安全阈值",
        "pressure",
        ["释放压力", "检查减压阀", "检查系统负载"]
    )
    
    reasoner.add_fault_description(
        "滑块异常",
        "滑块位置或运动异常",
        "system",
        ["检查机械结构", "校准传感器", "检查驱动系统"]
    )
    
    reasoner.add_fault_description(
        "通信故障",
        "PLC通信异常",
        "network",
        ["检查网络连接", "检查PLC状态", "重启通信模块"]
    )
    
    reasoner.add_fault_description(
        "上油箱滤油受阻",
        "上油箱滤油器堵塞",
        "system",
        ["更换滤油器", "检查油液清洁度"]
    )
    
    reasoner.add_fault_description(
        "下油箱滤油受阻",
        "下油箱滤油器堵塞",
        "system",
        ["更换滤油器"]
    )
    
    reasoner.add_fault_description(
        "液压油污染",
        "液压油污染度超标",
        "system",
        ["更换液压油", "检查过滤系统"]
    )
    
    reasoner.add_fault_description(
        "油温传感器故障",
        "油温传感器读数异常",
        "system",
        ["检查传感器接线", "校准传感器", "更换传感器"]
    )
    
    return reasoner