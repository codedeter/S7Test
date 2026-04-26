import numpy as np
from collections import defaultdict

class DataAnalyzer:
    def __init__(self):
        self.data_history = defaultdict(list)
        self.threshold = 0.8
    
    def add_data_point(self, db_number, address, value):
        key = f"{db_number}:{address}"
        self.data_history[key].append({
            'timestamp': np.datetime64('now'),
            'value': value
        })
        
        if len(self.data_history[key]) > 100:
            self.data_history[key].pop(0)
    
    def analyze_data(self, db_number, address, value):
        key = f"{db_number}:{address}"
        history = self.data_history[key]
        
        if len(history) < 10:
            return {'normal': True, 'confidence': 0.5}
        
        values = [item['value'] for item in history]
        mean = np.mean(values)
        std_dev = np.std(values)
        
        if std_dev == 0:
            return {'normal': True, 'confidence': 0.9}
        
        z_score = abs((value - mean) / std_dev)
        
        if z_score > 3:
            return {
                'normal': False,
                'confidence': min(1, z_score / 5),
                'message': f'值偏离正常范围过多，Z分数: {z_score:.2f}'
            }
        
        trend = self.calculate_trend(history)
        if abs(trend) > 0.1:
            return {
                'normal': False,
                'confidence': min(1, abs(trend) * 10),
                'message': f'值变化趋势异常，趋势值: {trend:.2f}'
            }
        
        return {'normal': True, 'confidence': 0.9}
    
    def calculate_trend(self, history):
        values = [item['value'] for item in history]
        n = len(values)
        if n < 2:
            return 0
        
        x = np.arange(n)
        slope, _ = np.polyfit(x, values, 1)
        return slope
    
    def predict_value(self, db_number, address):
        key = f"{db_number}:{address}"
        history = self.data_history[key]
        
        if len(history) < 5:
            return None
        
        values = [item['value'] for item in history]
        mean = np.mean(values)
        trend = self.calculate_trend(history)
        
        return mean + trend * 5
