#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PLC连接状态诊断工具
检测所有配置的PLC设备连接状态，分析连接失败原因
"""
import os
import sys
import time
import socket
import subprocess
from typing import Dict, List, Tuple

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.devices_config import DEFAULT_DEVICES
from src.devices.device_manager import PLCClient
from src.devices.device_config import DeviceConfig, DeviceType


def ping_host(ip_address: str, timeout: int = 2) -> Tuple[bool, float]:
    """
    测试网络可达性
    """
    try:
        start_time = time.time()
        result = subprocess.run(
            ['ping', '-n', '1', '-w', str(timeout * 1000), ip_address],
            capture_output=True,
            timeout=timeout + 1,
            text=True
        )
        latency = (time.time() - start_time) * 1000
        return (result.returncode == 0, latency)
    except subprocess.TimeoutExpired:
        return (False, 0.0)
    except Exception as e:
        print(f"Ping error for {ip_address}: {e}")
        return (False, 0.0)


def check_port_open(ip_address: str, port: int = 102, timeout: int = 2) -> bool:
    """
    检查指定端口是否开放（S7协议默认端口102）
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip_address, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"Port check error for {ip_address}:{port}: {e}")
        return False


def diagnose_plc_connection(device_config: Dict) -> Dict:
    """
    诊断单个PLC设备的连接状态
    """
    device_id = device_config['device_id']
    device_name = device_config['device_name']
    ip_address = device_config['ip_address']
    rack = device_config.get('rack', 0)
    slot = device_config.get('slot', 1)
    
    result = {
        'device_id': device_id,
        'device_name': device_name,
        'ip_address': ip_address,
        'rack': rack,
        'slot': slot,
        'ping_reachable': False,
        'ping_latency_ms': 0.0,
        'port_102_open': False,
        'plc_connected': False,
        'connection_error': None,
        'diagnosis': []
    }
    
    print("\n" + "="*60)
    print("正在诊断设备: %s - %s" % (device_id, device_name))
    print("IP地址: %s, Rack: %d, Slot: %d" % (ip_address, rack, slot))
    print('-' * 60)
    
    # 1. 网络可达性测试
    print("步骤1: 测试网络可达性 (Ping)...")
    reachable, latency = ping_host(ip_address)
    result['ping_reachable'] = reachable
    result['ping_latency_ms'] = latency
    
    if reachable:
        print("   OK Ping成功，延迟: %.2f ms" % latency)
        result['diagnosis'].append("网络可达性正常")
    else:
        print("   FAIL Ping失败 - 目标主机不可达")
        result['diagnosis'].append("网络不可达 - 请检查网络连接或防火墙设置")
    
    # 2. 端口检查
    print("步骤2: 检查S7端口(102)...")
    port_open = check_port_open(ip_address, 102)
    result['port_102_open'] = port_open
    
    if port_open:
        print("   OK 端口102开放")
        result['diagnosis'].append("S7端口(102)开放")
    else:
        print("   FAIL 端口102关闭或被防火墙阻止")
        result['diagnosis'].append("S7端口(102)未开放 - 可能被防火墙阻止或PLC未启用S7通信")
    
    # 3. PLC连接测试（仅当网络可达时）
    if reachable and port_open:
        print("步骤3: 尝试建立PLC连接...")
        try:
            config = DeviceConfig(
                device_id=device_id,
                device_name=device_name,
                device_type=device_config['device_type'],
                ip_address=ip_address,
                rack=rack,
                slot=slot,
                enabled=True
            )
            
            client = PLCClient(config)
            start_time = time.time()
            connected = client.connect()
            latency = (time.time() - start_time) * 1000
            
            result['plc_connected'] = connected
            
            if connected:
                print("   OK PLC连接成功，耗时: %.2f ms" % latency)
                result['diagnosis'].append("PLC连接成功，Rack=%d, Slot=%d" % (rack, slot))
                client.disconnect()
            else:
                error = client.get_last_error()
                result['connection_error'] = error
                print("   FAIL PLC连接失败: %s" % error)
                
                # 分析错误原因
                if error:
                    if "timeout" in error.lower():
                        result['diagnosis'].append("连接超时 - 可能是Rack/Slot配置错误或PLC负载过高")
                    elif "refused" in error.lower():
                        result['diagnosis'].append("连接被拒绝 - PLC可能未配置S7通信或资源不足")
                    elif "invalid" in error.lower():
                        result['diagnosis'].append("无效参数 - 请检查Rack和Slot配置")
                    else:
                        result['diagnosis'].append("未知错误: %s" % error)
                else:
                    result['diagnosis'].append("连接失败但无具体错误信息")
                    
        except Exception as e:
            result['connection_error'] = str(e)
            print("   FAIL PLC连接异常: %s" % e)
            result['diagnosis'].append("连接异常: %s" % e)
    
    return result


def generate_report(results: List[Dict]):
    """
    生成诊断报告
    """
    print("\n" + "="*80)
    print("PLC连接状态诊断报告")
    print("="*80)
    
    connected_count = sum(1 for r in results if r['plc_connected'])
    reachable_count = sum(1 for r in results if r['ping_reachable'])
    port_open_count = sum(1 for r in results if r['port_102_open'])
    
    print("\n诊断摘要:")
    print("  设备总数: %d" % len(results))
    print("  网络可达: %d/%d" % (reachable_count, len(results)))
    print("  端口开放: %d/%d" % (port_open_count, len(results)))
    print("  PLC连接成功: %d/%d" % (connected_count, len(results)))
    
    print("\n详细状态:")
    print("-" * 80)
    print("%-15s %-15s %-15s %-6s %-6s %-10s %s" % ("设备ID", "设备名称", "IP地址", "Ping", "端口", "PLC连接", "诊断"))
    print("-" * 80)
    
    for r in results:
        ping_status = "OK" if r['ping_reachable'] else "FAIL"
        port_status = "OK" if r['port_102_open'] else "FAIL"
        plc_status = "成功" if r['plc_connected'] else "失败"
        
        print("%-15s %-15s %-15s %-6s %-6s %-10s %s" % (
            r['device_id'], 
            r['device_name'][:15], 
            r['ip_address'], 
            ping_status, 
            port_status, 
            plc_status, 
            ", ".join(r['diagnosis'][:2])
        ))
    
    # 失败设备详细分析
    failed_devices = [r for r in results if not r['plc_connected']]
    if failed_devices:
        print("\n连接失败设备详细分析:")
        print("-" * 80)
        for r in failed_devices:
            print("\n设备: %s - %s" % (r['device_id'], r['device_name']))
            print("  IP地址: %s" % r['ip_address'])
            print("  Rack/Slot: %d/%d" % (r['rack'], r['slot']))
            print("  网络可达: %s" % ("是" if r['ping_reachable'] else "否"))
            print("  端口102: %s" % ("开放" if r['port_102_open'] else "关闭"))
            print("  连接错误: %s" % r['connection_error'])
            print("  诊断建议:")
            for diag in r['diagnosis']:
                print("    - %s" % diag)


def main():
    """
    主函数
    """
    print("PLC连接状态诊断工具")
    print("正在加载设备配置...")
    
    devices = DEFAULT_DEVICES
    
    if not devices:
        print("错误: 未找到任何设备配置")
        return
    
    print("找到 %d 个PLC设备配置" % len(devices))
    
    results = []
    for device in devices:
        result = diagnose_plc_connection(device)
        results.append(result)
    
    generate_report(results)


if __name__ == "__main__":
    main()
