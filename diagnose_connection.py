#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断服务器启动时的PLC连接问题
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.devices.device_manager import DeviceManager, PLCClient
from src.devices.device_config import DeviceConfig, DeviceType
from config.devices_config import create_device_configs, DEFAULT_DEVICES

def test_full_connection_flow():
    """测试完整的连接流程，模拟服务器启动"""
    print("=" * 60)
    print("测试完整连接流程")
    print("=" * 60)
    
    # 创建设备管理器
    print("\n1. 创建设备管理器...")
    device_manager = DeviceManager()
    
    # 添加所有设备配置
    print("\n2. 添加设备配置...")
    device_configs = create_device_configs()
    for config in device_configs:
        device_manager.add_device(config)
        print("   Added device: {} ({})".format(config.device_id, config.device_name))
    
    print(f"\n   共添加 {len(device_configs)} 个设备")
    
    # 测试连接所有设备
    print("\n3. 测试连接所有设备...")
    start_time = time.time()
    results = device_manager.connect_all()
    elapsed_time = time.time() - start_time
    
    print(f"   连接耗时: {elapsed_time:.2f}秒")
    print("\n   连接结果:")
    for device_id, success in results.items():
        status = "成功" if success else "失败"
        prefix = "OK" if success else "FAIL"
        print("   {} {}: {}".format(prefix, device_id, status))
    
    # 检查设备状态
    print("\n4. 检查设备状态...")
    for device_id in device_manager.devices:
        status = device_manager.get_device_status(device_id)
        print(f"   {device_id}: {status.status.value}")
        
        if status.connected:
            # 尝试读取数据
            try:
                collector = device_manager.collectors.get(device_id)
                if collector:
                    data = collector.collect_all_data()
                    print(f"      数据点数: {len(data)}")
            except Exception as e:
                print(f"      读取数据失败: {e}")
    
    # 显示连接池状态
    print("\n5. 连接池状态:")
    pool_summary = device_manager._connection_pool.get_pool_summary()
    print(f"   总设备: {pool_summary['total_devices']}")
    print(f"   已连接: {pool_summary['connected']}")
    print(f"   连接中: {pool_summary['connecting']}")
    print(f"   重连中: {pool_summary['reconnecting']}")
    print(f"   断开: {pool_summary['disconnected']}")

def test_single_device_from_config():
    """测试从配置创建的设备连接"""
    print("\n" + "=" * 60)
    print("测试从配置创建的设备连接")
    print("=" * 60)
    
    # 获取第一个设备配置
    device_def = DEFAULT_DEVICES[0]
    print(f"\n设备: {device_def['device_name']}")
    print(f"IP: {device_def['ip_address']}")
    
    # 创建配置对象
    config = DeviceConfig(
        device_id=device_def['device_id'],
        device_name=device_def['device_name'],
        device_type=device_def['device_type'],
        ip_address=device_def['ip_address'],
        rack=device_def.get('rack', 0),
        slot=device_def.get('slot', 1),
        enabled=True
    )
    
    # 创建客户端并连接
    client = PLCClient(config)
    print(f"\n连接到 {config.ip_address}...")
    result = client.connect()
    print(f"连接结果: {'成功' if result else '失败'}")
    
    if result:
        print("读取DB1数据...")
        data = client.read_db(1, 0, 20)
        if data:
            print(f"成功读取 {len(data)} 字节")
            print(f"数据: {list(data[:10])}...")
        client.disconnect()

if __name__ == "__main__":
    # 测试单个设备
    test_single_device_from_config()
    
    # 测试完整流程
    test_full_connection_flow()