"""
检查规则中使用的变量的实际值
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from src.analysis.plc_variable_loader import load_plc_tags
from src.plc.plc_data_collector import create_data_collector

# 规则中使用的变量
rule_vars = [
    "润滑泵运行", "开机润滑完成", "油超温温度", "上油加热关闭温度",
    "左移动台故障", "右移动台故障", "左安全门上升", "右安全门上升",
    "急停合格", "滑块上限", "滑块下限位", "压制力达到", "压机模式",
    "驱动器正常", "系统Error", "上模夹紧", "合模位"
]

print("======================================================================")
print("检查规则使用的变量当前值")
print("======================================================================")

# 加载变量表和采集数据
loader = load_plc_tags()
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

print("\n======================================================================")
print("规则变量检查结果:")
print("======================================================================")

for var_name in rule_vars:
    found = var_name in value_map
    value = value_map.get(var_name, "Not found")
    print(f"\n变量名: {var_name}")
    print(f"  状态: {'Collected' if found else 'Not collected'}")
    print(f"  当前值: {value}")
    
    # 查找变量详细信息
    if var_name in loader.variables:
        var_info = loader.variables[var_name]
        print(f"  地址: {var_info.get('logical_address')}")
        print(f"  注释: {var_info.get('comment')}")

print("\n======================================================================")
print("当前所有可能的布尔值变量前50个:")
print("======================================================================")
count = 0
for tag_name, value in value_map.items():
    if isinstance(value, (int, bool)) and value in [0, 1, True, False]:
        print(f"{tag_name}: {value}")
        count += 1
        if count >= 50:
            break
