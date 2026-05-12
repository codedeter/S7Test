import threading
import time
from collections import deque
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

from src.data.cache_manager import get_cache_manager
from src.config.device_mapping import get_device_type, get_device_mapping


@dataclass
class PipelineData:
    device_id: str
    data: List[Dict[str, Any]]
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None


class PipelineStage:
    def __init__(self, name: str):
        self.name = name
        self._next_stage: Optional['PipelineStage'] = None
    
    def set_next(self, stage: 'PipelineStage') -> 'PipelineStage':
        self._next_stage = stage
        return self
    
    def process(self, data: PipelineData) -> Optional[PipelineData]:
        result = self._process(data)
        if result is not None and self._next_stage is not None:
            return self._next_stage.process(result)
        return result
    
    def _process(self, data: PipelineData) -> Optional[PipelineData]:
        raise NotImplementedError


class DataBufferStage(PipelineStage):
    def __init__(self, max_size: int = 50):
        super().__init__('buffer')
        self._buffer = deque(maxlen=max_size)
        self._lock = threading.Lock()
    
    def _process(self, data: PipelineData) -> Optional[PipelineData]:
        with self._lock:
            self._buffer.append({
                'timestamp': data.timestamp,
                'device_id': data.device_id,
                'data': data.data,
                'metadata': data.metadata
            })
        return data
    
    def get_latest(self, device_id: Optional[str] = None, count: int = 1) -> List[Dict]:
        with self._lock:
            if device_id:
                filtered = [item for item in reversed(self._buffer) 
                           if item['device_id'] == device_id]
                return filtered[:count]
            else:
                return list(reversed(self._buffer))[:count]


class AnomalyDetectionStage(PipelineStage):
    def __init__(self, data_analyzer):
        super().__init__('anomaly_detection')
        self._data_analyzer = data_analyzer
        self._anomalies: List[Dict] = []
        self._lock = threading.Lock()
    
    def _process(self, data: PipelineData) -> Optional[PipelineData]:
        anomalies = []
        for item in data.data:
            db_number = item.get('db_number')
            address = item.get('address')
            value = item.get('value')
            
            self._data_analyzer.add_data_point(db_number, address, value)
            analysis_result = self._data_analyzer.analyze_data(db_number, address, value)
            
            if not analysis_result['normal']:
                predicted_value = self._data_analyzer.predict_value(db_number, address)
                anomaly = {
                    'timestamp': data.timestamp,
                    'device_id': data.device_id,
                    'db_number': db_number,
                    'address': address,
                    'tag_name': item.get('tag_name'),
                    'value': value,
                    'predicted_value': predicted_value,
                    'confidence': analysis_result['confidence'],
                    'message': analysis_result['message']
                }
                anomalies.append(anomaly)
        
        if anomalies:
            with self._lock:
                self._anomalies.extend(anomalies)
                if len(self._anomalies) > 100:
                    self._anomalies = self._anomalies[-100:]
        
        return data
    
    def get_pending_anomalies(self) -> List[Dict]:
        with self._lock:
            anomalies = list(self._anomalies)
            self._anomalies.clear()
            return anomalies


class RulesEngineStage(PipelineStage):
    def __init__(self, drools_engine):
        super().__init__('rules_engine')
        self._drools_engine = drools_engine
        self._results: List[Dict] = []
        self._lock = threading.Lock()
    
    def _process(self, data: PipelineData) -> Optional[PipelineData]:
        facts = {}
        has_changed = False
        
        for item in data.data:
            tag_name = item.get('tag_name')
            if tag_name:
                key = f"{data.device_id}:{tag_name}"
                facts[key] = item['value']
                has_changed = True
        
        if has_changed:
            self._drools_engine.clear_facts()
            self._drools_engine.insert_facts(facts)
            results = self._drools_engine.fire_all_rules()
            
            if results:
                with self._lock:
                    for result in results:
                        result['timestamp'] = data.timestamp
                        result['device_id'] = data.device_id
                        self._results.append(result)
                    if len(self._results) > 100:
                        self._results = self._results[-100:]
        
        return data
    
    def get_pending_results(self) -> List[Dict]:
        with self._lock:
            results = list(self._results)
            self._results.clear()
            return results


class FaultDetectionStage(PipelineStage):
    def __init__(self, fault_detector_registry, fault_tracker, fault_reasoner):
        super().__init__('fault_detection')
        self._fault_detector_registry = fault_detector_registry
        self._fault_tracker = fault_tracker
        self._fault_reasoner = fault_reasoner
        self._fault_status: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def _process(self, data: PipelineData) -> Optional[PipelineData]:
        device_type = self._get_device_type(data.device_id)
        if not device_type:
            return data
        
        fault_data, var_values = self._extract_fault_data(data.data)
        
        fault_result = self._fault_detector_registry.get_fault_summary(
            device_type, fault_data, var_values
        )
        
        if self._fault_detector_registry.has_detector(device_type):
            detector = self._fault_detector_registry.get_detector(device_type)
            analysis = detector.analyze_with_rules(fault_data, var_values)
            fault_result['analysis'] = analysis
        
        self._fault_tracker.update_faults(
            data.device_id,
            fault_result.get('active_faults', []),
            'warning' if not fault_result.get('has_critical') else 'critical'
        )
        
        active_faults = self._fault_tracker.get_active_faults()
        active_fault_names = [f['fault_name'] for f in active_faults]
        
        inferences = []
        if active_fault_names:
            try:
                inferences = self._fault_reasoner.infer_root_cause(data.device_id, active_fault_names)
            except Exception:
                pass
        
        with self._lock:
            self._fault_status[data.device_id] = {
                'device_id': data.device_id,
                'timestamp': data.timestamp,
                'total_faults': len(active_faults),
                'has_critical': fault_result.get('has_critical'),
                'active_faults': active_faults,
                'fault_analysis': fault_result.get('analysis', {}),
                'severity': 'critical' if fault_result.get('has_critical') else 'warning',
                'device_type': device_type,
                'inferences': [inf.to_dict() for inf in inferences] if inferences else []
            }
        
        return data
    
    def _get_device_type(self, device_id: str) -> Optional[str]:
        return get_device_type(device_id)
    
    def _extract_fault_data(self, data: List[Dict]) -> tuple:
        fault_data = {}
        var_values = {}
        
        for item in data:
            db_number = item.get('db_number')
            tag_name = item.get('tag_name')
            if db_number == 51 and tag_name:
                fault_data[tag_name] = item['value']
            elif db_number in (1, 10) and tag_name:
                var_values[tag_name] = item['value']
        
        return fault_data, var_values
    
    def get_fault_status(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._fault_status)


class DataPipeline:
    def __init__(self):
        self._stages: List[PipelineStage] = []
        self._first_stage: Optional[PipelineStage] = None
        self._cache_manager = get_cache_manager()
    
    def add_stage(self, stage: PipelineStage) -> 'DataPipeline':
        self._stages.append(stage)
        if self._first_stage is None:
            self._first_stage = stage
        else:
            last_stage = self._stages[-2]
            last_stage.set_next(stage)
        return self
    
    def process(self, device_id: str, data: List[Dict[str, Any]], 
                metadata: Optional[Dict[str, Any]] = None) -> Optional[PipelineData]:
        pipeline_data = PipelineData(
            device_id=device_id,
            data=data,
            timestamp=time.time(),
            metadata=metadata
        )
        
        if self._first_stage:
            return self._first_stage.process(pipeline_data)
        return pipeline_data
    
    def get_stage(self, name: str) -> Optional[PipelineStage]:
        for stage in self._stages:
            if stage.name == name:
                return stage
        return None
