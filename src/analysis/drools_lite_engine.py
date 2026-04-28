"""
Drools Lite - 轻量级规则引擎
完全自包含，无需外部依赖，Python 3兼容
"""
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class RulePriority(Enum):
    """规则优先级"""
    EMERGENCY = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


@dataclass
class Rule:
    """规则类"""
    rule_id: str
    name: str
    description: str
    condition: Callable[[Dict[str, Any]], bool]
    action: Callable[[Dict[str, Any]], Dict[str, Any]]
    severity: RulePriority
    enabled: bool = True


class DroolsLite:
    """
    Drools Lite 轻量级规则引擎
    """
    
    def __init__(self):
        self.facts: Dict[str, Any] = {}
        self.rules: List[Rule] = []
        self.fired_rules: List[Dict[str, Any]] = []
        self._init_plc_rules()
    
    def _init_plc_rules(self):
        """初始化PLC故障诊断规则"""
        
        # 规则1: 油温过低警告
        self.add_rule(
            rule_id="TEMPERATURE_LOW_001",
            name="油温过低警告",
            description="实际油温低于上油需加热温度，开启上油箱加热",
            condition=lambda facts: facts.get('上油箱油温', 0) < facts.get('上油需加热温度', 0),
            action=lambda facts: {
                'rule_id': 'TEMPERATURE_LOW_001',
                'name': '油温过低警告',
                'severity': 'low',
                'description': f'油温过低需加热: {facts.get("上油箱油温", 0):.1f}°C < {facts.get("上油需加热温度", 0):.1f}°C',
                'value': facts.get('上油箱油温', 0),
                'threshold': facts.get('上油需加热温度', 0),
                'action': '开启上油箱加热'
            },
            severity=RulePriority.LOW
        )
        
        # 规则2: 油需冷却警告
        self.add_rule(
            rule_id="TEMPERATURE_COOLING_001",
            name="油需冷却警告",
            description="实际油温超过油需冷却温度，开启冷却循环泵",
            condition=lambda facts: facts.get('上油箱油温', 0) > facts.get('油需冷却温度', 0),
            action=lambda facts: {
                'rule_id': 'TEMPERATURE_COOLING_001',
                'name': '油需冷却警告',
                'severity': 'low',
                'description': f'油温需冷却: {facts.get("上油箱油温", 0):.1f}°C > {facts.get("油需冷却温度", 0):.1f}°C',
                'value': facts.get('上油箱油温', 0),
                'threshold': facts.get('油需冷却温度', 0),
                'action': '开启冷却循环泵'
            },
            severity=RulePriority.LOW
        )
        
        # 规则3: 油温过高警告
        self.add_rule(
            rule_id="TEMPERATURE_HIGH_001",
            name="油温过高警告",
            description="实际油温超过油超温温度，主电机停止运行",
            condition=lambda facts: facts.get('上油箱油温', 0) > facts.get('油超温温度', 0),
            action=lambda facts: {
                'rule_id': 'TEMPERATURE_HIGH_001',
                'name': '油温过高警告',
                'severity': 'high',
                'description': f'油温过高停机: {facts.get("上油箱油温", 0):.1f}°C > {facts.get("油超温温度", 0):.1f}°C',
                'value': facts.get('上油箱油温', 0),
                'threshold': facts.get('油超温温度', 0),
                'action': '主电机停止运行'
            },
            severity=RulePriority.HIGH
        )
        
        # 规则4: 急停触发
        self.add_rule(
            rule_id="EMERGENCY_STOP_001",
            name="急停触发",
            description="急停合格信号为1表示急停触发",
            condition=lambda facts: facts.get('急停合格', 0) == 1,
            action=lambda facts: {
                'rule_id': 'EMERGENCY_STOP_001',
                'name': '急停触发',
                'severity': 'emergency',
                'description': '急停按钮被触发，请立即检查',
                'value': facts.get('急停合格', 0)
            },
            severity=RulePriority.EMERGENCY
        )
        
        # 规则4: 移动台故障
        self.add_rule(
            rule_id="MOBILE_TABLE_001",
            name="移动台故障",
            description="左移动台故障信号为1",
            condition=lambda facts: facts.get('左移动台故障', 0) == 1,
            action=lambda facts: {
                'rule_id': 'MOBILE_TABLE_001',
                'name': '移动台故障',
                'severity': 'medium',
                'description': '左移动台检测到故障信号',
                'value': facts.get('左移动台故障', 0)
            },
            severity=RulePriority.MEDIUM
        )
        
        # 规则5: 滑块位置异常
        self.add_rule(
            rule_id="SLIDER_POSITION_001",
            name="滑块位置异常",
            description="滑块不在上限位置且在下限位",
            condition=lambda facts: (
                facts.get('滑块上限', 0) == 0 and 
                facts.get('滑块下限位', 0) == 1
            ),
            action=lambda facts: {
                'rule_id': 'SLIDER_POSITION_001',
                'name': '滑块位置异常',
                'severity': 'medium',
                'description': '滑块不在正常位置范围',
                'slider_upper': facts.get('滑块上限', 0),
                'slider_lower': facts.get('滑块下限位', 0)
            },
            severity=RulePriority.MEDIUM
        )
        
        # 规则6: 压制力异常
        self.add_rule(
            rule_id="PRESSURE_ABNORMAL_001",
            name="压制力异常",
            description="压机模式为1但压制力未达到",
            condition=lambda facts: (
                facts.get('压制力达到', 0) == 0 and 
                facts.get('压机模式', 0) == 1
            ),
            action=lambda facts: {
                'rule_id': 'PRESSURE_ABNORMAL_001',
                'name': '压制力异常',
                'severity': 'medium',
                'description': '压制过程中压制力未达到设定值',
                'pressure_reached': facts.get('压制力达到', 0),
                'press_mode': facts.get('压机模式', 0)
            },
            severity=RulePriority.MEDIUM
        )
        
        # 规则7: 驱动器故障
        self.add_rule(
            rule_id="DRIVER_FAULT_001",
            name="驱动器故障",
            description="驱动器正常信号为1表示有故障",
            condition=lambda facts: facts.get('驱动器正常', 0) == 1,
            action=lambda facts: {
                'rule_id': 'DRIVER_FAULT_001',
                'name': '驱动器故障',
                'severity': 'high',
                'description': '驱动器状态异常，请检查',
                'value': facts.get('驱动器正常', 0)
            },
            severity=RulePriority.HIGH
        )
        
        # 规则8: 系统错误
        self.add_rule(
            rule_id="SYSTEM_ERROR_001",
            name="系统错误",
            description="系统错误信号为1",
            condition=lambda facts: facts.get('系统Error', 0) == 1,
            action=lambda facts: {
                'rule_id': 'SYSTEM_ERROR_001',
                'name': '系统错误',
                'severity': 'emergency',
                'description': 'PLC检测到系统错误',
                'value': facts.get('系统Error', 0)
            },
            severity=RulePriority.EMERGENCY
        )
        
        # 新增规则：滑块下行前置条件检查 - 基于梯形图
        self.add_rule(
            rule_id="SLIDER_DOWN_PRECHECK_001",
            name="滑块下行前置条件",
            description="滑块下行但前置条件不满足",
            condition=lambda facts: (
                facts.get('滑块下行', 0) == 1 and (
                    facts.get('急停合格', 0) != 0 or
                    facts.get('安全门上升', 0) == 0 or
                    facts.get('上模夹紧', 0) == 0 or
                    facts.get('移动台原位', 0) == 0 or
                    facts.get('压机原位', 0) == 0 or
                    facts.get('滑块上限位', 0) == 0
                )
            ),
            action=lambda facts: {
                'rule_id': 'SLIDER_DOWN_PRECHECK_001',
                'name': '滑块下行前置条件不满足',
                'severity': 'high',
                'description': '滑块下行但安全条件不满足，请检查',
                'emergency_ok': facts.get('急停合格', 0),
                'safety_door': facts.get('安全门上升', 0),
                'upper_clamp': facts.get('上模夹紧', 0),
                'table_home': facts.get('移动台原位', 0),
                'press_home': facts.get('压机原位', 0),
                'slider_upper': facts.get('滑块上限位', 0)
            },
            severity=RulePriority.HIGH
        )
        
        # 新增规则：滑块不在限位但在运行
        self.add_rule(
            rule_id="SLIDER_POSITION_WARNING_001",
            name="滑块位置异常",
            description="滑块运行但不在正常位置且速度为零",
            condition=lambda facts: (
                facts.get('滑块下行', 0) == 1 and 
                facts.get('滑块上限位', 0) == 0 and 
                facts.get('滑块下限位', 0) == 0 and
                (facts.get('滑块速度', 0) == 0 or abs(facts.get('滑块速度', 0)) < 0.1)
            ),
            action=lambda facts: {
                'rule_id': 'SLIDER_POSITION_WARNING_001',
                'name': '滑块位置警告',
                'severity': 'medium',
                'description': '滑块有下行指令但不在限位且速度为零，可能卡住',
                'slider_down': facts.get('滑块下行', 0),
                'slider_upper': facts.get('滑块上限位', 0),
                'slider_lower': facts.get('滑块下限位', 0),
                'slider_speed': facts.get('滑块速度', 0)
            },
            severity=RulePriority.MEDIUM
        )
    
    def add_rule(self, rule_id: str, name: str, description: str,
                 condition: Callable[[Dict[str, Any]], bool],
                 action: Callable[[Dict[str, Any]], Dict[str, Any]],
                 severity: RulePriority = RulePriority.MEDIUM,
                 enabled: bool = True):
        """
        添加规则
        
        Args:
            rule_id: 规则ID
            name: 规则名称
            description: 规则描述
            condition: 条件函数
            action: 动作函数
            severity: 优先级
            enabled: 是否启用
        """
        rule = Rule(
            rule_id=rule_id,
            name=name,
            description=description,
            condition=condition,
            action=action,
            severity=severity,
            enabled=enabled
        )
        self.rules.append(rule)
    
    def insert_fact(self, key: str, value: Any):
        """
        插入事实
        
        Args:
            key: 事实键
            value: 事实值
        """
        self.facts[key] = value
    
    def insert_facts(self, facts: Dict[str, Any]):
        """
        批量插入事实
        
        Args:
            facts: 事实字典
        """
        self.facts.update(facts)
    
    def clear_facts(self):
        """清除所有事实"""
        self.facts.clear()
    
    def fire_all_rules(self) -> List[Dict[str, Any]]:
        """
        触发所有匹配的规则
        
        Returns:
            触发的规则结果列表
        """
        results = []
        
        # 按优先级排序规则
        sorted_rules = sorted(self.rules, key=lambda r: r.severity.value)
        
        for rule in sorted_rules:
            if not rule.enabled:
                continue
            
            try:
                if rule.condition(self.facts):
                    result = rule.action(self.facts)
                    result['severity'] = rule.severity.name.lower()
                    result['rule_id'] = rule.rule_id
                    results.append(result)
            except Exception as e:
                print(f"规则执行失败 {rule.name}: {e}")
        
        return results


