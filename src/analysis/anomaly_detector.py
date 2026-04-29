import time
import threading
import math
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


class AnomalyLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    SEVERE = "severe"


class AnomalyType(Enum):
    VALUE_OUT_OF_RANGE = "value_out_of_range"
    VALUE_SPIKE = "value_spike"
    VALUE_DROP = "value_drop"
    VALUE_STUCK = "value_stuck"
    RATE_OF_CHANGE = "rate_of_change"
    PATTERN_ANOMALY = "pattern_anomaly"
    PREDICTION_DEVIATION = "prediction_deviation"


@dataclass
class AnomalyContext:
    device_id: str
    tag_name: str
    db_number: int
    address: int
    anomaly_type: AnomalyType
    level: AnomalyLevel
    value: float
    expected_value: Optional[float] = None
    threshold: Optional[float] = None
    confidence: float = 0.0
    message: str = ""
    timestamp: float = field(default_factory=lambda: time.time())
    duration: float = 0.0
    historical_values: List[float] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'device_id': self.device_id,
            'tag_name': self.tag_name,
            'db_number': self.db_number,
            'address': self.address,
            'anomaly_type': self.anomaly_type.value,
            'level': self.level.value,
            'value': self.value,
            'expected_value': self.expected_value,
            'threshold': self.threshold,
            'confidence': self.confidence,
            'message': self.message,
            'timestamp': self.timestamp,
            'duration': self.duration,
            'timestamp_str': datetime.fromtimestamp(self.timestamp).strftime('%Y-%m-%d %H:%M:%S')
        }


