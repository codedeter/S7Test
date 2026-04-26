"""
测试驱动器正常变量
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from src.analysis.plc_variable_loader import load_plc_tags
from src.plc.plc_client import PLCClient
from src.plc.plc_data_collector import create_data_collector

# 加载变量表
loader = load_plc_tags()
print("="*60)
print("PLC变量表加载成功")
print(f"总变量数: {len(loader.variables)}")
print("="*60)

# 查找驱动器正常变量
print("\n查找驱动器相关变量:")
for name, var in loader.variables.items():
    if '驱动器' in name or 'driver' in name.lower():
        print(f"\n变量名: {name}")
        print(f"逻辑地址: {var.get('logical_address')}")
        print(f"数据类型: {var.get('data_type')}")
        print(f"注释: {var.get('comment')}")

print("\n" + "="*60)
print("当前采集的变量数据:")
collector = create_data_collector()
collector.plc.connect()
data = collector.collect_all_data()
print(f"采集到 {len(data)} 个变量")

print("\n查找与驱动器相关的实际采集数据:")
found = False
for item in data:
    tag_name = item.get('tag_name')
    if tag_name and ('驱动器' in tag_name or 'driver' in tag_name.lower()):
        print(f"\n变量名: {tag_name}")
        print(f"DB号: {item.get('db_number')}")
        print(f"地址: {item.get('address')}")
        print(f"值: {item.get('value')}")
        found = True

if not found:
    print("\n没有找到驱动器相关变量！")
    print("检查所有采集的变量名:")
    for item in data[:20]:
        print(f"  - {item.get('tag_name')}")
