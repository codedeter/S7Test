import snap7
import struct

PLC_IP = "172.16.15.111"
RACK = 0
SLOT = 1

def connect():
    client = snap7.client.Client()
    client.connect(PLC_IP, RACK, SLOT)
    return client

def verify_all():
    client = connect()
    print("Connected to PLC\n")

    print("=== DB1 (GLABAL) Verification ===")
    data = client.db_read(1, 0, 83)
    print(f"Raw: {data.hex()}\n")

    bool_tests = [
        (0, 0, '保压选择'),
        (0, 2, '电机启动主控'),
        (3, 0, '滑块下行'),
        (3, 2, '回程主控'),
        (4, 0, '开机润滑'),
        (4, 3, '锁紧准备'),
    ]
    print("Boolean values:")
    for byte_off, bit_off, name in bool_tests:
        val = (data[byte_off] >> bit_off) & 0x01
        print(f"  {name}: {val}")

    print("\nInt/Real values:")
    int_tests = [
        (7, 2, '压机模式', 'int'),
        (10, 4, '润滑次数', 'dint'),
        (14, 4, '润滑时间', 'dint'),
        (18, 4, '油超温温度', 'real'),
        (22, 4, '油需冷却温度', 'real'),
        (29, 4, '上油加热关闭温度', 'real'),
        (33, 4, '上油需加热温度', 'real'),
    ]
    for offset, size, name, dtype in int_tests:
        raw = data[offset:offset+size]
        if dtype == 'int':
            val = int.from_bytes(raw, 'little', signed=True)
            print(f"  {name} (Byte {offset}): {val}")
        elif dtype == 'dint':
            val = int.from_bytes(raw, 'little', signed=True)
            print(f"  {name} (Byte {offset}): {val}")
        elif dtype == 'real':
            val = struct.unpack('<f', raw)[0]
            print(f"  {name} (Byte {offset}): {val:.2f}")

    print("\n=== DB10 (显示值) Verification ===")
    data10 = client.db_read(10, 0, 105)
    print(f"Raw: {data10.hex()}\n")

    real_tests = [
        (0, '模拟量采集.滑块左位移'),
        (4, '模拟量采集.滑块右位移'),
        (8, '模拟量采集.3Y10压力Mpa'),
        (12, '模拟量采集.主缸压力Mpa'),
        (16, '模拟量采集.侧缸压力Mpa'),
        (20, '模拟量采集.上油箱油温'),
        (24, '模拟量采集.移动台夹紧压力Mpa'),
        (28, '模拟量采集.2M1实时电机速度'),
        (32, '模拟量采集.2M2实时电机速度'),
        (36, '模拟量采集.冷却水温度'),
        (40, '模拟量采集.水流量'),
        (44, 'HMI显示.滑块实际位移'),
        (48, 'HMI显示.滑块中间缸压力T'),
        (52, 'HMI显示.滑块侧缸压力T'),
        (56, 'HMI显示.滑块总压T'),
        (60, 'HMI显示.滑块速度'),
        (64, 'HMI显示.左变频器转速显示'),
        (68, 'HMI显示.右变频器转速显示'),
        (72, 'HMI显示.左缓冲转速'),
        (76, 'HMI显示.右缓冲转速'),
        (80, 'HMI显示.3Y10压力T'),
        (84, '压力滤波显示'),
        (88, '左缓冲位置'),
        (92, '右缓冲位置'),
    ]
    print("Real values:")
    for offset, name in real_tests:
        raw = data10[offset:offset+4]
        val = struct.unpack('<f', raw)[0]
        print(f"  Byte {offset}: {name} = {val:.2f}")

    print("\nInt/DInt values:")
    other_tests = [
        (44, 2, 'HMI显示.保压时间', 'int'),
        (96, 4, '缓冲时间', 'dint'),
    ]
    for offset, size, name, dtype in other_tests:
        raw = data10[offset:offset+size]
        val = int.from_bytes(raw, 'little', signed=True)
        print(f"  Byte {offset}: {name} = {val}")

    print("\n=== DB51 (故障报警) Verification ===")
    data51 = client.db_read(51, 0, 11)
    print(f"Raw: {data51.hex()}\n")

    bool_tests_51 = [
        (0, 0, '上油箱油温过低'),
        (0, 1, '上油箱油需冷却'),
        (0, 2, '上油箱油温过高'),
        (0, 3, '上油箱滤油受阻'),
        (1, 0, '流量阀滤油堵塞'),
        (1, 1, '伺服阀滤油堵塞'),
    ]
    print("Boolean values (first 6):")
    for byte_off, bit_off, name in bool_tests_51:
        val = (data51[byte_off] >> bit_off) & 0x01
        print(f"  Byte {byte_off}, Bit {bit_off}: {name} = {val}")

    client.disconnect()
    print("\nDisconnected")

if __name__ == "__main__":
    verify_all()