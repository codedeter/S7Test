"""
故障规则库管理模块
基于PLC变量表和GLABAL.db生成故障推理规则
"""

import re
from datetime import datetime
try:
    from .slider_down_detector import create_slider_detector
except ImportError:
    from src.analysis.slider_down_detector import create_slider_detector

class FaultRule:
    def __init__(self, rule_id, name, condition, conclusion, severity, description):
        self.rule_id = rule_id
        self.name = name
        self.condition = condition
        self.conclusion = conclusion
        self.severity = severity
        self.description = description

    def evaluate(self, facts):
        try:
            safe_vars = {}
            for key, value in facts.items():
                safe_key = key.replace(' ', '_').replace('.', '_').replace('(', '').replace(')', '').replace('-', '_')
                safe_vars[safe_key] = value
            
            safe_condition = self.condition
            for key in facts.keys():
                safe_key = key.replace(' ', '_').replace('.', '_').replace('(', '').replace(')', '').replace('-', '_')
                safe_condition = safe_condition.replace(key, safe_key)
            
            return eval(safe_condition, {"__builtins__": {}}, safe_vars)
        except Exception as e:
            return False

class RuleEngine:
    def __init__(self):
        self.rules = []
        self.facts = {}
        self.slider_detector = create_slider_detector()

    def add_rule(self, rule):
        self.rules.append(rule)

    def update_fact(self, key, value):
        self.facts[key] = value

    def update_facts(self, facts_dict):
        self.facts.update(facts_dict)
        # 同时更新滑块下行检测器
        self.slider_detector.update_facts(facts_dict)

    def forward_chain(self):
        triggered_rules = []
        for rule in self.rules:
            if rule.evaluate(self.facts):
                triggered_rules.append(rule)
        return triggered_rules

    def check_slider_down_abnormal(self):
        """
        检查滑块下行异常
        
        Returns:
            滑块下行异常检测结果
        """
        return self.slider_detector.check_abnormal()

    def get_slider_down_reasoning(self):
        """
        获取滑块下行异常推理报告
        
        Returns:
            推理报告字符串
        """
        return self.slider_detector.get_abnormal_reasoning()

    def clear_facts(self):
        self.facts = {}

def parse_logical_address(addr):
    if not addr or not isinstance(addr, str):
        return None, None, None

    addr = addr.strip()

    if addr.startswith('%M'):
        return 'M', int(addr[2:].split('.')[0]), int(addr.split('.')[1]) if '.' in addr else 0
    elif addr.startswith('%DB'):
        parts = addr[3:].split('.')
        db_num = int(parts[0])
        if parts[1].startswith('DBX'):
            offset = int(parts[1][3:])
            bit = int(parts[2]) if len(parts) > 2 else 0
            return 'DB', db_num, (offset, bit, 'Bool')
        elif parts[1].startswith('DBD'):
            offset = int(parts[1][3:])
            return 'DB', db_num, (offset, 'DInt')
        elif parts[1].startswith('DBW'):
            offset = int(parts[1][3:])
            return 'DB', db_num, (offset, 'Int')
        elif parts[1].startswith('DBB'):
            offset = int(parts[1][3:])
            return 'DB', db_num, (offset, 'Byte')
    elif addr.startswith('%I'):
        parts = addr[2:].split('.')
        if len(parts) == 2:
            return 'I', int(parts[0]), int(parts[1])
        return 'I', int(parts[0]), 0
    elif addr.startswith('%Q'):
        parts = addr[2:].split('.')
        if len(parts) == 2:
            return 'Q', int(parts[0]), int(parts[1])
        return 'Q', int(parts[0]), 0
    elif addr.startswith('%T'):
        return 'T', int(addr[2:]), 0
    elif addr.startswith('%C'):
        return 'C', int(addr[2:]), 0

    return None, None, None

