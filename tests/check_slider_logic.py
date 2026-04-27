"""
滑块下行前置条件不满足报错逻辑检查报告
"""
import time
from src.analysis.slider_down_detector import create_slider_detector

print("=" * 70)
print("滑块下行前置条件不满足报错逻辑检查")
print("=" * 70)

detector = create_slider_detector()

# 基础数据
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

print("\n[检查点1] 初始状态检查")
print("-" * 70)
detector.update_facts(base_facts)
result = detector.check_abnormal()
print(f"  下行指令: {'激活' if detector.down_command_active else '未激活'}")
print(f"  不满足条件数: {len(result['unsatisfied_conditions'])}")
print(f"  异常状态: {result['abnormal']}")

print("\n[检查点2] 下行指令激活，有条件不满足，速度为0 - 0秒")
print("-" * 70)
facts1 = base_facts.copy()
facts1['滑块慢下'] = 1
facts1['急停合格'] = 1
detector.update_facts(facts1)
result = detector.check_abnormal()
print(f"  下行指令: {'激活' if detector.down_command_active else '未激活'}")
print(f"  不满足条件数: {len(result['unsatisfied_conditions'])}")
print(f"  已过时间: {result['elapsed_time']:.3f}秒")
print(f"  容忍时间: {result['delay_tolerance'] + result['error_tolerance']:.1f}秒")
print(f"  异常状态: {result['abnormal']}")
print(f"  描述: {result['description']}")

print("\n[检查点3] 等待1.0秒后")
print("-" * 70)
time.sleep(1.0)
detector.update_facts(facts1)
result = detector.check_abnormal()
print(f"  已过时间: {result['elapsed_time']:.3f}秒")
print(f"  异常状态: {result['abnormal']}")
print(f"  描述: {result['description']}")

print("\n[检查点4] 等待到2.6秒后（超过容忍期）")
print("-" * 70)
target_wait = max(0, 2.7 - result['elapsed_time'])
print(f"等待 {target_wait:.2f} 秒...")
time.sleep(target_wait)
detector.update_facts(facts1)
result = detector.check_abnormal()
print(f"  已过时间: {result['elapsed_time']:.3f}秒")
print(f"  异常状态: {result['abnormal']}")
print(f"  描述: {result['description']}")

if result['abnormal']:
    print("\n  推理报告:")
    print(detector.get_abnormal_reasoning())

print("\n[检查点5] 滑块速度不为0的情况")
print("-" * 70)
facts2 = facts1.copy()
facts2['滑块速度'] = 50.0
detector.update_facts(facts2)
result = detector.check_abnormal()
print(f"  滑块速度: {facts2['滑块速度']}")
print(f"  异常状态: {result['abnormal']}")
print(f"  描述: {result['description']}")

print("\n[检查点6] 滑块速度接近0（0.05）的情况")
print("-" * 70)
facts3 = facts1.copy()
facts3['滑块速度'] = 0.05
detector.update_facts(facts3)
result = detector.check_abnormal()
print(f"  滑块速度: {facts3['滑块速度']}")
print(f"  异常状态: {result['abnormal']}")
print(f"  描述: {result['description']}")

print("\n[检查点7] 所有条件都满足的正常情况")
print("-" * 70)
facts4 = base_facts.copy()
facts4['滑块慢下'] = 1
facts4['滑块速度'] = 45.0
detector.update_facts(facts4)
result = detector.check_abnormal()
print(f"  不满足条件数: {len(result['unsatisfied_conditions'])}")
print(f"  滑块速度: {facts4['滑块速度']}")
print(f"  异常状态: {result['abnormal']}")

print("\n" + "=" * 70)
print("总结")
print("=" * 70)
print("\n当前逻辑工作流程:")
print("  1. 下行指令激活 -> 开始计时")
print("  2. 0~2.5秒 -> 容忍期内，即使条件不满足也不报警")
print("  3. >2.5秒 -> 如果条件不满足且滑块未动 -> 报警")
print("  4. 如果滑块在移动（速度>0.1） -> 即使条件不满足也不报警")
print("\n时间配置:")
print("  - 延迟容忍时间: 1.5秒")
print("  - 误差容忍时间: 1.0秒")
print("  - 总容忍时间: 2.5秒")
print("\n报警条件:")
print("  - 滑块下行指令激活")
print("  - 存在不满足的前置条件")
print("  - 滑块速度为0或<0.1")
print("  - 已过时间 > 2.5秒")
print("\n" + "=" * 70)
print("  所有逻辑检查完成")
