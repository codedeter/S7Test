import time
import threading
from collections import deque
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from src.data.data_storage import DataStorage
from src.analysis.data_analyzer import DataAnalyzer
from src.analysis.drools_lite_engine import create_drools_lite_engine
from src.analysis.slider_down_detector import create_slider_detector
from src.analysis.rxb800_rules import RXB800FaultRules
from src.analysis.fault_tracker import FaultTracker, AnomalyTracker
from src.analysis.fault_detector_base import FaultDetectorRegistry, create_detector
from src.devices.device_manager import CollectedData


@dataclass
class ProcessingResult:
    device_data_map: Dict[str, Any]
    anomalies: List[Dict[str, Any]]
    drools_results: List[Dict[str, Any]]
    slider_results: List[Dict[str, Any]]
    fault_status: Dict[str, Any]


class DataProcessor:
    def __init__(self):
        self.data_storage = DataStorage()
        self.data_analyzer = DataAnalyzer()
        self.drools_engine = create_drools_lite_engine()
        self.fault_tracker = FaultTracker(self.data_storage)
        self.anomaly_tracker = AnomalyTracker()
        self.slider_detector = create_slider_detector()
        
        self._init_fault_detectors()
        
        self.data_buffer = deque(maxlen=50)
        self.buffer_lock = threading.Lock()
        self.latest_anomalies = []
        self.latest_drools_results = []
        self.latest_slider_results = []
        self.latest_fault_status = {}
        
        self.anomalies_lock = threading.Lock()
        self.drools_lock = threading.Lock()
        self.slider_lock = threading.Lock()
        self.fault_lock = threading.Lock()
    
    def _init_fault_detectors(self):
        """
        初始化故障检测器
        注册所有支持的设备类型的故障检测器
        """
        create_detector('RXB800')
        print("Fault detectors initialized")
    
    def detect_device_faults(self, device_id: str, device_type: str, 
                              device_data: Dict[str, Any], var_values: Dict[str, Any] = None) -> dict:
        """
        使用通用故障检测器框架检测设备故障
        
        Args:
            device_id: 设备ID
            device_type: 设备类型
            device_data: 设备数据（故障位数据）
            var_values: 其他变量值（用于条件过滤）
        
        Returns:
            故障检测结果
        """
        summary = FaultDetectorRegistry.get_fault_summary(device_type, device_data, var_values)
        analysis = {}
        
        # 如果注册了该类型的检测器，进行详细分析
        if FaultDetectorRegistry.has_detector(device_type):
            detector = FaultDetectorRegistry.get_detector(device_type)
            analysis = detector.analyze_with_rules(device_data, var_values)
        
        return {
            'summary': summary,
            'analysis': analysis,
            'active_faults': summary.get('active_faults', []),
            'has_critical': summary.get('has_critical', False),
            'total_faults': summary.get('total_faults', 0)
        }

    def process_device_data(self, all_device_data: List[CollectedData]) -> ProcessingResult:
        device_data_map = {}
        new_anomalies = []
        new_drools_results = []
        new_slider_results = []
        new_fault_status = {}

        for device_data in all_device_data:
            device_id = device_data.device_id
            data = device_data.data

            self.data_storage.batch_insert_plc_data(data, device_id)

            with self.buffer_lock:
                self.data_buffer.append({
                    'timestamp': time.time() * 1000,
                    'device_id': device_id,
                    'device_name': device_data.device_name,
                    'data': data
                })

            facts = {}

            for item in data:
                tag_name = item.get('tag_name')
                if tag_name:
                    key = f"{device_id}:{tag_name}"
                    facts[key] = item['value']

                    db_number = item['db_number']
                    address = item['address']
                    value = item['value']
                    self.data_analyzer.add_data_point(db_number, address, value)

                    analysis_result = self.data_analyzer.analyze_data(db_number, address, value)
                    if not analysis_result['normal']:
                        predicted_value = self.data_analyzer.predict_value(db_number, address)
                        anomaly = {
                            'timestamp': time.time(),
                            'device_id': device_id,
                            'db_number': db_number,
                            'address': address,
                            'tag_name': tag_name,
                            'value': value,
                            'predicted_value': predicted_value,
                            'confidence': analysis_result['confidence'],
                            'message': analysis_result['message']
                        }
                        self.anomaly_tracker.update_anomaly(anomaly)
                        new_anomalies.append(anomaly)

            if new_anomalies:
                with self.anomalies_lock:
                    self.latest_anomalies.extend(new_anomalies)
                    if len(self.latest_anomalies) > 20:
                        self.latest_anomalies = self.latest_anomalies[-20:]

            self.drools_engine.clear_facts()
            self.drools_engine.insert_facts(facts)
            drools_results = self.drools_engine.fire_all_rules()
            if drools_results:
                with self.drools_lock:
                    for result in drools_results:
                        result['timestamp'] = time.time()
                        result['device_id'] = device_id
                        self.latest_drools_results.append(result)
                    if len(self.latest_drools_results) > 20:
                        self.latest_drools_results = self.latest_drools_results[-20:]

            self.slider_detector.update_facts(facts)
            slider_result = self.slider_detector.check_abnormal()
            if slider_result['abnormal']:
                with self.slider_lock:
                    slider_result['timestamp'] = time.time()
                    slider_result['device_id'] = device_id
                    self.latest_slider_results.append(slider_result)
                    if len(self.latest_slider_results) > 10:
                        self.latest_slider_results = self.latest_slider_results[-10:]

            self._process_device_faults(device_id, data)

        return ProcessingResult(
            device_data_map=device_data_map,
            anomalies=new_anomalies,
            drools_results=new_drools_results,
            slider_results=new_slider_results,
            fault_status=new_fault_status
        )

    def prepare_socketio_data(self):
        device_data_map = {}
        
        with self.buffer_lock:
            if self.data_buffer:
                # 从缓冲区中获取最新的数据，按设备分组
                device_latest_data = {}
                
                # 倒序遍历，确保只保留每个设备的最新数据
                for buffer_item in reversed(list(self.data_buffer)):
                    device_id = buffer_item.get('device_id', 'unknown')
                    if device_id not in device_latest_data:
                        device_latest_data[device_id] = buffer_item
                
                # 构建发送数据包
                for device_id, buffer_item in device_latest_data.items():
                    device_data_map[device_id] = {
                        'device_id': device_id,
                        'device_name': buffer_item.get('device_name', device_id),
                        'current_values': {},
                        'history_data': []
                    }

                    latest_data = buffer_item['data']
                    
                    # 打印几个关键变量的值，确认数据在变化
                    print(f"[DataProcessor] {device_id} data sample:")
                    count = 0
                    for item in latest_data:
                        tag_name = item.get('tag_name')
                        if tag_name and count < 5:
                            print(f"  {tag_name}: {item['value']} (DB{item['db_number']}.{item['address']})")
                            count += 1
                    
                    for item in latest_data:
                        tag_name = item.get('tag_name')
                        if tag_name:
                            key = f"{device_id}:{tag_name}"
                            device_data_map[device_id]['current_values'][key] = item

                    # 添加一条历史数据
                    device_data_map[device_id]['history_data'].append({
                        'timestamp': buffer_item['timestamp'],
                        'data': latest_data
                    })
        
        return device_data_map

    def get_pending_anomalies(self):
        with self.anomalies_lock:
            anomalies = list(self.latest_anomalies)
            self.latest_anomalies.clear()
        return anomalies

    def get_pending_drools_results(self):
        with self.drools_lock:
            results = list(self.latest_drools_results)
            self.latest_drools_results.clear()
        return results

    def get_pending_slider_results(self):
        with self.slider_lock:
            results = list(self.latest_slider_results)
            self.latest_slider_results.clear()
        return results

    def get_fault_status(self):
        with self.fault_lock:
            return dict(self.latest_fault_status)
    
    def _process_device_faults(self, device_id: str, data: List[Dict[str, Any]]):
        """
        处理设备故障检测
        使用通用故障检测器框架进行故障分析
        
        Args:
            device_id: 设备ID
            data: 设备数据
        """
        # 根据设备ID确定设备类型
        device_type = self._get_device_type(device_id)
        
        if not device_type:
            return
        
        # 提取故障位数据和相关变量
        fault_data, var_values = self._extract_fault_data(device_id, data, device_type)
        
        if not fault_data:
            return
        
        # 使用通用故障检测器框架进行检测
        fault_result = self.detect_device_faults(device_id, device_type, fault_data, var_values)
        
        # 更新故障追踪器
        self.fault_tracker.update_faults(
            device_id, 
            fault_result['active_faults'], 
            'warning' if not fault_result['has_critical'] else 'critical'
        )
        
        # 获取活动故障及其持续时间
        active_faults_with_duration = self.fault_tracker.get_active_faults()
        severity = 'critical' if fault_result['has_critical'] else 'warning'
        
        # 更新最新故障状态
        with self.fault_lock:
            self.latest_fault_status[device_id] = {
                'device_id': device_id,
                'timestamp': time.time(),
                'total_faults': len(active_faults_with_duration),
                'has_critical': fault_result['has_critical'],
                'active_faults': active_faults_with_duration,
                'fault_analysis': fault_result['analysis'],
                'severity': severity,
                'device_type': device_type
            }
        
        # 打印日志
        print(f"[{device_id}] Fault Analysis ({device_type}): {len(active_faults_with_duration)} active faults, Critical: {fault_result['has_critical']}")
        if fault_result['total_faults'] > 0:
            print(f"[{device_id}] Active faults: {fault_result['active_faults'][:5]}...")
    
    def _get_device_type(self, device_id: str) -> Optional[str]:
        """
        根据设备ID确定设备类型
        
        Args:
            device_id: 设备ID
        
        Returns:
            设备类型字符串，如果无法确定返回None
        """
        # 设备类型映射
        device_type_map = {
            'plc_002': 'RXB800',
            # 可以在这里添加更多设备类型映射
        }
        
        return device_type_map.get(device_id)
    
    def _extract_fault_data(self, device_id: str, data: List[Dict[str, Any]], device_type: str) -> tuple:
        """
        提取故障位数据和相关变量
        
        Args:
            device_id: 设备ID
            data: 设备数据
            device_type: 设备类型
        
        Returns:
            (fault_data, var_values) 元组
        """
        fault_data = {}
        var_values = {}
        
        # 根据设备类型提取相应的数据
        if device_type == 'RXB800':
            # RXB800设备：DB51包含故障位，DB1和DB10包含相关变量
            for item in data:
                db_number = item.get('db_number')
                if db_number == 51:
                    fault_data[item['tag_name']] = item['value']
                elif db_number in (1, 10):
                    var_values[item['tag_name']] = item['value']
        else:
            # 默认：提取所有数据作为故障数据
            for item in data:
                fault_data[item['tag_name']] = item['value']
        
        return fault_data, var_values

    def get_active_anomalies(self):
        return self.anomaly_tracker.get_active_anomalies()