def create_drools_lite_engine() -> DroolsLite:
    """
    创建Drools Lite规则引擎
    
    Returns:
        DroolsLite实例
    """
    return DroolsLite()


if __name__ == '__main__':
    print("=== Drools Lite 规则引擎测试 ===\n")
    
    engine = create_drools_lite_engine()
    
    # 测试1: 正常状态
    print("测试1: 正常状态（急停合格=0，油温=50）")
    test_facts = {
        '急停合格': 0,
        '油超温温度': 50,
        '上油加热关闭温度': 50,
        '左移动台故障': 0,
        '滑块上限': 1,
        '滑块下限位': 0,
        '压制力达到': 1,
        '压机模式': 1,
        '驱动器正常': 0,
        '系统Error': 0
    }
    engine.insert_facts(test_facts)
    results = engine.fire_all_rules()
    print(f"触发规则数: {len(results)}")
    for r in results:
        print(f"  - {r['name']}: {r['description']}")
    
    # 测试2: 急停触发
    print("\n测试2: 急停触发（急停合格=1，油温=70）")
    engine.clear_facts()
    test_facts = {
        '急停合格': 1,
        '油超温温度': 70,
        '上油加热关闭温度': 50,
        '左移动台故障': 0,
        '滑块上限': 1,
        '滑块下限位': 0,
        '压制力达到': 1,
        '压机模式': 1,
        '驱动器正常': 0,
        '系统Error': 0
    }
    engine.insert_facts(test_facts)
    results = engine.fire_all_rules()
    print(f"触发规则数: {len(results)}")
    for r in results:
        print(f"  - [{r['severity'].upper()}] {r['name']}: {r['description']}")
    
    print("\n=== 测试完成 ===")
