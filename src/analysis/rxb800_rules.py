class FaultRule:
    def __init__(self, fault_bit: str, related_vars: list, condition: str = "any_fault"):
        self.fault_bit = fault_bit
        self.related_vars = related_vars
        self.condition = condition

    def is_triggered(self, db51_values: dict) -> bool:
        fault_value = db51_values.get(self.fault_bit, 0)
        return fault_value == 1

class RXB800FaultRules:
    FAULT_VAR_MAP = {
        '上油箱油温': {
            'faults': ['上油箱油温过低', '上油箱油温过高', '上油箱油需冷却'],
            'threshold_vars': {
                'low': '上油需加热温度',
                'cooling': '油需冷却温度',
                'high': '油超温温度'
            },
            'unit': '°C'
        },
        '冷却水温度': {
            'faults': [],  # 无直接故障关联
            'normal_range': (5.0, 40.0),
            'unit': '°C'
        },
        '主缸压力Mpa': {
            'faults': ['压力偏差过大'],
            'normal_range': (0.0, 35.0),
            'unit': 'MPa'
        },
        '侧缸压力Mpa': {
            'faults': [],
            'normal_range': (0.0, 35.0),
            'unit': 'MPa'
        },
        '上油箱油温过低': {
            'faults': ['上油箱油温过低'],
            'normal_range': (10.0, 100.0),
            'unit': '状态'
        },
        '上油箱油温过高': {
            'faults': ['上油箱油温过高'],
            'normal_range': (0.0, 1.0),
            'unit': '状态'
        },
        '上油箱油需冷却': {
            'faults': ['上油箱油需冷却'],
            'normal_range': (0.0, 1.0),
            'unit': '状态'
        },
        '润滑液位低故障': {
            'faults': ['润滑液位低故障'],
            'normal_range': (0.0, 1.0),
            'unit': '状态'
        },
        '润滑泵滤油器堵塞': {
            'faults': ['润滑泵滤油器堵塞'],
            'normal_range': (0.0, 1.0),
            'unit': '状态'
        },
        '2M1伺服故障报警': {
            'faults': ['2M1伺服故障报警'],
            'normal_range': (0.0, 1.0),
            'unit': '状态'
        },
        '2M2伺服故障报警': {
            'faults': ['2M2伺服故障报警'],
            'normal_range': (0.0, 1.0),
            'unit': '状态'
        },
        '左变频器故障': {
            'faults': ['左变频器故障'],
            'normal_range': (0.0, 1.0),
            'unit': '状态'
        },
        '右变频器故障': {
            'faults': ['右变频器故障'],
            'normal_range': (0.0, 1.0),
            'unit': '状态'
        },
        '左缓冲变频器故障': {
            'faults': ['左缓冲变频器故障'],
            'normal_range': (0.0, 1.0),
            'unit': '状态'
        },
        '右缓冲变频器故障': {
            'faults': ['右缓冲变频器故障'],
            'normal_range': (0.0, 1.0),
            'unit': '状态'
        },
        'PLC网络故障': {
            'faults': ['PLC网络故障'],
            'normal_range': (0.0, 1.0),
            'unit': '状态'
        },
        '滑块网络故障': {
            'faults': ['滑块网络故障'],
            'normal_range': (0.0, 1.0),
            'unit': '状态'
        },
        '左G120网络故障': {
            'faults': ['左G120网络故障'],
            'normal_range': (0.0, 1.0),
            'unit': '状态'
        },
    }

    @staticmethod
    def get_db51_fault_bits() -> dict:
        return {
            '上油箱油温过低': 0,
            '上油箱油需冷却': 1,
            '上油箱油温过高': 2,
            '上油箱滤油受阻': 3,
            '上油箱油空': 4,
            '上油箱需补油': 5,
            '润滑泵滤油器堵塞': 6,
            '辅助油路滤油堵塞': 7,
            '流量阀滤油堵塞': 8,
            '伺服阀滤油堵塞': 9,
            '3Y4滤油受阻': 10,
            '润滑液位低故障': 11,
            '操作站急停不合格': 12,
            '左前立柱急停不合格': 13,
            '右后立柱急停不合格': 14,
            '左后立柱急停不合格': 15,
            '右前立柱急停不合格': 16,
            '前按钮站急停不合格': 17,
            '后按钮站急停不合格': 18,
            '左光幕不合格': 19,
            '右光幕不合格': 20,
            '位移偏差不合格': 21,
            '滑块处于上极限': 22,
            '滑块处于下极限': 23,
            '操作台静止按下': 24,
            '闸阀3S113关闭': 25,
            '闸阀3S114关闭': 26,
            '闸阀3S115关闭': 27,
            '5Q1电源未接通': 28,
            '提升夹紧截止阀未打开到位': 29,
            '充液截止阀1位打开到位': 30,
            '充液截止阀2位打开到位': 31,
            '充液截止阀3位打开到位': 32,
            '上模夹紧泵站液位低': 33,
            'PLC网络故障': 34,
            '动力柜网络故障': 35,
            '操作站网络故障': 36,
            '底梁网络故障': 37,
            '上梁网络故障': 38,
            '下油箱网络故障': 39,
            '滑块网络故障': 40,
            '滑块左位移传感器网络故障': 41,
            '左G120网络故障': 42,
            '左变频器故障': 43,
            '右变频器故障': 44,
            '左缓冲变频器故障': 45,
            '右缓冲变频器故障': 46,
            '2Q1电源未接通': 47,
            '2Q2电源未接通': 48,
            '4Q1电源未接通': 49,
            '4Q2电源未接通': 50,
            '2Q7电源未接通': 51,
            '5Q2电源未接通': 52,
            '5Q3电源未接通': 53,
            '7Q1电源未接通': 54,
            '1Q3电源未接通': 55,
            '2Q5电源未接通': 56,
            '14Q1电源未接通': 57,
            '1Q10电源未接通': 58,
            '1Q11电源未接通': 59,
            '1Q12电源未接通': 60,
            '8Q1电源未接通': 61,
            '8Q2电源未接通': 62,
            '电能表网络故障': 63,
            '滑块位移传感器网络故障': 64,
            '左缓冲变频器网络故障': 65,
            '右缓冲变频器网络故障': 66,
            '移动台变频器网络故障': 67,
            '左移动台变频器网络故障': 68,
            '右移动台变频器传感器网络故障': 69,
            '左缓冲编码器网络故障': 70,
            '右缓冲编码器网络故障': 71,
            '2KM1电源未接通': 72,
            '2KM2电源未接通': 73,
            '2M1伺服故障报警': 74,
            '2M2伺服故障报警': 75,
            '滑块下滑报警': 76,
            '左缓冲位置与配方不匹配': 77,
            '右缓冲位置与配方不匹配': 78,
            '左前按钮需更换': 79,
            '右前按钮需更换': 80,
            '左后按钮需更换': 81,
            '右后按钮需更换': 82,
            '获取MES当前计划数量为0': 83,
            '获取MES无订单': 84,
            '与MES握手失败': 85,
            '左安全门上升': 86,
            '左安全门下降': 87,
        }

    @staticmethod
    def get_fault_to_var_relations() -> dict:
        return {
            '上油箱油温过低': {
                'type': 'analog',
                'var_name': '上油箱油温',
                'condition': 'below',
                'threshold_var': '上油需加热温度',
                'action': '开启上油箱加热',
                'severity': 'warning'
            },
            '上油箱油温过高': {
                'type': 'analog',
                'var_name': '上油箱油温',
                'condition': 'above',
                'threshold_var': '油超温温度',
                'action': '主电机停止运行',
                'severity': 'critical'
            },
            '上油箱油需冷却': {
                'type': 'analog',
                'var_name': '上油箱油温',
                'condition': 'needs_cooling',
                'threshold_var': '油需冷却温度',
                'action': '开启冷却循环泵',
                'severity': 'warning'
            },
            '润滑液位低故障': {
                'type': 'status',
                'var_name': '润滑液位状态',
                'condition': 'low',
                'severity': 'critical'
            },
            '润滑泵滤油器堵塞': {
                'type': 'status',
                'var_name': '润滑泵状态',
                'condition': 'blocked',
                'severity': 'warning'
            },
            '2M1伺服故障报警': {
                'type': 'status',
                'var_name': '2M1伺服状态',
                'condition': 'fault',
                'severity': 'critical'
            },
            '2M2伺服故障报警': {
                'type': 'status',
                'var_name': '2M2伺服状态',
                'condition': 'fault',
                'severity': 'critical'
            },
            '左变频器故障': {
                'type': 'status',
                'var_name': '左变频器状态',
                'condition': 'fault',
                'severity': 'critical'
            },
            '右变频器故障': {
                'type': 'status',
                'var_name': '右变频器状态',
                'condition': 'fault',
                'severity': 'critical'
            },
            '左缓冲变频器故障': {
                'type': 'status',
                'var_name': '左缓冲变频器状态',
                'condition': 'fault',
                'severity': 'critical'
            },
            '右缓冲变频器故障': {
                'type': 'status',
                'var_name': '右缓冲变频器状态',
                'condition': 'fault',
                'severity': 'critical'
            },
            'PLC网络故障': {
                'type': 'network',
                'var_name': 'PLC连接',
                'condition': 'offline',
                'severity': 'critical'
            },
            '滑块网络故障': {
                'type': 'network',
                'var_name': '滑块网络',
                'condition': 'offline',
                'severity': 'critical'
            },
            '左G120网络故障': {
                'type': 'network',
                'var_name': '左G120网络',
                'condition': 'offline',
                'severity': 'critical'
            },
            '滑块处于上极限': {
                'type': 'status',
                'var_name': '滑块位置状态',
                'condition': 'upper_limit',
                'severity': 'info'
            },
            '滑块处于下极限': {
                'type': 'status',
                'var_name': '滑块位置状态',
                'condition': 'lower_limit',
                'severity': 'info'
            },
            '位移偏差不合格': {
                'type': 'status',
                'var_name': '位移偏差状态',
                'condition': 'abnormal',
                'severity': 'warning'
            },
        }

    @staticmethod
    def analyze_with_rules(db51_values: dict, var_values: dict) -> dict:
        results = {}
        relations = RXB800FaultRules.get_fault_to_var_relations()

        for fault_name, is_fault_active in db51_values.items():
            if is_fault_active == 1 and fault_name in relations:
                relation = relations[fault_name]

                if fault_name in ('左光幕不合格', '右光幕不合格'):
                    continue

                var_name = relation['var_name']

                if var_name not in results:
                    results[var_name] = {
                        'normal': True,
                        'faults': [],
                        'severity': 'normal'
                    }

                results[var_name]['normal'] = False
                results[var_name]['faults'].append({
                    'fault_name': fault_name,
                    'severity': relation['severity'],
                    'condition': relation['condition']
                })

                if relation['severity'] == 'critical':
                    results[var_name]['severity'] = 'critical'
                elif relation['severity'] == 'warning' and results[var_name]['severity'] != 'critical':
                    results[var_name]['severity'] = 'warning'

        safety_conditions = var_values.get('双手合格', 0) == 1 and var_values.get('允许下行', 0) == 1
        if not safety_conditions:
            for fault_name in ('左光幕不合格', '右光幕不合格'):
                if db51_values.get(fault_name, 0) == 1:
                    print(f"[RXB800] 光栅故障 {fault_name} 已忽略 (双手合格={var_values.get('双手合格', 0)}, 允许下行={var_values.get('允许下行', 0)})")

        return results

    @staticmethod
    def get_active_fault_count(db51_values: dict) -> int:
        return sum(1 for v in db51_values.values() if v == 1)

    @staticmethod
    def get_fault_summary(db51_values: dict, var_values: dict = None) -> dict:
        active_faults = [name for name, value in db51_values.items() if value == 1]

        if var_values:
            safety_conditions = var_values.get('双手合格', 0) == 1 and var_values.get('允许下行', 0) == 1
            if not safety_conditions:
                active_faults = [f for f in active_faults if f not in ('左光幕不合格', '右光幕不合格')]

        return {
            'total_faults': len(active_faults),
            'active_faults': active_faults,
            'has_critical': any(f in ['PLC网络故障', '滑块网络故障', '2M1伺服故障报警',
                                       '2M2伺服故障报警', '左变频器故障', '右变频器故障',
                                       '左缓冲变频器故障', '右缓冲变频器故障', '上油箱油温过高',
                                       '润滑液位低故障']
                               for f in active_faults)
        }
