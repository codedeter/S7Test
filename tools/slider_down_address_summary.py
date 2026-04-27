"""
滑块下行指令地址总结
"""
print("=" * 70)
print("滑块下行指令地址与变量信息")
print("=" * 70)

print("\n[核心信息]")
print("-" * 70)
print("  地址: DB1.DBX3.1")
print("  变量名: 滑块下行")
print("  数据类型: Bool")
print("  说明: 这是滑块下行的主要控制信号")

print("\n[相关辅助信号]")
print("-" * 70)
related_signals = [
    ('滑块慢下', 'DB1.DBX8.1', '滑块慢下信号'),
    ('3Y1', 'DB1.DBX8.7', '3Y1阀控制信号'),
    ('打开充液阀', 'DB1.DBX7.5', '充液阀打开信号'),
    ('下行主控', 'DB1.DBX2.3', '下行主控信号'),
    ('滑块下行前条件检查', 'DB1.DBX2.4', '下行前条件检查'),
]

for name, addr, desc in related_signals:
    print(f"  {name} ({addr})")
    print(f"    - {desc}")

print("\n[自动模式相关变量]")
print("-" * 70)
auto_mode_vars = [
    ('压机模式', 'DB1.DBW32', '工作模式 (Int类型)'),
    ('左模具有料', 'DB1.DBX16.6', '左模具内有板料'),
    ('左模具无料', 'DB1.DBX16.7', '左模具内无板料'),
    ('右模具有料', 'DB1.DBX17.0', '右模具内有板料'),
    ('右模具无料', 'DB1.DBX17.1', '右模具内无板料'),
]

for name, addr, desc in auto_mode_vars:
    print(f"  {name} ({addr})")
    print(f"    - {desc}")

print("\n[自动模式下下行逻辑推测]")
print("-" * 70)
print("  在自动模式下，滑块下行条件可能包括:")
print("    1. 压机模式 = 自动模式 (需要确认具体数值)")
print("    2. 左模具有料 OR 右模具有料 (至少一个模具内有板料)")
print("    3. 压机自动启动信号 (需要找到对应变量)")
print("    4. 其他安全条件 (急停、安全门等)")
print("    5. 滑块在上限位置")

print("\n[建议]")
print("-" * 70)
print("  1. 监控正常自动运行过程，记录:")
print("     - 压机模式的实际值")
print("     - 下行指令发出时的条件组合")
print("     - 板料检测信号的状态")
print("  2. 分析PLC程序梯形图，确认:")
print("     - 自动模式的具体数值")
print("     - 下行指令的完整触发条件")
print("  3. 记录异常场景，用于逻辑验证")

print("\n" + "=" * 70)
