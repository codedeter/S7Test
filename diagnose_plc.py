
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PLC连接诊断工具 - 测试各种连接参数
"""
import sys
import os
import time
import socket
from typing import Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.devices_config import create_device_configs

try:
    import snap7
except ImportError:
    print("snap7 未安装，请先安装 snap7")
    sys.exit(1)


def test_tcp_port(ip: str, port: int, timeout: int = 2) -> Tuple[bool, float]:
    """测试 TCP 端口是否可达"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        start_time = time.time()
        result = sock.connect_ex((ip, port))
        elapsed = (time.time() - start_time) * 1000
        sock.close()
        return (result == 0), elapsed
    except Exception as e:
        return False, 0


def test_snap7_connect(ip: str, rack: int, slot: int, connection_type: int = 3, timeout: int = 5) -> Tuple[bool, str]:
    """测试 snap7 连接"""
    try:
        client = snap7.client.Client()
        client.set_connection_type(connection_type)
        client.set_param(16, timeout)
        
        start_time = time.time()
        client.connect(ip, rack, slot)
        
        if client.get_connected():
            elapsed = (time.time() - start_time) * 1000
            client.disconnect()
            return True, f"成功 (耗时: {elapsed:.1f}ms)"
        else:
            client.disconnect()
            return False, "连接失败 (未成功建立)"
    except Exception as e:
        return False, str(e)


def main():
    print("="*70)
    print("PLC连接诊断工具")
    print("="*70)
    
    device_configs = create_device_configs()
    
    # 测试参数组合
    connection_types = [1, 2, 3]  # 不同的连接类型
    rack_slots = [(0, 1), (0, 0), (0, 2), (1, 0)]
    
    for cfg in device_configs:
        print("\n" + "-"*70)
        print(f"设备: {cfg.device_id} ({cfg.device_name})")
        print(f"IP: {cfg.ip_address}")
        print("-"*70)
        
        # 测试 TCP 102 端口
        print("\n1. 测试 S7 协议端口 (TCP 102):")
        tcp_ok, tcp_time = test_tcp_port(cfg.ip_address, 102)
        if tcp_ok:
            print(f"   [OK] 端口 102 可达 (响应: {tcp_time:.1f}ms)")
        else:
            print(f"   [FAIL] 端口 102 不可达")
            continue  # 如果端口不可达，继续下一个设备
        
        # 测试各种连接参数组合
        print("\n2. 尝试不同的连接参数组合:")
        found = False
        for conn_type in connection_types:
            for rack, slot in rack_slots:
                print(f"   尝试: Type={conn_type}, Rack={rack}, Slot={slot}...", end="")
                ok, msg = test_snap7_connect(cfg.ip_address, rack, slot, conn_type)
                if ok:
                    print(f" [OK] {msg}")
                    found = True
                    # 记录成功的配置
                    print(f"      > 推荐配置: Rack={rack}, Slot={slot}, Type={conn_type}")
                    break
                else:
                    print(f" [FAIL] {msg}")
            if found:
                break
        
        if not found:
            print("\n   [WARNING] 未能建立连接，请检查:")
            print("   - 网络是否可达")
            print("   - PLC 是否运行")
            print("   - 是否需要安全连接")
            print("   - 防火墙设置")
    
    print("\n" + "="*70)
    print("诊断完成")
    print("="*70)


if __name__ == "__main__":
    main()
