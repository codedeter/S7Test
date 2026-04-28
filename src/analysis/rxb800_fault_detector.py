"""
RXB800设备故障检测器
继承自BaseFaultDetector，实现RXB800特定的86个故障位检测
"""

from src.analysis.fault_detector_base import BaseFaultDetector, FaultBit


class RXB800FaultDetector(BaseFaultDetector):
    """
    RXB800设备专用故障检测器
    包含86个故障位的定义和检测逻辑
    """
    
    DEVICE_TYPE = "RXB800"
    
    # 故障严重程度定义
    SEVERITY_CRITICAL = 'critical'
    SEVERITY_WARNING = 'warning'
    SEVERITY_INFO = 'info'
    
    # 需要安全条件过滤的故障
    SAFETY_FILTERED_FAULTS = {
        '左光幕不合格',
        '右光幕不合格'
    }
    
    def _init_fault_bits(self):
        """
        初始化RXB800设备的86个故障位
        """
        # ===== 油温相关故障 =====
        self.register_fault_bit(FaultBit(
            name='上油箱油温过低',
            bit_position=0,
            severity=self.SEVERITY_WARNING,
            description='上油箱油温低于正常范围',
            related_variables=['上油箱油温'],
            condition_type='analog',
            normal_range=(10.0, 60.0),
            unit='°C'
        ))
        
        self.register_fault_bit(FaultBit(
            name='上油箱油需冷却',
            bit_position=1,
            severity=self.SEVERITY_WARNING,
            description='上油箱油温需要冷却',
            related_variables=['上油箱油温'],
            condition_type='analog',
            threshold=50.0,
            unit='°C'
        ))
        
        self.register_fault_bit(FaultBit(
            name='上油箱油温过高',
            bit_position=2,
            severity=self.SEVERITY_CRITICAL,
            description='上油箱油温过高，可能导致设备损坏',
            related_variables=['上油箱油温'],
            condition_type='analog',
            normal_range=(10.0, 60.0),
            unit='°C'
        ))
        
        # ===== 滤油器故障 =====
        self.register_fault_bit(FaultBit(
            name='上油箱滤油受阻',
            bit_position=3,
            severity=self.SEVERITY_WARNING,
            description='上油箱滤油器受阻'
        ))
        
        self.register_fault_bit(FaultBit(
            name='上油箱油空',
            bit_position=4,
            severity=self.SEVERITY_CRITICAL,
            description='上油箱油位为空'
        ))
        
        self.register_fault_bit(FaultBit(
            name='上油箱需补油',
            bit_position=5,
            severity=self.SEVERITY_WARNING,
            description='上油箱需要补充油液'
        ))
        
        self.register_fault_bit(FaultBit(
            name='润滑泵滤油器堵塞',
            bit_position=6,
            severity=self.SEVERITY_WARNING,
            description='润滑泵滤油器堵塞'
        ))
        
        self.register_fault_bit(FaultBit(
            name='辅助油路滤油堵塞',
            bit_position=7,
            severity=self.SEVERITY_WARNING,
            description='辅助油路滤油器堵塞'
        ))
        
        self.register_fault_bit(FaultBit(
            name='流量阀滤油堵塞',
            bit_position=8,
            severity=self.SEVERITY_WARNING,
            description='流量阀滤油器堵塞'
        ))
        
        self.register_fault_bit(FaultBit(
            name='伺服阀滤油堵塞',
            bit_position=9,
            severity=self.SEVERITY_WARNING,
            description='伺服阀滤油器堵塞'
        ))
        
        self.register_fault_bit(FaultBit(
            name='3Y4滤油受阻',
            bit_position=10,
            severity=self.SEVERITY_WARNING,
            description='3Y4阀滤油受阻'
        ))
        
        # ===== 润滑系统故障 =====
        self.register_fault_bit(FaultBit(
            name='润滑液位低故障',
            bit_position=11,
            severity=self.SEVERITY_CRITICAL,
            description='润滑系统液位过低'
        ))
        
        # ===== 急停故障 =====
        self.register_fault_bit(FaultBit(
            name='操作站急停不合格',
            bit_position=12,
            severity=self.SEVERITY_CRITICAL,
            description='操作站急停按钮触发'
        ))
        
        self.register_fault_bit(FaultBit(
            name='左前立柱急停不合格',
            bit_position=13,
            severity=self.SEVERITY_CRITICAL,
            description='左前立柱急停按钮触发'
        ))
        
        self.register_fault_bit(FaultBit(
            name='右后立柱急停不合格',
            bit_position=14,
            severity=self.SEVERITY_CRITICAL,
            description='右后立柱急停按钮触发'
        ))
        
        self.register_fault_bit(FaultBit(
            name='左后立柱急停不合格',
            bit_position=15,
            severity=self.SEVERITY_CRITICAL,
            description='左后立柱急停按钮触发'
        ))
        
        self.register_fault_bit(FaultBit(
            name='右前立柱急停不合格',
            bit_position=16,
            severity=self.SEVERITY_CRITICAL,
            description='右前立柱急停按钮触发'
        ))
        
        self.register_fault_bit(FaultBit(
            name='前按钮站急停不合格',
            bit_position=17,
            severity=self.SEVERITY_CRITICAL,
            description='前按钮站急停按钮触发'
        ))
        
        self.register_fault_bit(FaultBit(
            name='后按钮站急停不合格',
            bit_position=18,
            severity=self.SEVERITY_CRITICAL,
            description='后按钮站急停按钮触发'
        ))
        
        # ===== 安全光幕 =====
        self.register_fault_bit(FaultBit(
            name='左光幕不合格',
            bit_position=19,
            severity=self.SEVERITY_WARNING,
            description='左安全光幕被遮挡'
        ))
        
        self.register_fault_bit(FaultBit(
            name='右光幕不合格',
            bit_position=20,
            severity=self.SEVERITY_WARNING,
            description='右安全光幕被遮挡'
        ))
        
        # ===== 位移偏差 =====
        self.register_fault_bit(FaultBit(
            name='位移偏差不合格',
            bit_position=21,
            severity=self.SEVERITY_WARNING,
            description='位移偏差超过允许范围'
        ))
        
        # ===== 滑块位置状态 =====
        self.register_fault_bit(FaultBit(
            name='滑块处于上极限',
            bit_position=22,
            severity=self.SEVERITY_INFO,
            description='滑块处于上极限位置'
        ))
        
        self.register_fault_bit(FaultBit(
            name='滑块处于下极限',
            bit_position=23,
            severity=self.SEVERITY_INFO,
            description='滑块处于下极限位置'
        ))
        
        # ===== 操作状态 =====
        self.register_fault_bit(FaultBit(
            name='操作台静止按下',
            bit_position=24,
            severity=self.SEVERITY_INFO,
            description='操作台静止按钮被按下'
        ))
        
        # ===== 闸阀状态 =====
        self.register_fault_bit(FaultBit(
            name='闸阀3S113关闭',
            bit_position=25,
            severity=self.SEVERITY_WARNING,
            description='闸阀3S113关闭'
        ))
        
        self.register_fault_bit(FaultBit(
            name='闸阀3S114关闭',
            bit_position=26,
            severity=self.SEVERITY_WARNING,
            description='闸阀3S114关闭'
        ))
        
        self.register_fault_bit(FaultBit(
            name='闸阀3S115关闭',
            bit_position=27,
            severity=self.SEVERITY_WARNING,
            description='闸阀3S115关闭'
        ))
        
        # ===== 电源故障 =====
        self.register_fault_bit(FaultBit(
            name='5Q1电源未接通',
            bit_position=28,
            severity=self.SEVERITY_CRITICAL,
            description='5Q1电源未接通'
        ))
        
        self.register_fault_bit(FaultBit(
            name='提升夹紧截止阀未打开到位',
            bit_position=29,
            severity=self.SEVERITY_WARNING,
            description='提升夹紧截止阀未打开到位'
        ))
        
        self.register_fault_bit(FaultBit(
            name='充液截止阀1位打开到位',
            bit_position=30,
            severity=self.SEVERITY_INFO,
            description='充液截止阀1位打开到位'
        ))
        
        self.register_fault_bit(FaultBit(
            name='充液截止阀2位打开到位',
            bit_position=31,
            severity=self.SEVERITY_INFO,
            description='充液截止阀2位打开到位'
        ))
        
        self.register_fault_bit(FaultBit(
            name='充液截止阀3位打开到位',
            bit_position=32,
            severity=self.SEVERITY_INFO,
            description='充液截止阀3位打开到位'
        ))
        
        self.register_fault_bit(FaultBit(
            name='上模夹紧泵站液位低',
            bit_position=33,
            severity=self.SEVERITY_WARNING,
            description='上模夹紧泵站液位低'
        ))
        
        # ===== 网络故障 =====
        self.register_fault_bit(FaultBit(
            name='PLC网络故障',
            bit_position=34,
            severity=self.SEVERITY_CRITICAL,
            description='PLC网络通信故障',
            condition_type='network'
        ))
        
        self.register_fault_bit(FaultBit(
            name='动力柜网络故障',
            bit_position=35,
            severity=self.SEVERITY_CRITICAL,
            description='动力柜网络通信故障',
            condition_type='network'
        ))
        
        self.register_fault_bit(FaultBit(
            name='操作站网络故障',
            bit_position=36,
            severity=self.SEVERITY_CRITICAL,
            description='操作站网络通信故障',
            condition_type='network'
        ))
        
        self.register_fault_bit(FaultBit(
            name='底梁网络故障',
            bit_position=37,
            severity=self.SEVERITY_CRITICAL,
            description='底梁网络通信故障',
            condition_type='network'
        ))
        
        self.register_fault_bit(FaultBit(
            name='上梁网络故障',
            bit_position=38,
            severity=self.SEVERITY_CRITICAL,
            description='上梁网络通信故障',
            condition_type='network'
        ))
        
        self.register_fault_bit(FaultBit(
            name='下油箱网络故障',
            bit_position=39,
            severity=self.SEVERITY_CRITICAL,
            description='下油箱网络通信故障',
            condition_type='network'
        ))
        
        self.register_fault_bit(FaultBit(
            name='滑块网络故障',
            bit_position=40,
            severity=self.SEVERITY_CRITICAL,
            description='滑块网络通信故障',
            condition_type='network'
        ))
        
        self.register_fault_bit(FaultBit(
            name='滑块左位移传感器网络故障',
            bit_position=41,
            severity=self.SEVERITY_CRITICAL,
            description='滑块左位移传感器网络故障',
            condition_type='network'
        ))
        
        self.register_fault_bit(FaultBit(
            name='左G120网络故障',
            bit_position=42,
            severity=self.SEVERITY_CRITICAL,
            description='左G120变频器网络故障',
            condition_type='network'
        ))
        
        # ===== 变频器故障 =====
        self.register_fault_bit(FaultBit(
            name='左变频器故障',
            bit_position=43,
            severity=self.SEVERITY_CRITICAL,
            description='左变频器故障'
        ))
        
        self.register_fault_bit(FaultBit(
            name='右变频器故障',
            bit_position=44,
            severity=self.SEVERITY_CRITICAL,
            description='右变频器故障'
        ))
        
        self.register_fault_bit(FaultBit(
            name='左缓冲变频器故障',
            bit_position=45,
            severity=self.SEVERITY_CRITICAL,
            description='左缓冲变频器故障'
        ))
        
        self.register_fault_bit(FaultBit(
            name='右缓冲变频器故障',
            bit_position=46,
            severity=self.SEVERITY_CRITICAL,
            description='右缓冲变频器故障'
        ))
        
        # ===== 更多电源故障 =====
        self.register_fault_bit(FaultBit(
            name='2Q1电源未接通',
            bit_position=47,
            severity=self.SEVERITY_CRITICAL,
            description='2Q1电源未接通'
        ))
        
        self.register_fault_bit(FaultBit(
            name='2Q2电源未接通',
            bit_position=48,
            severity=self.SEVERITY_CRITICAL,
            description='2Q2电源未接通'
        ))
        
        self.register_fault_bit(FaultBit(
            name='4Q1电源未接通',
            bit_position=49,
            severity=self.SEVERITY_CRITICAL,
            description='4Q1电源未接通'
        ))
        
        self.register_fault_bit(FaultBit(
            name='4Q2电源未接通',
            bit_position=50,
            severity=self.SEVERITY_CRITICAL,
            description='4Q2电源未接通'
        ))
        
        self.register_fault_bit(FaultBit(
            name='2Q7电源未接通',
            bit_position=51,
            severity=self.SEVERITY_CRITICAL,
            description='2Q7电源未接通'
        ))
        
        self.register_fault_bit(FaultBit(
            name='5Q2电源未接通',
            bit_position=52,
            severity=self.SEVERITY_CRITICAL,
            description='5Q2电源未接通'
        ))
        
        self.register_fault_bit(FaultBit(
            name='5Q3电源未接通',
            bit_position=53,
            severity=self.SEVERITY_CRITICAL,
            description='5Q3电源未接通'
        ))
        
        self.register_fault_bit(FaultBit(
            name='7Q1电源未接通',
            bit_position=54,
            severity=self.SEVERITY_CRITICAL,
            description='7Q1电源未接通'
        ))
        
        self.register_fault_bit(FaultBit(
            name='1Q3电源未接通',
            bit_position=55,
            severity=self.SEVERITY_CRITICAL,
            description='1Q3电源未接通'
        ))
        
        self.register_fault_bit(FaultBit(
            name='2Q5电源未接通',
            bit_position=56,
            severity=self.SEVERITY_CRITICAL,
            description='2Q5电源未接通'
        ))
        
        self.register_fault_bit(FaultBit(
            name='14Q1电源未接通',
            bit_position=57,
            severity=self.SEVERITY_CRITICAL,
            description='14Q1电源未接通'
        ))
        
        self.register_fault_bit(FaultBit(
            name='1Q10电源未接通',
            bit_position=58,
            severity=self.SEVERITY_CRITICAL,
            description='1Q10电源未接通'
        ))
        
        self.register_fault_bit(FaultBit(
            name='1Q11电源未接通',
            bit_position=59,
            severity=self.SEVERITY_CRITICAL,
            description='1Q11电源未接通'
        ))
        
        self.register_fault_bit(FaultBit(
            name='1Q12电源未接通',
            bit_position=60,
            severity=self.SEVERITY_CRITICAL,
            description='1Q12电源未接通'
        ))
        
        self.register_fault_bit(FaultBit(
            name='8Q1电源未接通',
            bit_position=61,
            severity=self.SEVERITY_CRITICAL,
            description='8Q1电源未接通'
        ))
        
        self.register_fault_bit(FaultBit(
            name='8Q2电源未接通',
            bit_position=62,
            severity=self.SEVERITY_CRITICAL,
            description='8Q2电源未接通'
        ))
        
        # ===== 电能表网络 =====
        self.register_fault_bit(FaultBit(
            name='电能表网络故障',
            bit_position=63,
            severity=self.SEVERITY_WARNING,
            description='电能表网络通信故障',
            condition_type='network'
        ))
        
        # ===== 传感器网络 =====
        self.register_fault_bit(FaultBit(
            name='滑块位移传感器网络故障',
            bit_position=64,
            severity=self.SEVERITY_CRITICAL,
            description='滑块位移传感器网络故障',
            condition_type='network'
        ))
        
        # ===== 变频器网络 =====
        self.register_fault_bit(FaultBit(
            name='左缓冲变频器网络故障',
            bit_position=65,
            severity=self.SEVERITY_CRITICAL,
            description='左缓冲变频器网络故障',
            condition_type='network'
        ))
        
        self.register_fault_bit(FaultBit(
            name='右缓冲变频器网络故障',
            bit_position=66,
            severity=self.SEVERITY_CRITICAL,
            description='右缓冲变频器网络故障',
            condition_type='network'
        ))
        
        self.register_fault_bit(FaultBit(
            name='移动台变频器网络故障',
            bit_position=67,
            severity=self.SEVERITY_CRITICAL,
            description='移动台变频器网络故障',
            condition_type='network'
        ))
        
        self.register_fault_bit(FaultBit(
            name='左移动台变频器网络故障',
            bit_position=68,
            severity=self.SEVERITY_CRITICAL,
            description='左移动台变频器网络故障',
            condition_type='network'
        ))
        
        self.register_fault_bit(FaultBit(
            name='右移动台变频器传感器网络故障',
            bit_position=69,
            severity=self.SEVERITY_CRITICAL,
            description='右移动台变频器传感器网络故障',
            condition_type='network'
        ))
        
        # ===== 编码器网络 =====
        self.register_fault_bit(FaultBit(
            name='左缓冲编码器网络故障',
            bit_position=70,
            severity=self.SEVERITY_CRITICAL,
            description='左缓冲编码器网络故障',
            condition_type='network'
        ))
        
        self.register_fault_bit(FaultBit(
            name='右缓冲编码器网络故障',
            bit_position=71,
            severity=self.SEVERITY_CRITICAL,
            description='右缓冲编码器网络故障',
            condition_type='network'
        ))
        
        # ===== KM电源 =====
        self.register_fault_bit(FaultBit(
            name='2KM1电源未接通',
            bit_position=72,
            severity=self.SEVERITY_CRITICAL,
            description='2KM1电源未接通'
        ))
        
        self.register_fault_bit(FaultBit(
            name='2KM2电源未接通',
            bit_position=73,
            severity=self.SEVERITY_CRITICAL,
            description='2KM2电源未接通'
        ))
        
        # ===== 伺服故障 =====
        self.register_fault_bit(FaultBit(
            name='2M1伺服故障报警',
            bit_position=74,
            severity=self.SEVERITY_CRITICAL,
            description='2M1伺服驱动器故障报警'
        ))
        
        self.register_fault_bit(FaultBit(
            name='2M2伺服故障报警',
            bit_position=75,
            severity=self.SEVERITY_CRITICAL,
            description='2M2伺服驱动器故障报警'
        ))
        
        # ===== 滑块报警 =====
        self.register_fault_bit(FaultBit(
            name='滑块下滑报警',
            bit_position=76,
            severity=self.SEVERITY_CRITICAL,
            description='滑块下滑报警'
        ))
        
        # ===== 缓冲位置 =====
        self.register_fault_bit(FaultBit(
            name='左缓冲位置与配方不匹配',
            bit_position=77,
            severity=self.SEVERITY_WARNING,
            description='左缓冲位置与配方不匹配'
        ))
        
        self.register_fault_bit(FaultBit(
            name='右缓冲位置与配方不匹配',
            bit_position=78,
            severity=self.SEVERITY_WARNING,
            description='右缓冲位置与配方不匹配'
        ))
        
        # ===== 按钮状态 =====
        self.register_fault_bit(FaultBit(
            name='左前按钮需更换',
            bit_position=79,
            severity=self.SEVERITY_WARNING,
            description='左前按钮需要更换'
        ))
        
        self.register_fault_bit(FaultBit(
            name='右前按钮需更换',
            bit_position=80,
            severity=self.SEVERITY_WARNING,
            description='右前按钮需要更换'
        ))
        
        self.register_fault_bit(FaultBit(
            name='左后按钮需更换',
            bit_position=81,
            severity=self.SEVERITY_WARNING,
            description='左后按钮需要更换'
        ))
        
        self.register_fault_bit(FaultBit(
            name='右后按钮需更换',
            bit_position=82,
            severity=self.SEVERITY_WARNING,
            description='右后按钮需要更换'
        ))
        
        # ===== MES通信 =====
        self.register_fault_bit(FaultBit(
            name='获取MES当前计划数量为0',
            bit_position=83,
            severity=self.SEVERITY_INFO,
            description='MES当前计划数量为0'
        ))
        
        self.register_fault_bit(FaultBit(
            name='获取MES无订单',
            bit_position=84,
            severity=self.SEVERITY_INFO,
            description='MES无订单'
        ))
        
        self.register_fault_bit(FaultBit(
            name='与MES握手失败',
            bit_position=85,
            severity=self.SEVERITY_WARNING,
            description='与MES系统握手失败'
        ))
        
        # ===== 安全门状态 =====
        self.register_fault_bit(FaultBit(
            name='左安全门上升',
            bit_position=86,
            severity=self.SEVERITY_INFO,
            description='左安全门上升'
        ))
        
        self.register_fault_bit(FaultBit(
            name='左安全门下降',
            bit_position=87,
            severity=self.SEVERITY_INFO,
            description='左安全门下降'
        ))
    
    def _init_fault_relations(self):
        """
        初始化故障位与变量的关系映射
        """
        # 这个方法在基类中已经通过FaultBit的related_variables实现
        # 这里可以添加额外的关系逻辑
        pass
    
    def _should_filter_fault(self, fault_name: str, var_values: dict) -> bool:
        """
        判断是否应该过滤某个故障
        
        RXB800特定逻辑：当安全条件不满足时，忽略光栅故障
        """
        if not var_values:
            return False
        
        # 安全条件：双手合格且允许下行
        safety_conditions = var_values.get('双手合格', 0) == 1 and var_values.get('允许下行', 0) == 1
        
        if not safety_conditions:
            # 安全条件不满足时，过滤光栅故障
            if fault_name in self.SAFETY_FILTERED_FAULTS:
                return True
        
        return False