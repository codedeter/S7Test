import snap7
import struct

PLC_IP = "172.16.15.111"
RACK = 0
SLOT = 1

def connect():
    client = snap7.client.Client()
    client.connect(PLC_IP, RACK, SLOT)
    return client

def verify_db1(client):
    print("\n=== Verifying DB1 (GLABAL) offsets ===")
    data = client.db_read(1, 0, 83)
    print(f"DB1 ({len(data)} bytes): {data.hex()}")

    print("\n--- Global Bool tests ---")
    tests = [
        (0, 0, '保压选择'),
        (0, 2, '电机启动主控'),
        (3, 0, '滑块下行'),
        (3, 2, '回程主控'),
    ]
    for byte_off, bit_off, name in tests:
        val = (data[byte_off] >> bit_off) & 0x01
        print(f"  Byte {byte_off}, Bit {bit_off}: {name} = {val}")

    print("\n--- Int/Real tests ---")
    int_tests = [
        (7, 2, '压机模式'),
        (10, 4, '润滑次数'),
        (14, 4, '润滑时间'),
        (18, 4, '油超温温度'),
        (22, 4, '油需冷却温度'),
    ]
    for offset, size, name in int_tests:
        if offset + size <= len(data):
            raw = data[offset:offset+size]
            if size == 2:
                val = int.from_bytes(raw, 'little', signed=True)
                print(f"  Byte {offset}: {name} = {val}")
            elif size == 4:
                try:
                    val = struct.unpack('<f', raw)[0]
                    print(f"  Byte {offset}: {name} = {val:.2f}")
                except:
                    val = int.from_bytes(raw, 'little', signed=True)
                    print(f"  Byte {offset}: {name} = {val}")

def verify_db51(client):
    print("\n=== Verifying DB51 (故障报警) offsets ===")
    data = client.db_read(51, 0, 11)
    print(f"DB51 ({len(data)} bytes): {data.hex()}")

    print("\n--- First 20 Bool tests ---")
    tests = [
        (0, 0, '上油箱油温过低'),
        (0, 1, '上油箱油需冷却'),
        (0, 3, '上油箱滤油受阻'),
        (1, 0, '流量阀滤油堵塞'),
        (2, 0, '右前立柱急停不合格'),
    ]
    for byte_off, bit_off, name in tests:
        if byte_off < len(data):
            val = (data[byte_off] >> bit_off) & 0x01
            print(f"  Byte {byte_off}, Bit {bit_off}: {name} = {val}")

def verify_db10(client):
    print("\n=== Verifying DB10 (显示值) offsets ===")
    data = client.db_read(10, 0, 105)
    print(f"DB10 ({len(data)} bytes): {data.hex()}")

    print("\n--- Real value tests ---")
    real_tests = [
        (0, '滑块左位移'),
        (4, '滑块右位移'),
        (8, '3Y10压力Mpa'),
        (12, '主缸压力Mpa'),
        (16, '侧缸压力Mpa'),
        (20, '上油箱油温'),
        (24, '移动台夹紧压力Mpa'),
        (28, '2M1实时电机速度'),
        (32, '2M2实时电机速度'),
        (36, '冷却水温度'),
        (40, '水流量'),
    ]
    for offset, name in real_tests:
        if offset + 4 <= len(data):
            raw = data[offset:offset+4]
            val = struct.unpack('<f', raw)[0]
            print(f"  Byte {offset}: {name} = {val:.2f}")

    print("\n--- HMI显示 tests ---")
    hmi_tests = [
        (44, '滑块实际位移'),
        (48, '滑块中间缸压力T'),
        (52, '滑块侧缸压力T'),
        (56, '滑块总压T'),
        (60, '滑块速度'),
    ]
    for offset, name in hmi_tests:
        if offset + 4 <= len(data):
            raw = data[offset:offset+4]
            val = struct.unpack('<f', raw)[0]
            print(f"  Byte {offset}: {name} = {val:.2f}")

    print("\n--- Other values ---")
    other_tests = [
        (84, '压力滤波显示'),
        (88, '左缓冲位置'),
        (92, '右缓冲位置'),
    ]
    for offset, name in other_tests:
        if offset + 4 <= len(data):
            raw = data[offset:offset+4]
            val = struct.unpack('<f', raw)[0]
            print(f"  Byte {offset}: {name} = {val:.2f}")

    print("\n--- Int values ---")
    int_tests = [
        (44, '保压时间'),
        (96, '缓冲时间'),
    ]
    for offset, name in int_tests:
        if offset + 4 <= len(data):
            raw = data[offset:offset+4]
            val = int.from_bytes(raw, 'little', signed=True)
            print(f"  Byte {offset}: {name} = {val}")

def main():
    client = connect()
    print("Connected to PLC")

    verify_db1(client)
    verify_db51(client)
    verify_db10(client)

    client.disconnect()
    print("\nDisconnected")

if __name__ == "__main__":
    main()