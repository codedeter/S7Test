import sys
sys.path.insert(0, '.')
from config.devices_config import create_device_configs

configs = create_device_configs()
for cfg in configs:
    print(f"\nDevice: {cfg.device_id} - {cfg.device_name}")
    for db in cfg.data_blocks:
        print(f"  DB{db.number}: name={db.name}, size={db.size}, vars={len(db.variables)}")
        if db.size == 0:
            print(f"    WARNING: size is 0!")