import sys
sys.path.insert(0, 'C:\\Users\\44673\\Desktop\\文件往这里存！！！\\TRAE\\S7Test')

print("=== 测试数据采集链路 ===\n")

print("[1] 创建设备管理器...")
from src.devices import create_device_manager
dm = create_device_manager()
print("设备管理器创建成功")

print("\n[2] 添加设备...")
from config.devices_config import create_device_configs
configs = create_device_configs()
for cfg in configs:
    dm.add_device(cfg)
    print(f"  添加设备: {cfg.device_id} ({cfg.device_name})")
    print(f"    数据块: {[db.number for db in cfg.data_blocks]}")
    for db in cfg.data_blocks:
        print(f"    DB{db.number}: {len(db.variables)} 个变量")

print("\n[3] 连接PLC02...")
result = dm.connect_device('plc_002')
print(f"  连接结果: {result}")
status = dm.get_device_status('plc_002')
print(f"  状态: {status.status.value if status else 'unknown'}")
print(f"  已连接: {status.connected if status else False}")

if status and status.connected:
    print("\n[4] 采集数据...")
    data = dm.collect_data('plc_002')
    if data:
        print(f"  采集到 {len(data.data)} 个数据点")
        if len(data.data) > 0:
            print(f"  前5个数据点:")
            for item in data.data[:5]:
                print(f"    - {item.get('tag_name', 'N/A')}: {item.get('value', 'N/A')}")
    else:
        print("  采集失败，返回None")

    print("\n[5] 测试DeviceCollector...")
    collector = dm.collectors.get('plc_002')
    if collector:
        print(f"  Collector已创建")
        print(f"  数据块映射: {list(collector.db_mappings.keys())}")

        print("\n[6] 直接调用collector采集...")
        collected = collector.collect_all_data()
        print(f"  采集到 {len(collected)} 个数据点")
        if len(collected) > 0:
            print(f"  前3个:")
            for item in collected[:3]:
                print(f"    - tag: {item.get('tag_name')}, value: {item.get('value')}")
    else:
        print("  Collector不存在")

print("\n=== 测试完成 ===")