import time
import threading
import math
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
    CAUSE = "cause"
    TRIGGER = "trigger"
    SYMPTOM = "symptom"
    CONCURRENT = "concurrent"
    PRECONDITION = "precondition"
    CORRELATION = "correlation"
    AGGREGATE = "aggregate"


class InferenceStrategy(Enum):
    DIRECT_CAUSE = "direct_cause"
    CHAIN_REASONING = "chain_reasoning"
    STATISTICAL = "statistical"
    TEMPORAL = "temporal"
    HIERARCHICAL = "hierarchical"


@dataclass
class FaultRelation:
    source_fault: str
    target_fault: str
    relation_type: FaultRelationType
    confidence: float = 1.0
    description: str = ""
    delay_ms: int = 0
    requires_all: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'source_fault': self.source_fault,
            'target_fault': self.target_fault,
            'relation_type': self.relation_type.value,
            'confidence': self.confidence,
            'description': self.description,
            'delay_ms': self.delay_ms
        }


@dataclass
class FaultOccurrence:
    fault_name: str
    device_id: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: float = 0.0
    severity: str = "warning"
    context: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_active(self) -> bool:
        return self.end_time is None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'fault_name': self.fault_name,
            'device_id': self.device_id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration_ms': self.duration_ms,
            'severity': self.severity,
            'is_active': self.is_active
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
    strategy: InferenceStrategy = InferenceStrategy.DIRECT_CAUSE
    related_evidence: List[str] = field(default_factory=list)
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
            'strategy': self.strategy.value,
            'related_evidence': self.related_evidence,
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
    confidence_modifier: float = 1.0
    
    def matches(self, active_faults: List[str]) -> bool:
        for condition, value in self.conditions:
            if value:
                if condition not in active_faults:
                    return False
            else:
                if condition in active_faults:
                    return False
        return True


