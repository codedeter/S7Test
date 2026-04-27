"""
简单测试滑块下行检测器
"""

from src.analysis.slider_down_detector import create_slider_detector

print("=== 滑块下行检测器简单测试 ===\n")

detector = create_slider_detector()

# 测试场景：急停按下
print("场景1: 急停按下，有下行指令")
facts1 = {
    '急停合格': 1,  # 急停按下（不满足）
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
    '滑块慢下': 1  # 下行指令
}
detector.update_facts(facts1)
result = detector.check_abnormal()
print(f"异常: {result['abnormal']}")
print(f"不满足条件数: {len(result['unsatisfied_conditions'])}")
if result['abnormal']:
    print("\n推理报告:")
    print(detector.get_abnormal_reasoning())
print()

# 测试场景：多个条件不满足
print("场景2: 多个条件不满足")
facts2 = {
    '急停合格': 1,
    '滑块上限': 1,
    '滑块下限位': 0,
    '双手合格': 0,
    '电机启动主控': 0,
    '允许下行': 1,
    '移动台合格': 1,
    '驱动器正常': 0,
    '系统Error': 0,
    '安全爪打开到位': 1,
    '安全爪主控': 1,
    '滑块慢下': 1
}
detector.update_facts(facts2)
result = detector.check_abnormal()
print(f"异常: {result['abnormal']}")
print(f"不满足条件数: {len(result['unsatisfied_conditions'])}")
if result['abnormal']:
    print("\n推理报告:")
    print(detector.get_abnormal_reasoning())
print()

print("=== 测试完成 ===")
