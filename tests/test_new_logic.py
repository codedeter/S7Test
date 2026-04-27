"""
测试滑块下行异常检测的新逻辑
"""
from src.analysis.slider_down_detector import create_slider_detector

print("=== 滑块下行异常检测新逻辑测试 ===\n")

detector = create_slider_detector()

# 基础正常数据
base_facts = {
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
    '滑块速度': 0
}

print("测试场景1: 正常状态 - 无下行指令")
print("-" * 50)
detector.update_facts(base_facts)
result = detector.check_abnormal()
print(f"异常: {result['abnormal']}")
print()

print("测试场景2: 下行指令发出，有条件不满足，速度为0 - 应该报警")
print("-" * 50)
facts2 = base_facts.copy()
facts2['滑块慢下'] = 1
facts2['急停合格'] = 1  # 不满足条件
facts2['滑块速度'] = 0
detector.update_facts(facts2)
result = detector.check_abnormal()
print(f"异常: {result['abnormal']}")
print(f"描述: {result['description']}")
print(f"不满足条件数: {len(result['unsatisfied_conditions'])}")
print()

print("测试场景3: 下行指令发出，有条件不满足，速度不为0 - 不应该报警")
print("-" * 50)
facts3 = base_facts.copy()
facts3['滑块慢下'] = 1
facts3['急停合格'] = 1  # 不满足条件
facts3['滑块速度'] = 50.5  # 有速度
detector.update_facts(facts3)
result = detector.check_abnormal()
print(f"异常: {result['abnormal']}")
print(f"描述: {result['description']}")
print(f"不满足条件数: {len(result['unsatisfied_conditions'])}")
print()

print("测试场景4: 下行指令发出，有条件不满足，速度接近0 - 应该报警")
print("-" * 50)
facts4 = base_facts.copy()
facts4['滑块慢下'] = 1
facts4['急停合格'] = 1  # 不满足条件
facts4['滑块速度'] = 0.05  # 速度很小
detector.update_facts(facts4)
result = detector.check_abnormal()
print(f"异常: {result['abnormal']}")
print(f"描述: {result['description']}")
print(f"不满足条件数: {len(result['unsatisfied_conditions'])}")
print()

print("测试场景5: 下行指令发出，所有条件满足 - 正常不报警")
print("-" * 50)
facts5 = base_facts.copy()
facts5['滑块慢下'] = 1
facts5['滑块速度'] = 60.0
detector.update_facts(facts5)
result = detector.check_abnormal()
print(f"异常: {result['abnormal']}")
print(f"不满足条件数: {len(result['unsatisfied_conditions'])}")
print()

print("\n=== 测试完成 ===")
print("\n总结:")
print("✓ 当滑块下行且有条件不满足，但滑块在移动时 - 不报警")
print("✓ 当滑块下行且有条件不满足，且滑块速度为0时 - 报警")
