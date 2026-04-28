"""
RXA1300 设备故障检测器
使用可配置架构，复用 RX 系列基础故障
"""
from typing import List, Dict
from src.analysis.configurable_fault_detector import (
    RXFaultDetector, create_rx_detector
)


class RXA1300FaultDetector(RXFaultDetector):
    """
    RXA1300 设备故障检测器
    """
    
    def __init__(self):
        # 定义 RXA1300 特定的附加故障
        additional_faults = [
            # ===== 滤油器其他故障 =====
            {
                'name': '上油箱需补油',
                'bit_position': 5,
                'severity': 'warning',
                'description': '上油箱需要补油'
            },
            {
                'name': '润滑泵滤油器堵塞',
                'bit_position': 6,
                'severity': 'warning',
                'description': '润滑泵滤油器堵塞'
            },
            {
                'name': '辅助油路滤油堵塞',
                'bit_position': 7,
                'severity': 'warning',
                'description': '辅助油路滤油堵塞'
            },
            
            # ===== 急停故障 =====
            {
                'name': '操作站急停不合格',
                'bit_position': 12,
                'severity': 'critical',
                'description': '操作站急停按钮按下'
            },
            {
                'name': '左前立柱急停不合格',
                'bit_position': 13,
                'severity': 'critical',
                'description': '左前立柱急停按钮按下'
            },
            {
                'name': '右后立柱急停不合格',
                'bit_position': 14,
                'severity': 'critical',
                'description': '右后立柱急停按钮按下'
            },
            {
                'name': '左后立柱急停不合格',
                'bit_position': 15,
                'severity': 'critical',
                'description': '左后立柱急停按钮按下'
            },
            {
                'name': '右前立柱急停不合格',
                'bit_position': 16,
                'severity': 'critical',
                'description': '右前立柱急停按钮按下'
            },
            {
                'name': '前按钮站急停不合格',
                'bit_position': 17,
                'severity': 'critical',
                'description': '前按钮站急停按钮按下'
            },
            {
                'name': '后按钮站急停不合格',
                'bit_position': 18,
                'severity': 'critical',
                'description': '后按钮站急停按钮按下'
            },
            
            # ===== 安全光幕 =====
            {
                'name': '左光幕不合格',
                'bit_position': 19,
                'severity': 'critical',
                'description': '左安全光幕不合格'
            },
            {
                'name': '右光幕不合格',
                'bit_position': 20,
                'severity': 'critical',
                'description': '右安全光幕不合格'
            },
            
            # ===== 网络故障 =====
            {
                'name': 'PLC网络故障',
                'bit_position': 21,
                'severity': 'critical',
                'description': 'PLC网络故障'
            },
            {
                'name': '滑块驱动器网络故障',
                'bit_position': 22,
                'severity': 'critical',
                'description': '滑块驱动器网络故障'
            },
            {
                'name': '左移动台变频器网络故障',
                'bit_position': 23,
                'severity': 'critical',
                'description': '左移动台变频器网络故障'
            },
            {
                'name': '右移动台变频器网络故障',
                'bit_position': 24,
                'severity': 'critical',
                'description': '右移动台变频器网络故障'
            },
            {
                'name': '触摸屏网络故障',
                'bit_position': 25,
                'severity': 'critical',
                'description': '触摸屏网络故障'
            },
            {
                'name': '安全继电器网络故障',
                'bit_position': 26,
                'severity': 'critical',
                'description': '安全继电器网络故障'
            },
            {
                'name': '上循环泵变频器网络故障',
                'bit_position': 27,
                'severity': 'warning',
                'description': '上循环泵变频器网络故障'
            },
            {
                'name': '下循环泵变频器网络故障',
                'bit_position': 28,
                'severity': 'warning',
                'description': '下循环泵变频器网络故障'
            },
            {
                'name': '油温冷却循环泵变频器网络故障',
                'bit_position': 29,
                'severity': 'warning',
                'description': '油温冷却循环泵变频器网络故障'
            }
        ]
        
        # 调用父类初始化，复用 RX 系列基础故障
        super().__init__('RXA1300', additional_faults)


# 工厂函数
def create_rxa1300_detector() -> RXA1300FaultDetector:
    return RXA1300FaultDetector()