class EnhancedFaultReasoner:
    def __init__(self):
        self._fault_relations: List[FaultRelation] = []
        self._inference_rules: List[FaultRule] = []
        self._fault_descriptions: Dict[str, Dict[str, Any]] = {}
        self._system_dependencies: Dict[str, List[str]] = {}
        self._fault_occurrences: List[FaultOccurrence] = []
        self._lock = threading.Lock()
        
        self._load_default_relations()
        self._load_default_descriptions()
    
    def _load_default_relations(self):
        self._fault_relations = [
            FaultRelation("过滤器压差高", "上油箱滤油受阻", FaultRelationType.CAUSE, 0.92, "压差高指示过滤器堵塞"),
            FaultRelation("急停按钮", "紧急停止", FaultRelationType.TRIGGER, 0.99, "急停按钮触发紧急停止"),
        ]
    
    def _load_default_descriptions(self):
        descriptions = {
            "电机过热": {
                'description': "电机温度超过安全阈值",
                'category': "motor",
                'actions': ["立即停机冷却", "检查散热系统", "检查负载情况", "联系维修人员"]
            },
            "电机过载": {
                'description': "电机负载超过额定值",
                'category': "motor",
                'actions': ["降低设备负载", "检查传动系统", "检查电机参数"]
            },
            "上油箱油温过高": {
                'description': "上油箱油温超过安全阈值",
                'category': "temperature",
                'actions': ["启动冷却系统", "检查油路", "检查油温传感器"]
            },
            "下油箱油温过高": {
                'description': "下油箱油温超过安全阈值",
                'category': "temperature",
                'actions': ["启动冷却系统", "检查油路"]
            },
            "上油箱油空": {
                'description': "上油箱油位过低",
                'category': "oil_level",
                'actions': ["补充润滑油", "检查油位传感器", "检查泄漏"]
            },
            "下油箱油空": {
                'description': "下油箱油位过低",
                'category': "oil_level",
                'actions': ["补充润滑油", "检查油位传感器"]
            },
            "紧急停止": {
                'description': "紧急停止按钮被触发",
                'category': "safety",
                'actions': ["确认现场安全", "复位急停按钮", "检查急停原因"]
            },
            "安全门打开": {
                'description': "安全门未关闭",
                'category': "safety",
                'actions': ["关闭安全门", "检查门开关"]
            },
            "压力过高": {
                'description': "系统压力超过安全阈值",
                'category': "pressure",
                'actions': ["释放压力", "检查减压阀", "检查系统负载"]
            },
            "滑块异常": {
                'description': "滑块位置或运动异常",
                'category': "system",
                'actions': ["检查机械结构", "校准传感器", "检查驱动系统"]
            },
            "通信故障": {
                'description': "PLC通信异常",
                'category': "network",
                'actions': ["检查网络连接", "检查PLC状态", "重启通信模块"]
            },
            "上油箱滤油受阻": {
                'description': "上油箱滤油器堵塞",
                'category': "system",
                'actions': ["更换滤油器", "检查油液清洁度"]
            },
            "液压油污染": {
                'description': "液压油污染度超标",
                'category': "system",
                'actions': ["更换液压油", "检查过滤系统"]
            },
            "油温传感器故障": {
                'description': "油温传感器读数异常",
                'category': "system",
                'actions': ["检查传感器接线", "校准传感器", "更换传感器"]
            },
            "冷却泵故障": {
                'description': "冷却泵运行异常",
                'category': "system",
                'actions': ["检查冷却泵", "检查电源", "检查管路"]
            },
            "润滑泵故障": {
                'description': "润滑泵运行异常",
                'category': "system",
                'actions': ["检查润滑泵", "检查油路", "补充润滑油"]
            },
            "电源异常": {
                'description': "电源供应异常",
                'category': "system",
                'actions': ["检查电源", "检查UPS", "检查接线"]
            },
            "过滤器压差高": {
                'description': "过滤器压差超过阈值",
                'category': "system",
                'actions': ["清洗或更换过滤器", "检查油液"]
            },
            "急停按钮": {
                'description': "急停按钮状态",
                'category': "safety",
                'actions': ["检查急停按钮", "复位按钮"]
            },
            "光幕异常": {
                'description': "安全光幕异常",
                'category': "safety",
                'actions': ["检查光幕", "清除遮挡", "检查接线"]
            },
            "系统压力过高": {
                'description': "系统压力过高",
                'category': "pressure",
                'actions': ["释放压力", "检查液压系统"]
            },
        }
        
        for name, desc in descriptions.items():
            self.add_fault_description(name, desc['description'], desc['category'], desc['actions'])
    
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
    
    def record_fault_occurrence(self, fault_name: str, device_id: str, severity: str = "warning", context: Dict[str, Any] = None):
        occurrence = FaultOccurrence(
            fault_name=fault_name,
            device_id=device_id,
            start_time=time.time(),
            severity=severity,
            context=context or {}
        )
        
        with self._lock:
            self._fault_occurrences.append(occurrence)
            
            if len(self._fault_occurrences) > 1000:
                self._fault_occurrences = self._fault_occurrences[-1000:]
    
    def resolve_fault_occurrence(self, fault_name: str, device_id: str):
        with self._lock:
            for occurrence in self._fault_occurrences:
                if occurrence.fault_name == fault_name and occurrence.device_id == device_id and occurrence.is_active:
                    occurrence.end_time = time.time()
                    occurrence.duration_ms = (occurrence.end_time - occurrence.start_time) * 1000
                    break
    
    def infer_root_cause(self, device_id: str, active_faults: List[str], fault_timestamps: Dict[str, float] = None) -> List[InferenceResult]:
        if not active_faults:
            return []
        
        results = []
        fault_timestamps = fault_timestamps or {f: time.time() for f in active_faults}
        
        for fault in active_faults:
            result = self._analyze_fault_with_multiple_strategies(device_id, fault, active_faults, fault_timestamps)
            if result:
                results.append(result)
        
        results.sort(key=lambda x: (-self._get_confidence_score(x.confidence), -x.confidence_score))
        return results
    
    def _analyze_fault_with_multiple_strategies(self, device_id: str, fault_name: str, active_faults: List[str], timestamps: Dict[str, float]) -> Optional[InferenceResult]:
        strategies = [
            self._analyze_direct_cause,
            self._analyze_chain_reasoning,
            self._analyze_statistical_correlation,
            self._analyze_temporal,
        ]
        
        best_result = None
        best_score = 0.0
        
        for strategy in strategies:
            try:
                result = strategy(device_id, fault_name, active_faults, timestamps)
                if result and result.confidence_score > best_score:
                    best_result = result
                    best_score = result.confidence_score
            except Exception as e:
                continue
        
        return best_result
    
    def _analyze_direct_cause(self, device_id: str, fault_name: str, active_faults: List[str], timestamps: Dict[str, float]) -> Optional[InferenceResult]:
        potential_causes = self._find_potential_causes(fault_name, active_faults, timestamps)
        
        if not potential_causes:
            return None
        
        root_cause, confidence = self._select_most_likely_cause(potential_causes)
        contributing_factors = [c[0] for c in potential_causes if c[0] != root_cause]
        affected_systems = self._find_potential_effects(fault_name, active_faults)
        
        return self._build_result(
            fault_name, device_id, root_cause, contributing_factors, affected_systems,
            confidence, InferenceStrategy.DIRECT_CAUSE,
            [f"直接原因: {root_cause}" if root_cause else "无直接原因"]
        )
    
    def _analyze_chain_reasoning(self, device_id: str, fault_name: str, active_faults: List[str], timestamps: Dict[str, float]) -> Optional[InferenceResult]:
        chain = self._find_cause_chain(fault_name, active_faults, timestamps, depth=3)
        
        if len(chain) < 2:
            return None
        
        root_cause = chain[-1]
        confidence = self._calculate_chain_confidence(chain)
        
        return self._build_result(
            fault_name, device_id, root_cause, chain[:-1], [],
            confidence, InferenceStrategy.CHAIN_REASONING,
            [f"因果链: {' -> '.join(reversed(chain))}"]
        )
    
    def _analyze_statistical_correlation(self, device_id: str, fault_name: str, active_faults: List[str], timestamps: Dict[str, float]) -> Optional[InferenceResult]:
        correlations = self._find_correlated_faults(fault_name, active_faults)
        
        if not correlations:
            return None
        
        contributing_factors = [c[0] for c in correlations]
        avg_confidence = sum(c[1] for c in correlations) / len(correlations)
        
        return self._build_result(
            fault_name, device_id, None, contributing_factors, [],
            avg_confidence * 0.7, InferenceStrategy.STATISTICAL,
            [f"相关故障: {', '.join(contributing_factors)}"]
        )
    
    def _analyze_temporal(self, device_id: str, fault_name: str, active_faults: List[str], timestamps: Dict[str, float]) -> Optional[InferenceResult]:
        potential_causes = self._find_temporal_causes(fault_name, active_faults, timestamps)
        
        if not potential_causes:
            return None
        
        root_cause, confidence = potential_causes[0]
        
        return self._build_result(
            fault_name, device_id, root_cause, [], [],
            confidence, InferenceStrategy.TEMPORAL,
            [f"时序分析: {root_cause} 在 {fault_name} 之前发生"]
        )
    
    def _find_potential_causes(self, fault_name: str, active_faults: List[str], timestamps: Dict[str, float]) -> List[Tuple[str, float]]:
        causes = []
        
        for relation in self._fault_relations:
            if relation.target_fault == fault_name and relation.relation_type in (FaultRelationType.CAUSE, FaultRelationType.TRIGGER):
                if relation.source_fault in active_faults:
                    adjusted_confidence = self._adjust_confidence_for_delay(relation, timestamps)
                    causes.append((relation.source_fault, adjusted_confidence))
        
        return sorted(causes, key=lambda x: -x[1])
    
    def _find_potential_effects(self, fault_name: str, active_faults: List[str]) -> List[str]:
        effects = []
        
        for relation in self._fault_relations:
            if relation.source_fault == fault_name and relation.relation_type in (FaultRelationType.SYMPTOM, FaultRelationType.CAUSE):
                if relation.target_fault in active_faults:
                    effects.append(relation.target_fault)
        
        return effects
    
    def _find_cause_chain(self, fault_name: str, active_faults: List[str], timestamps: Dict[str, float], depth: int = 3) -> List[str]:
        chain = [fault_name]
        current_fault = fault_name
        
        for _ in range(depth):
            causes = self._find_potential_causes(current_fault, active_faults, timestamps)
            if causes:
                next_cause = causes[0][0]
                if next_cause in chain:
                    break
                chain.append(next_cause)
                current_fault = next_cause
            else:
                break
        
        return chain
    
    def _find_correlated_faults(self, fault_name: str, active_faults: List[str]) -> List[Tuple[str, float]]:
        correlations = []
        
        for relation in self._fault_relations:
            if relation.relation_type == FaultRelationType.CORRELATION:
                if relation.source_fault == fault_name and relation.target_fault in active_faults:
                    correlations.append((relation.target_fault, relation.confidence))
                elif relation.target_fault == fault_name and relation.source_fault in active_faults:
                    correlations.append((relation.source_fault, relation.confidence))
        
        return sorted(correlations, key=lambda x: -x[1])
    
    def _find_temporal_causes(self, fault_name: str, active_faults: List[str], timestamps: Dict[str, float]) -> List[Tuple[str, float]]:
        causes = []
        fault_time = timestamps.get(fault_name, time.time())
        
        for relation in self._fault_relations:
            if relation.target_fault == fault_name and relation.relation_type in (FaultRelationType.CAUSE, FaultRelationType.TRIGGER):
                if relation.source_fault in active_faults:
                    source_time = timestamps.get(relation.source_fault, 0)
                    time_diff = fault_time - source_time
                    
                    min_delay = relation.delay_ms / 1000
                    max_delay = min_delay + 30
                    
                    if min_delay <= time_diff <= max_delay:
                        confidence = 0.8 + (1 - time_diff / max_delay) * 0.2
                        causes.append((relation.source_fault, min(confidence, relation.confidence)))
        
        return sorted(causes, key=lambda x: -x[1])
    
    def _adjust_confidence_for_delay(self, relation: FaultRelation, timestamps: Dict[str, float]) -> float:
        if relation.delay_ms == 0:
            return relation.confidence
        
        source_time = timestamps.get(relation.source_fault, 0)
        target_time = timestamps.get(relation.target_fault, time.time())
        time_diff = target_time - source_time
        
        expected_delay = relation.delay_ms / 1000
        tolerance = 10
        
        if abs(time_diff - expected_delay) <= tolerance:
            return relation.confidence
        elif time_diff < expected_delay - tolerance:
            return relation.confidence * 0.5
        elif time_diff > expected_delay + tolerance:
            return relation.confidence * 0.7
        
        return relation.confidence
    
    def _select_most_likely_cause(self, causes: List[Tuple[str, float]]) -> Tuple[Optional[str], float]:
        if not causes:
            return None, 0.0
        
        max_confidence = max(c[1] for c in causes)
        top_causes = [c for c in causes if c[1] == max_confidence]
        
        if len(top_causes) == 1:
            return top_causes[0]
        
        for cause, _ in top_causes:
            if self._is_independent_cause(cause, [c[0] for c in top_causes if c[0] != cause]):
                return cause, max_confidence
        
        return top_causes[0]
    
    def _is_independent_cause(self, cause: str, other_causes: List[str]) -> bool:
        for other in other_causes:
            for relation in self._fault_relations:
                if relation.source_fault == other and relation.target_fault == cause:
                    return False
        return True
    
    def _calculate_chain_confidence(self, chain: List[str]) -> float:
        if len(chain) < 2:
            return 0.0
        
        total_confidence = 1.0
        
        for i in range(len(chain) - 1):
            target = chain[i]
            source = chain[i + 1]
            
            found = False
            for relation in self._fault_relations:
                if relation.source_fault == source and relation.target_fault == target:
                    total_confidence *= relation.confidence
                    found = True
                    break
            
            if not found:
                total_confidence *= 0.5
        
        return total_confidence
    
    def _build_result(self, fault_name: str, device_id: str, root_cause: Optional[str], 
                      contributing_factors: List[str], affected_systems: List[str],
                      confidence_score: float, strategy: InferenceStrategy,
                      evidence: List[str]) -> InferenceResult:
        
        confidence = self._map_score_to_confidence(confidence_score)
        
        explanation = []
        if root_cause:
            explanation.append(f"检测到 {fault_name}，最可能的根因是 {root_cause}")
        if contributing_factors:
            explanation.append(f"相关因素: {', '.join(contributing_factors)}")
        if affected_systems:
            explanation.append(f"可能影响: {', '.join(affected_systems)}")
        if not root_cause and not contributing_factors:
            explanation.append(f"无法确定 {fault_name} 的直接原因")
        
        recommended_actions = self._get_recommended_actions(fault_name, root_cause)
        
        return InferenceResult(
            fault_name=fault_name,
            device_id=device_id,
            root_cause=root_cause,
            contributing_factors=contributing_factors,
            affected_systems=affected_systems,
            confidence=confidence,
            confidence_score=confidence_score,
            recommended_actions=recommended_actions,
            explanation='. '.join(explanation),
            strategy=strategy,
            related_evidence=evidence
        )
    
    def _map_score_to_confidence(self, score: float) -> ReasoningConfidence:
        if score >= 0.85:
            return ReasoningConfidence.CERTAIN
        elif score >= 0.7:
            return ReasoningConfidence.HIGH
        elif score >= 0.5:
            return ReasoningConfidence.MEDIUM
        elif score > 0:
            return ReasoningConfidence.LOW
        else:
            return ReasoningConfidence.UNKNOWN
    
    def _get_confidence_score(self, confidence: ReasoningConfidence) -> int:
        scores = {
            ReasoningConfidence.CERTAIN: 4,
            ReasoningConfidence.HIGH: 3,
            ReasoningConfidence.MEDIUM: 2,
            ReasoningConfidence.LOW: 1,
            ReasoningConfidence.UNKNOWN: 0
        }
        return scores.get(confidence, 0)
    
    def _get_recommended_actions(self, fault_name: str, root_cause: Optional[str]) -> List[str]:
        actions = []
        seen_actions = set()
        
        desc = self._fault_descriptions.get(fault_name)
        if desc:
            for action in desc.get('actions', []):
                if action not in seen_actions:
                    actions.append(action)
                    seen_actions.add(action)
        
        if root_cause:
            root_desc = self._fault_descriptions.get(root_cause)
            if root_desc:
                for action in root_desc.get('actions', []):
                    if action not in seen_actions:
                        actions.append(action)
                        seen_actions.add(action)
        
        return actions
    
    def analyze_fault_pattern(self, device_id: str, active_faults: List[str], fault_timestamps: Dict[str, float] = None) -> Dict[str, Any]:
        results = self.infer_root_cause(device_id, active_faults, fault_timestamps)
        
        summary = {
            'device_id': device_id,
            'total_faults': len(active_faults),
            'active_faults': active_faults,
            'inferences': [r.to_dict() for r in results],
            'has_critical': any(r.confidence in (ReasoningConfidence.CERTAIN, ReasoningConfidence.HIGH) and r.root_cause for r in results),
            'recommendations': self._generate_recommendations(results),
            'strategies_used': list(set(r.strategy.value for r in results))
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
            desc = self._fault_descriptions.get(fault, {})
            nodes.append({
                'id': fault,
                'label': fault,
                'category': desc.get('category', 'system'),
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
    
    def get_fault_descriptions(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._fault_descriptions)
    
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
                        description=rel_data.get('description', ''),
                        delay_ms=rel_data.get('delay_ms', 0)
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
    
    def get_statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'total_relations': len(self._fault_relations),
                'total_descriptions': len(self._fault_descriptions),
                'total_rules': len(self._inference_rules),
                'total_occurrences': len(self._fault_occurrences),
                'active_occurrences': sum(1 for o in self._fault_occurrences if o.is_active)
            }


def create_enhanced_fault_reasoner() -> EnhancedFaultReasoner:
    """创建增强版故障推理引擎"""
    return EnhancedFaultReasoner()