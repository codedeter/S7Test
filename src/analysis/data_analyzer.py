import numpy as np
from collections import defaultdict
import time


class DataAnalyzer:
    def __init__(self):
        self.data_history = defaultdict(list)
        self.min_samples = 10
        self.z_score_threshold = 3.0
        self.trend_threshold = 0.1
    
    def add_data_point(self, db_number, address, value):
        key = f"{db_number}:{address}"
        self.data_history[key].append({
            'timestamp': time.time(),
            'value': value
        })
        
        max_history = 100
        max_age_seconds = 300
        self._clean_history(key, max_history, max_age_seconds)
    
    def _clean_history(self, key, max_items, max_age_seconds):
        """
        清理历史数据
        移除超过数量限制或时间限制的数据
        """
        if len(self.data_history[key]) <= max_items:
            return
        
        now = time.time()
        self.data_history[key] = [
            item for item in self.data_history[key]
            if now - item['timestamp'] <= max_age_seconds
        ]
        
        if len(self.data_history[key]) > max_items:
            self.data_history[key] = self.data_history[key][-max_items:]
    
    def analyze_data(self, db_number, address, value):
        key = f"{db_number}:{address}"
        history = self.data_history[key]
        
        if len(history) < self.min_samples:
            return {'normal': True, 'confidence': 0.5}
        
        values = [item['value'] for item in history]
        timestamps = [item['timestamp'] for item in history]
        
        mean = np.mean(values)
        std_dev = np.std(values)
        
        if std_dev == 0:
            return {'normal': True, 'confidence': 0.9}
        
        z_score = abs((value - mean) / std_dev)
        
        if z_score > self.z_score_threshold:
            return {
                'normal': False,
                'confidence': min(1, z_score / 5),
                'message': f'值偏离正常范围过多，Z分数: {z_score:.2f}'
            }
        
        trend = self.calculate_trend(timestamps, values)
        if abs(trend) > self.trend_threshold:
            return {
                'normal': False,
                'confidence': min(1, abs(trend) * 10),
                'message': f'值变化趋势异常，趋势值: {trend:.2f}'
            }
        
        return {'normal': True, 'confidence': 0.9}
    
    def calculate_trend(self, timestamps, values):
        """
        计算趋势（归一化斜率）
        """
        n = len(values)
        if n < 2:
            return 0
        
        timestamps = np.array(timestamps)
        values = np.array(values)
        
        if np.max(timestamps) == np.min(timestamps):
            return 0
        
        normalized_timestamps = (timestamps - np.min(timestamps)) / (np.max(timestamps) - np.min(timestamps))
        
        slope, _ = np.polyfit(normalized_timestamps, values, 1)
        
        value_range = np.max(values) - np.min(values) if np.max(values) != np.min(values) else 1
        
        return slope / value_range
    
    def predict_value(self, db_number, address):
        key = f"{db_number}:{address}"
        history = self.data_history[key]
        
        if len(history) < 5:
            return None
        
        values = [item['value'] for item in history]
        timestamps = [item['timestamp'] for item in history]
        
        mean = np.mean(values)
        trend = self.calculate_trend(timestamps, values)
        
        value_range = np.max(values) - np.min(values) if len(values) > 1 else 1
        
        return mean + trend * value_range * 0.1