class AdvancedAnomalyDetector:
    def __init__(self, window_size: int = 60, anomaly_threshold: float = 3.0):
        self._window_size = window_size
        self._anomaly_threshold = anomaly_threshold
        self._data_history: Dict[str, List[Tuple[float, float]]] = {}
        self._lock = threading.Lock()
        self._statistics_cache: Dict[str, Dict[str, float]] = {}
        self._last_cleanup_time = time.time()
    
    def _get_key(self, device_id: str, tag_name: str) -> str:
        return f"{device_id}:{tag_name}"
    
    def add_data_point(self, device_id: str, tag_name: str, value: float):
        key = self._get_key(device_id, tag_name)
        timestamp = time.time()
        
        with self._lock:
            if key not in self._data_history:
                self._data_history[key] = []
            
            self._data_history[key].append((timestamp, value))
            
            if len(self._data_history[key]) > self._window_size:
                self._data_history[key] = self._data_history[key][-self._window_size:]
            
            self._invalidate_statistics(key)
    
    def _invalidate_statistics(self, key: str):
        if key in self._statistics_cache:
            del self._statistics_cache[key]
    
    def _calculate_statistics(self, key: str) -> Optional[Dict[str, float]]:
        with self._lock:
            if key in self._statistics_cache:
                return self._statistics_cache[key]
            
            data = self._data_history.get(key)
            if not data or len(data) < 5:
                return None
            
            values = [v for _, v in data]
            n = len(values)
            
            mean = sum(values) / n
            variance = sum((v - mean) ** 2 for v in values) / n
            std_dev = math.sqrt(variance)
            
            recent_values = values[-10:] if len(values) >= 10 else values
            recent_mean = sum(recent_values) / len(recent_values)
            
            statistics = {
                'mean': mean,
                'std_dev': std_dev,
                'min': min(values),
                'max': max(values),
                'range': max(values) - min(values),
                'recent_mean': recent_mean,
                'count': n
            }
            
            self._statistics_cache[key] = statistics
            return statistics
    
    def detect_anomaly(self, device_id: str, tag_name: str, current_value: float) -> Optional[AnomalyContext]:
        key = self._get_key(device_id, tag_name)
        statistics = self._calculate_statistics(key)
        
        if not statistics:
            return None
        
        mean = statistics['mean']
        std_dev = statistics['std_dev']
        recent_mean = statistics['recent_mean']
        data_range = statistics['range']
        
        if std_dev == 0:
            if len(self._data_history.get(key, [])) > 10:
                return self._detect_stuck_value(device_id, tag_name, current_value)
            return None
        
        z_score = abs(current_value - mean) / std_dev
        
        anomaly_type = None
        anomaly_level = AnomalyLevel.INFO
        message = ""
        confidence = 0.0
        
        if z_score > self._anomaly_threshold * 2:
            anomaly_level = AnomalyLevel.SEVERE
            confidence = min(0.95 + (z_score - 6) * 0.01, 1.0)
        elif z_score > self._anomaly_threshold * 1.5:
            anomaly_level = AnomalyLevel.CRITICAL
            confidence = min(0.85 + (z_score - 4.5) * 0.03, 0.95)
        elif z_score > self._anomaly_threshold:
            anomaly_level = AnomalyLevel.WARNING
            confidence = 0.7 + (z_score - 3) * 0.1
        
        if anomaly_level != AnomalyLevel.INFO:
            if current_value > mean:
                anomaly_type = AnomalyType.VALUE_SPIKE
                message = f"数值突增: 当前值 {current_value:.2f} 超出均值 {mean:.2f} 约 {z_score:.2f} 倍标准差"
            else:
                anomaly_type = AnomalyType.VALUE_DROP
                message = f"数值突降: 当前值 {current_value:.2f} 低于均值 {mean:.2f} 约 {z_score:.2f} 倍标准差"
        
        if not anomaly_type:
            rate_change = self._detect_rate_of_change(key, current_value)
            if rate_change:
                anomaly_type = AnomalyType.RATE_OF_CHANGE
                anomaly_level = rate_change[0]
                message = rate_change[1]
                confidence = rate_change[2]
        
        if not anomaly_type:
            pattern_match = self._detect_pattern_anomaly(key, current_value)
            if pattern_match:
                anomaly_type = pattern_match[0]
                anomaly_level = pattern_match[1]
                message = pattern_match[2]
                confidence = pattern_match[3]
        
        if anomaly_type:
            history = [v for _, v in self._data_history.get(key, [])[-10:]]
            return AnomalyContext(
                device_id=device_id,
                tag_name=tag_name,
                db_number=0,
                address=0,
                anomaly_type=anomaly_type,
                level=anomaly_level,
                value=current_value,
                expected_value=mean,
                threshold=std_dev * self._anomaly_threshold,
                confidence=confidence,
                message=message,
                historical_values=history
            )
        
        return None
    
    def _detect_stuck_value(self, device_id: str, tag_name: str, current_value: float) -> Optional[AnomalyContext]:
        key = self._get_key(device_id, tag_name)
        data = self._data_history.get(key, [])
        
        if len(data) < 20:
            return None
        
        last_values = [v for _, v in data[-20:]]
        unique_values = set(last_values)
        
        if len(unique_values) == 1:
            return AnomalyContext(
                device_id=device_id,
                tag_name=tag_name,
                db_number=0,
                address=0,
                anomaly_type=AnomalyType.VALUE_STUCK,
                level=AnomalyLevel.WARNING,
                value=current_value,
                confidence=0.9,
                message=f"数值持续不变: 连续 {len(last_values)} 次读取值均为 {current_value}"
            )
        
        return None
    
    def _detect_rate_of_change(self, key: str, current_value: float) -> Optional[Tuple[AnomalyLevel, str, float]]:
        data = self._data_history.get(key, [])
        if len(data) < 5:
            return None
        
        recent_data = data[-5:]
        if len(recent_data) < 5:
            return None
        
        timestamps = [t for t, _ in recent_data]
        values = [v for _, v in recent_data]
        
        time_diff = timestamps[-1] - timestamps[0]
        if time_diff < 0.1:
            return None
        
        value_diff = current_value - values[0]
        rate = value_diff / time_diff
        
        statistics = self._calculate_statistics(key)
        if not statistics:
            return None
        
        mean_abs_change = statistics['range'] / statistics.get('count', 1)
        
        if mean_abs_change == 0:
            return None
        
        change_ratio = abs(rate) / mean_abs_change
        
        if change_ratio > 10:
            level = AnomalyLevel.CRITICAL if change_ratio > 20 else AnomalyLevel.WARNING
            message = f"变化率异常: 每秒变化 {rate:.2f} (正常约 {mean_abs_change:.4f})"
            return (level, message, min(0.8 + change_ratio * 0.005, 0.95))
        
        return None
    
    def _detect_pattern_anomaly(self, key: str, current_value: float) -> Optional[Tuple[AnomalyType, AnomalyLevel, str, float]]:
        data = self._data_history.get(key, [])
        if len(data) < 30:
            return None
        
        values = [v for _, v in data]
        
        variance = sum((v - sum(values) / len(values)) ** 2 for v in values) / len(values)
        recent_values = values[-10:]
        recent_variance = sum((v - sum(recent_values) / len(recent_values)) ** 2 for v in recent_values) / len(recent_values)
        
        if variance > 0 and recent_variance / variance > 5:
            return (
                AnomalyType.PATTERN_ANOMALY,
                AnomalyLevel.WARNING,
                f"模式变化: 近期方差增加 {recent_variance / variance:.1f} 倍",
                0.75
            )
        
        return None
    
    def get_statistics(self, device_id: str, tag_name: str) -> Optional[Dict[str, float]]:
        key = self._get_key(device_id, tag_name)
        return self._calculate_statistics(key)
    
    def cleanup(self):
        now = time.time()
        if now - self._last_cleanup_time < 60:
            return
        
        with self._lock:
            keys_to_remove = []
            for key, data in self._data_history.items():
                if not data:
                    keys_to_remove.append(key)
                else:
                    oldest_time = data[0][0]
                    if now - oldest_time > 3600:
                        data[:] = [(t, v) for t, v in data if now - t <= 3600]
            
            for key in keys_to_remove:
                del self._data_history[key]
            
            self._last_cleanup_time = now


