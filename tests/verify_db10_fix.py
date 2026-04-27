#!/usr/bin/env python3
"""
验证 DB10 数据修复后的解析
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))
from src.plc.plc_data_collector import create_data_collector

def verify_db10():
    print("初始化 PLC 数据采集器...")
    collector = create_data_collector()
    
    print("连接 PLC...")
    if not collector.plc.connected:
        collector.plc.connect()
    
    if not collector.plc.connected:
        print("PLC 连接失败")
        return
    
    print("PLC 连接成功")
    print()
    print("收集数据...")
    data = collector.collect_all_data()
    
    print("共收集 %d 个数据点" % len(data))
    print()
    
    # 查找关键变量
    print("关键变量解析结果:")
    print("-" * 60)
    
    targets = [
        '2M1实时电机速度',
        '2M2实时电机速度', 
        '油温传感器',
        '水温传感器',
        '滑块总压力T',
        '滑块实际位移',
        '滑块速度'
    ]
    
    for target in targets:
        found = [d for d in data if d.get('tag_name') == target]
        if found:
            val = found[0].get('value')
            print("%s: %s" % (target, val))
    
    print()
    print("所有 DB10 变量:")
    db10_data = [d for d in data if d.get('db_number') == 10]
    for d in db10_data:
        print("  %s: %s" % (d.get('tag_name'), d.get('value')))

if __name__ == '__main__':
    verify_db10()