def create_fault_rules():
    engine = RuleEngine()

    # 根据实际设备情况修正的规则
    # 重要：不要用==True/False，要用==1/==0
    # 0=正常，1=异常
    rules = [
        # ===== 滑块下行异常检测规则 =====
        FaultRule(
            "F001",
            "滑块下行异常",
            "滑块慢下 == 1 AND 滑块上限 == 1",
            "滑块下行指令发出但未移动",
            "紧急",
            "滑块下行指令激活，但滑块仍在上限位置"
        ),
        FaultRule(
            "F001_1",
            "急停阻止下行",
            "急停合格 == 1 AND 滑块慢下 == 1",
            "急停按下阻止滑块下行",
            "紧急",
            "急停按钮被触发，滑块无法下行"
        ),
        FaultRule(
            "F001_2",
            "双手不合格",
            "双手合格 == 0 AND 滑块慢下 == 1",
            "双手操作不合格阻止下行",
            "高",
            "双手操作按钮未正确触发"
        ),
        FaultRule(
            "F001_3",
            "电机未启动",
            "电机启动主控 == 0 AND 滑块慢下 == 1",
            "电机未启动阻止下行",
            "高",
            "电机主控未启动，滑块无法下行"
        ),
        FaultRule(
            "F001_4",
            "驱动器故障",
            "驱动器正常 == 1 AND 滑块慢下 == 1",
            "驱动器故障阻止下行",
            "高",
            "驱动器检测到故障信号"
        ),
        FaultRule(
            "F001_5",
            "系统错误",
            "系统Error == 1 AND 滑块慢下 == 1",
            "系统错误阻止下行",
            "紧急",
            "PLC检测到系统错误信号"
        ),
        FaultRule(
            "F001_6",
            "不允许下行",
            "允许下行 == 0 AND 滑块慢下 == 1",
            "系统不允许下行",
            "高",
            "系统未允许滑块下行"
        ),
        FaultRule(
            "F001_7",
            "移动台不合格",
            "移动台合格 == 0 AND 滑块慢下 == 1",
            "移动台位置不合格",
            "高",
            "移动台未在合格位置"
        ),
        FaultRule(
            "F001_8",
            "安全爪未打开",
            "安全爪打开到位 == 0 AND 滑块慢下 == 1",
            "安全爪未打开到位",
            "高",
            "安全爪未完全打开"
        ),
        # ===== 原有规则 =====
        FaultRule(
            "F002",
            "温度过高报警",
            "油超温温度 > 60 OR 上油加热关闭温度 > 80",
            "油温过高",
            "高",
            "液压油温度超过安全阈值"
        ),
        FaultRule(
            "F003",
            "移动台故障",
            "左移动台故障 == 1",
            "移动台异常",
            "中",
            "左移动台检测到故障信号"
        ),
        FaultRule(
            "F005",
            "急停触发",
            "急停合格 == 1",  # 0=正常，1=急停被触发
            "急停被按下",
            "紧急",
            "急停按钮被触发"
        ),
        FaultRule(
            "F006",
            "滑块位置异常",
            "滑块上限 == 0 AND 滑块下限位 == 1",
            "滑块位置异常",
            "中",
            "滑块不在正常位置范围"
        ),
        FaultRule(
            "F007",
            "压制力异常",
            "压制力达到 == 0 AND 压机模式 == 1",
            "压制力未达到设定值",
            "中",
            "压制过程中压制力未达到"
        ),
        FaultRule(
            "F008",
            "通信故障",
            "驱动器正常 == 1",  # 0=正常，1=故障
            "驱动器通信异常",
            "高",
            "驱动器状态异常"
        ),
        FaultRule(
            "F009",
            "系统错误",
            "系统Error == 1",
            "系统错误",
            "紧急",
            "PLC检测到系统错误"
        ),
    ]

    for rule in rules:
        engine.add_rule(rule)

    return engine

def create_rules_from_excel(excel_data):
    engine = RuleEngine()

    for idx, row in enumerate(excel_data):
        if not row or len(row) < 5:
            continue

        name = row[0]
        addr = row[3]
        comment = row[4] if len(row) > 4 else ""

        if not name or not addr:
            continue

        area, num, detail = parse_logical_address(str(addr))
        if area is None:
            continue

        rule = FaultRule(
            f"R{idx+1:03d}",
            name,
            f"{name} == True",
            f"{name}触发",
            "中",
            comment
        )
        engine.add_rule(rule)

    return engine

def format_fault_report(triggered_rules, facts, slider_reasoning=None):
    report = []
    report.append("=" * 60)
    report.append("故障分析报告")
    report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 60)

    # 滑块下行异常推理
    if slider_reasoning:
        report.append("\n【滑块下行异常分析】")
        report.append(slider_reasoning)
        report.append("\n" + "=" * 60)

    if not triggered_rules:
        report.append("\n未检测到其他故障")
    else:
        report.append(f"\n【其他故障检测】")
        report.append(f"检测到 {len(triggered_rules)} 个故障:")
        for rule in triggered_rules:
            report.append(f"\n[{rule.severity}] {rule.rule_id} - {rule.name}")
            report.append(f"  描述: {rule.description}")
            report.append(f"  结论: {rule.conclusion}")

    return "\n".join(report)
