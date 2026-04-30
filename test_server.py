
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.devices import create_device_manager
from config.devices_config import create_device_configs

def init_devices_test(device_manager):
    device_configs = create_device_configs()
    for device_config in device_configs:
        device_manager.add_device(device_config)
    return len(device_configs)

print("Test 1: Checking device configurations...")
try:
    configs = create_device_configs()
    print(f"OK Found {len(configs)} device configurations:")
    for cfg in configs:
        print(f"  - {cfg.device_id}: {cfg.device_name} ({cfg.ip_address})")
except Exception as e:
    print(f"ERROR Error: {e}")
    import traceback
    traceback.print_exc()

print("\nTest 2: Creating Device Manager and initializing devices...")
try:
    manager = create_device_manager()
    device_count = init_devices_test(manager)
    print(f"OK Initialized {device_count} devices")
    
    devices = manager.list_devices()
    print(f"OK list_devices returned {len(devices)} devices")
    for d in devices:
        print(f"  - {d['device_id']}: {d['device_name']} ({d['status']}, connected={d['connected']})")
except Exception as e:
    print(f"ERROR Error: {e}")
    import traceback
    traceback.print_exc()

print("\nOK Tests completed!")
