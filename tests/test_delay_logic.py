"""
测试滑块下行检测的延时逻辑
"""
import time
from src.analysis.slider_down_detector import create_slider_detector

print("=== 滑块下行检测延时逻辑测试 ===\n")

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

print("测试1: 初始状态 - 无下行指令")
print("-" * 50)
detector.update_facts(base_facts)
result = detector.check_abnormal()
print(f"异常: {result['abnormal']}")
print()

print("测试2: 下行指令刚发出，有条件不满足，速度为0 - 在容忍期内不报警")
print("-" * 50)
facts2 = base_facts.copy()
facts2['滑块慢下'] = 1
facts2['急停合格'] = 1
facts2['滑块速度'] = 0
detector.update_facts(facts2)
result = detector.check_abnormal()
print(f"异常: {result['abnormal']}")
print(f"描述: {result['description']}")
print(f"已过时间: {result['elapsed_time']:.3f}秒")
print()

print("测试3: 等待1秒后 - 仍在容忍期内不报警")
print("-" * 50)
time.sleep(1.0)
detector.update_facts(facts2)
result = detector.check_abnormal()
print(f"异常: {result['abnormal']}")
print(f"描述: {result['description']}")
print(f"已过时间: {result['elapsed_time']:.3f}秒")
print()

print("测试4: 等待到超过2.5秒后 - 超过容忍期应该报警")
print("-" * 50)
target_sleep = max(0, 2.6 - result['elapsed_time'])
print(f"等待{target_sleep:.2f}秒...")
time.sleep(target_sleep)
detector.update_facts(facts2)
result = detector.check_abnormal()
print(f"异常: {result['abnormal']}")
print(f"描述: {result['description']}")
print(f"已过时间: {result['elapsed_time']:.3f}秒")
print(f"不满足条件数: {len(result['unsatisfied_conditions'])}")
if result['abnormal']:
    print("\n推理报告:")
    print(detector.get_abnormal_reasoning())
print()

print("测试5: 滑块开始移动，有速度 - 不应该报警")
print("-" * 50)
facts3 = facts2.copy()
facts3['滑块速度'] = 45.5
detector.update_facts(facts3)
result = detector.check_abnormal()
print(f"异常: {result['abnormal']}")
print(f"描述: {result['description']}")
print(f"已过时间: {result['elapsed_time']:.3f}秒")
print()

print("测试6: 重新测试 - 关闭下行指令，再打开")
print("-" * 50)
# 先关闭
facts_stop = base_facts.copy()
facts_stop['滑块慢下'] = 0
detector.update_facts(facts_stop)
result = detector.check_abnormal()
print(f"关闭后 - 异常: {result['abnormal']}")
print(f"已过时间: {result['elapsed_time']:.3f}秒")

time.sleep(0.5)

# 再次打开
facts_restart = facts2.copy()
facts_restart['滑块慢下'] = 1
detector.update_facts(facts_restart)
result = detector.check_abnormal()
print(f"重新打开后 - 异常: {result['abnormal']}")
print(f"描述: {result['description']}")
print(f"已过时间: {result['elapsed_time']:.3f}秒")
print()

print("\n=== 测试完成 ===")
print("\n总结:")
print("- 下行指令发出后有1.5秒延时容忍 + 1秒误差容忍 = 总2.5秒")
print("- 在容忍期内即使条件不满足也不报警")
print("- 超过2.5秒且滑块未移动时才报警")
print("- 如果滑块在移动，即使条件不满足也不报警")
