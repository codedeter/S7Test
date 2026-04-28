import time
import threading
from typing import Dict, List, Optional
from datetime import datetime
import json

class AnomalyTracker:
    def __init__(self, data_storage=None):
        self._active_anomalies: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self._data_storage = data_storage

    def set_data_storage(self, data_storage):
        self._data_storage = data_storage

    def update_anomaly(self, anomaly: Dict):
        with self._lock:
            key = f"{anomaly.get('device_id', 'unknown')}:{anomaly.get('tag_name', '')}:{anomaly.get('db_number', 0)}:{anomaly.get('address', 0)}"

            if anomaly.get('normal', False):
                if key in self._active_anomalies:
                    self._active_anomalies.pop(key)
                return

            if key not in self._active_anomalies:
                self._active_anomalies[key] = {
                    'device_id': anomaly.get('device_id'),
                    'tag_name': anomaly.get('tag_name'),
                    'db_number': anomaly.get('db_number'),
                    'address': anomaly.get('address'),
                    'start_time': time.time(),
                    'start_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'message': anomaly.get('message'),
                    'confidence': anomaly.get('confidence'),
                    'value': anomaly.get('value'),
                    'predicted_value': anomaly.get('predicted_value')
                }
            else:
                self._active_anomalies[key]['value'] = anomaly.get('value')
                self._active_anomalies[key]['confidence'] = anomaly.get('confidence')
                self._active_anomalies[key]['message'] = anomaly.get('message')
    
    def remove_anomaly(self, device_id: str, tag_name: str, db_number: int, address: int):
        """
        移除指定的异常
        
        Args:
            device_id: 设备ID
            tag_name: 标签名称
            db_number: DB编号
            address: 地址
        """
        with self._lock:
            key = f"{device_id}:{tag_name}:{db_number}:{address}"
            if key in self._active_anomalies:
                self._active_anomalies.pop(key)
    
    def cleanup_expired_anomalies(self, max_duration_seconds: float = 300):
        """
        清理过期的异常
        
        Args:
            max_duration_seconds: 最大持续时间，超过此时间的异常将被清理
        """
        with self._lock:
            now = time.time()
            expired_keys = []
            for key, anomaly_info in self._active_anomalies.items():
                duration = now - anomaly_info['start_time']
                if duration > max_duration_seconds:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._active_anomalies.pop(key, None)

    def get_active_anomalies(self) -> List[Dict]:
        with self._lock:
            result = []
            now = time.time()
            for key, anomaly_info in self._active_anomalies.items():
                duration = now - anomaly_info['start_time']
                result.append({
                    'device_id': anomaly_info['device_id'],
                    'tag_name': anomaly_info['tag_name'],
                    'db_number': anomaly_info['db_number'],
                    'address': anomaly_info['address'],
                    'start_time': anomaly_info['start_timestamp'],
                    'duration_seconds': duration,
                    'message': anomaly_info.get('message'),
                    'confidence': anomaly_info.get('confidence'),
                    'value': anomaly_info.get('value'),
                    'predicted_value': anomaly_info.get('predicted_value')
                })
            return result

    def get_active_anomaly_count(self, device_id: str = None) -> int:
        with self._lock:
            if device_id:
                return sum(1 for a in self._active_anomalies.values() if a.get('device_id') == device_id)
            return len(self._active_anomalies)

    def clear_all(self):
        with self._lock:
            self._active_anomalies.clear()


class FaultTracker:
    def __init__(self, data_storage=None):
        self._active_faults: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self._data_storage = data_storage

    def set_data_storage(self, data_storage):
        self._data_storage = data_storage

    def _get_fault_key(self, device_id: str, fault_name: str) -> str:
        return f"{device_id}:{fault_name}"

    def update_faults(self, device_id: str, active_faults: List[str], severity: str = 'warning'):
        with self._lock:
            current_fault_keys = set()

            for fault_name in active_faults:
                key = self._get_fault_key(device_id, fault_name)
                current_fault_keys.add(key)

                if key not in self._active_faults:
                    self._active_faults[key] = {
                        'device_id': device_id,
                        'fault_name': fault_name,
                        'start_time': time.time(),
                        'start_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'severity': severity,
                        'related_variables': {}
                    }
                else:
                    self._active_faults[key]['severity'] = severity

            resolved_faults = []
            for key, fault_info in list(self._active_faults.items()):
                if fault_info['device_id'] != device_id:
                    continue

                if key not in current_fault_keys:
                    resolved_faults.append(key)

            for key in resolved_faults:
                fault_info = self._active_faults.pop(key, None)
                if fault_info:
                    duration = time.time() - fault_info['start_time']
                    self._record_fault_resolved(fault_info, duration)

    def _record_fault_resolved(self, fault_info: dict, duration: float):
        if self._data_storage:
            end_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._data_storage.update_fault_record(
                fault_name=fault_info['fault_name'],
                device_id=fault_info['device_id'],
                end_time=end_timestamp,
                duration_seconds=duration
            )

    def get_active_faults(self) -> List[Dict]:
        with self._lock:
            result = []
            now = time.time()
            for fault_name, fault_info in self._active_faults.items():
                duration = now - fault_info['start_time']
                result.append({
                    'fault_name': fault_name,
                    'device_id': fault_info['device_id'],
                    'start_time': fault_info['start_timestamp'],
                    'duration_seconds': duration,
                    'severity': fault_info['severity'],
                    'related_variables': fault_info.get('related_variables', {})
                })
            return result

    def get_active_fault_count(self, device_id: str = None) -> int:
        with self._lock:
            if device_id:
                return sum(1 for f in self._active_faults.values() if f['device_id'] == device_id)
            return len(self._active_faults)

    def is_fault_active(self, device_id: str, fault_name: str) -> bool:
        with self._lock:
            key = self._get_fault_key(device_id, fault_name)
            return key in self._active_faults

    def get_fault_duration(self, device_id: str, fault_name: str) -> Optional[float]:
        with self._lock:
            key = self._get_fault_key(device_id, fault_name)
            if key in self._active_faults:
                return time.time() - self._active_faults[key]['start_time']
            return None

    def clear_all(self):
        with self._lock:
            self._active_faults.clear()
