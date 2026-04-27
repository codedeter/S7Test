import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from config.devices_config import create_device_configs
from src.devices import DeviceManager

def test_plc_read():
    device_manager = DeviceManager()
    configs = create_device_configs()

    print(f"Found {len(configs)} device(s)")
    print()

    for config in configs:
        print(f"Testing device: {config.device_id} - {config.device_name}")
        print(f"  IP: {config.ip_address}")
        print(f"  Type: {config.device_type.value}")
        print(f"  DataBlocks: {[db.number for db in config.data_blocks]}")

        device_manager.add_device(config)

        print(f"  Connecting...")
        if device_manager.connect_device(config.device_id):
            print(f"  Connected!")

            print(f"  Reading data...")
            data = device_manager.collect_data(config.device_id)
            if data:
                print(f"  Collected {len(data.data)} data points")
                for item in data.data[:5]:
                    print(f"    - {item.get('tag_name', 'unknown')}: {item.get('value', 'N/A')}")
                if len(data.data) > 5:
                    print(f"    ... and {len(data.data) - 5} more")
            else:
                print(f"  WARNING: No data collected!")
                print(f"  This may indicate:")
                print(f"    1. PLC variables not defined correctly")
                print(f"    2. DB addresses not matching actual PLC program")
                print(f"    3. Connection issue during data read")
        else:
            print(f"  FAILED to connect")

        print()

        device_manager.disconnect_device(config.device_id)

    device_manager.disconnect_all()

if __name__ == '__main__':
    test_plc_read()