class AnomalyAggregator:
    def __init__(self, aggregation_window: int = 60, min_confidence: float = 0.7):
        self._aggregation_window = aggregation_window
        self._min_confidence = min_confidence
        self._active_anomalies: Dict[str, AnomalyContext] = {}
        self._anomaly_history: List[AnomalyContext] = []
        self._lock = threading.Lock()
        self._max_history_size = 1000
    
    def update_anomaly(self, anomaly: AnomalyContext):
        key = f"{anomaly.device_id}:{anomaly.tag_name}:{anomaly.anomaly_type.value}"
        
        with self._lock:
            if anomaly.confidence < self._min_confidence:
                if key in self._active_anomalies:
                    del self._active_anomalies[key]
                return
            
            if key in self._active_anomalies:
                existing = self._active_anomalies[key]
                existing.value = anomaly.value
                existing.confidence = max(existing.confidence, anomaly.confidence)
                existing.duration = time.time() - existing.timestamp
                existing.message = anomaly.message
            else:
                anomaly_copy = AnomalyContext(**anomaly.__dict__)
                self._active_anomalies[key] = anomaly_copy
        
        self._record_history(anomaly)
    
    def _record_history(self, anomaly: AnomalyContext):
        with self._lock:
            self._anomaly_history.append(anomaly)
            if len(self._anomaly_history) > self._max_history_size:
                self._anomaly_history = self._anomaly_history[-self._max_history_size:]
    
    def get_active_anomalies(self, device_id: str = None, level: AnomalyLevel = None) -> List[AnomalyContext]:
        with self._lock:
            result = list(self._active_anomalies.values())
            
            if device_id:
                result = [a for a in result if a.device_id == device_id]
            
            if level:
                level_order = {AnomalyLevel.INFO: 0, AnomalyLevel.WARNING: 1, AnomalyLevel.CRITICAL: 2, AnomalyLevel.SEVERE: 3}
                target_level = level_order.get(level, 0)
                result = [a for a in result if level_order.get(a.level, 0) >= target_level]
            
            result.sort(key=lambda x: (x.level.value, -x.confidence))
            return result
    
    def get_anomaly_summary(self, device_id: str = None) -> Dict[str, Any]:
        active = self.get_active_anomalies(device_id)
        
        level_counts = {level.value: 0 for level in AnomalyLevel}
        type_counts = {at.value: 0 for at in AnomalyType}
        
        for anomaly in active:
            level_counts[anomaly.level.value] += 1
            type_counts[anomaly.anomaly_type.value] += 1
        
        return {
            'total_active': len(active),
            'level_counts': level_counts,
            'type_counts': type_counts,
            'devices_affected': len(set(a.device_id for a in active))
        }
    
    def resolve_anomaly(self, device_id: str, tag_name: str, anomaly_type: AnomalyType = None):
        with self._lock:
            keys_to_remove = []
            for key, anomaly in self._active_anomalies.items():
                if anomaly.device_id == device_id and anomaly.tag_name == tag_name:
                    if anomaly_type is None or anomaly.anomaly_type == anomaly_type:
                        keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._active_anomalies[key]
    
    def get_recent_anomalies(self, limit: int = 50) -> List[AnomalyContext]:
        with self._lock:
            return list(reversed(self._anomaly_history[-limit:]))
    
    def clear_all(self):
        with self._lock:
            self._active_anomalies.clear()
            self._anomaly_history.clear()


def create_anomaly_detector(window_size: int = 60) -> AdvancedAnomalyDetector:
    return AdvancedAnomalyDetector(window_size=window_size)


def create_anomaly_aggregator() -> AnomalyAggregator:
    return AnomalyAggregator()