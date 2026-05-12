
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PLC Network Diagnostic Tool
"""
import sys
import os
import socket
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.devices_config import create_device_configs

def test_tcp_connect(ip, port, timeout=2):
    """Test TCP connection to a host:port"""
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        start = time.time()
        result = sock.connect_ex((ip, port))
        duration = (time.time() - start) * 1000
        if result == 0:
            return True, duration
        else:
            return False, duration
    except Exception as e:
        return False, 0
    finally:
        if sock:
            sock.close()

def test_ping(ip, count=3, timeout=1):
    """Simple ping test using ICMP (Windows)"""
    import platform
    import subprocess
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, str(count), '-w', str(timeout*1000), ip]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        return result.returncode == 0, result.stdout
    except Exception as e:
        return False, str(e)

def main():
    print('='*60)
    print('PLC Network Diagnostic Tool')
    print('='*60)
    
    device_configs = create_device_configs()
    
    print(f'\nDevices to test: {len(device_configs)}')
    print(f'PLC S7 Protocol Port: 102')
    print('-'*60)
    
    for cfg in device_configs:
        print(f'\n{cfg.device_id} ({cfg.device_name}):')
        print(f'  IP Address: {cfg.ip_address}')
        print(f'  Rack/Slot: {cfg.rack}/{cfg.slot}')
        
        # Test Ping
        print(f'\n  1. Testing ICMP ping...')
        ping_ok, ping_output = test_ping(cfg.ip_address)
        print(f'     Ping: {"[OK]" if ping_ok else "[FAIL]"}')
        
        # Test TCP 102
        print(f'\n  2. Testing TCP port 102 (S7 Protocol)...')
        tcp_ok, tcp_time = test_tcp_connect(cfg.ip_address, 102)
        print(f'     TCP: {"[OK]" if tcp_ok else "[FAIL]"}')
        if tcp_time > 0:
            print(f'     Response time: {tcp_time:.1f}ms')
        
        # Summary
        print(f'\n  Summary:')
        if ping_ok and tcp_ok:
            print(f'     [OK] Device should be reachable!')
        elif ping_ok:
            print(f'     [WARN] Host responds to ping but port 102 is closed')
        else:
            print(f'     [ERROR] Host not reachable')
        
        print('  ' + '-'*50)
    
    print('\n' + '='*60)
    print('Diagnostic complete')
    print('='*60)

if __name__ == '__main__':
    main()
