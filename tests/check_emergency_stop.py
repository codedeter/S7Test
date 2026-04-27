"""
检查急停相关变量的实际值
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from src.plc.plc_data_collector import create_data_collector

print("="*70)
print("检查急停相关变量")
print("="*70)

collector = create_data_collector()
collector.plc.connect()
data = collector.collect_all_data()

# 创建值映射
value_map = {}
for item in data:
    tag_name = item.get('tag_name')
    if tag_name:
        value_map[tag_name] = item.get('value')

print(f"\n采集到 {len(value_map)} 个变量")

# 查找急停相关变量
print("\n" + "="*70)
print("急停相关变量:")
print("="*70)

for tag_name in sorted(value_map.keys()):
    if "急停" in tag_name or "stop" in tag_name.lower():
        value = value_map[tag_name]
        print(f"\n{tag_name}:")
        print(f"  值: {value}")
        print(f"  类型: {type(value)}")
        print(f"  == True? {value == True}")
        print(f"  == False? {value == False}")
        print(f"  is True? {value is True}")
        print(f"  is False? {value is False}")
        print(f"  1? {value == 1}")
        print(f"  0? {value == 0}")

print("\n" + "="*70)
print("所有布尔值变量:")
print("="*70)
for tag_name in sorted(value_map.keys()):
    value = value_map[tag_name]
    if isinstance(value, (int, bool)) and value in [0, 1, True, False]:
        print(f"{tag_name}: {value} (type: {type(value)})")
