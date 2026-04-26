"""
滑块下行异常检测测试
验证新增的滑块下行异常推理功能
"""

import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from analysis.fault_engine import create_fault_rules, format_fault_report
from analysis.slider_down_detector import create_slider_detector


def test_slider_down_abnormal():
    """测试滑块下行异常检测"""
    print("=" * 70)
    print("滑块下行异常检测测试")
    print("=" * 70)
    
    # 创建规则引擎
    engine = create_fault_rules()
    
    print("\n" + "-" * 70)
    print("测试1: 正常状态 - 所有条件满足，无下行指令")
    print("-" * 70)
    normal_facts = {
        '急停合格': 0,
        '滑块上限': 1,
        '滑块下限位': 0,
        '双手合格': 1,
        '电机启动主控': 1,
        '允许下行': 1,
        '移动台合格': 1,
        '驱动器正常': 0,
        '系统Error': 0,
        '安全爪打开到位': 1,
        '安全爪主控': 1,
        '滑块慢下': 0,
        '油超温温度': 50,
        '上油加热关闭温度': 50,
        '左移动台故障': 0,
        '压制力达到': 0,
        '压机模式': 0
    }
    engine.update_facts(normal_facts)
    triggered = engine.forward_chain()
    slider_result = engine.check_slider_down_abnormal()
    slider_reasoning = engine.get_slider_down_reasoning()
    
    print(f"触发规则数: {len(triggered)}")
    print(f"滑块异常: {slider_result['abnormal']}")
    if slider_result['abnormal']:
        print(slider_reasoning)
    else:
        print("状态正常")
    
    print("\n" + "-" * 70)
    print("测试2: 急停按下 - 下行指令发出但急停阻止")
    print("-" * 70)
    emergency_facts = normal_facts.copy()
    emergency_facts['急停合格'] = 1  # 急停按下
    emergency_facts['滑块慢下'] = 1  # 下行指令
    engine.update_facts(emergency_facts)
    triggered = engine.forward_chain()
    slider_result = engine.check_slider_down_abnormal()
    slider_reasoning = engine.get_slider_down_reasoning()
    
    print(f"触发规则数: {len(triggered)}")
    print(f"滑块异常: {slider_result['abnormal']}")
    for rule in triggered:
        print(f"  - [{rule.severity}] {rule.rule_id}: {rule.name}")
    print("\n故障报告:")
    print(format_fault_report(triggered, emergency_facts, slider_reasoning))
    
    print("\n" + "-" * 70)
    print("测试3: 多个条件不满足 - 急停+双手+电机")
    print("-" * 70)
    multi_fault_facts = normal_facts.copy()
    multi_fault_facts['急停合格'] = 1
    multi_fault_facts['双手合格'] = 0
    multi_fault_facts['电机启动主控'] = 0
    multi_fault_facts['滑块慢下'] = 1
    engine.update_facts(multi_fault_facts)
    triggered = engine.forward_chain()
    slider_result = engine.check_slider_down_abnormal()
    slider_reasoning = engine.get_slider_down_reasoning()
    
    print(f"触发规则数: {len(triggered)}")
    print(f"滑块异常: {slider_result['abnormal']}")
    print(f"不满足条件数: {len(slider_result['unsatisfied_conditions'])}")
    print("\n详细推理:")
    print(slider_reasoning)
    
    print("\n" + "-" * 70)
    print("测试4: 系统错误阻止下行")
    print("-" * 70)
    system_error_facts = normal_facts.copy()
    system_error_facts['系统Error'] = 1
    system_error_facts['滑块慢下'] = 1
    engine.update_facts(system_error_facts)
    triggered = engine.forward_chain()
    slider_reasoning = engine.get_slider_down_reasoning()
    
    print(f"触发规则数: {len(triggered)}")
    print("\n故障报告:")
    print(format_fault_report(triggered, system_error_facts, slider_reasoning))
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)


def test_slider_detector_direct():
    """直接测试滑块检测器"""
    print("\n" + "=" * 70)
    print("直接测试滑块检测器")
    print("=" * 70)
    
    detector = create_slider_detector()
    
    print("\n测试: 驱动器故障情况")
    facts = {
        '急停合格': 0,
        '滑块上限': 1,
        '滑块下限位': 0,
        '双手合格': 1,
        '电机启动主控': 1,
        '允许下行': 1,
        '移动台合格': 1,
        '驱动器正常': 1,  # 驱动器故障
        '系统Error': 0,
        '安全爪打开到位': 1,
        '安全爪主控': 1,
        '滑块慢下': 1
    }
    detector.update_facts(facts)
    result = detector.check_abnormal()
    print(f"异常: {result['abnormal']}")
    print(f"推理报告:")
    print(detector.get_abnormal_reasoning())


if __name__ == '__main__':
    test_slider_down_abnormal()
    test_slider_detector_direct()
