import snap7
import struct

PLC_IP = "172.16.15.111"
RACK = 0
SLOT = 1

def connect():
    client = snap7.client.Client()
    client.connect(PLC_IP, RACK, SLOT)
    return client

def read_and_display_db1(client):
    print("\n=== Reading DB1 (GLABAL) ===")
    data = client.db_read(1, 0, 83)
    print(f"DB1 raw data ({len(data)} bytes): {data.hex()}")
    print()

    bool_vars = [
        (0, 0, '保压选择'),
        (0, 1, '双手合格'),
        (0, 2, '电机启动主控'),
        (0, 3, '滑块上限'),
        (0, 4, '关断上循环泵'),
        (0, 5, '反行程检查'),
        (0, 6, '允许下行'),
        (0, 7, '回程停止位1'),
        (1, 0, '回程停止位2'),
        (1, 1, '回程停止位3'),
        (1, 2, '滑块快转慢位'),
        (1, 3, '滑块下限位'),
        (1, 4, '压制力达到'),
        (1, 5, '主缸泄压到位'),
        (1, 6, '滑块合模位'),
        (1, 7, '移动台落下到位指示'),
        (2, 0, '移动台提升到位指示'),
        (2, 1, '移动台移入到位指示'),
        (2, 2, '下行主控'),
        (2, 3, '滑块下行前条件检查'),
        (2, 4, '保压'),
        (2, 5, '泄压'),
        (2, 6, '静止按钮'),
        (2, 7, '回程按钮'),
        (3, 0, '滑块下行'),
        (3, 1, '单次连续压制力到达'),
        (3, 2, '回程主控'),
        (3, 3, '锁紧松开驱动滑块回程'),
        (3, 4, '滑块回程准备'),
        (3, 5, '滑块回程'),
        (3, 6, '润滑安全条件'),
        (3, 7, '开机润滑完成'),
        (4, 0, '开机润滑'),
        (4, 1, '润滑次数到'),
        (4, 2, '润滑泵开始运行'),
        (4, 3, '锁紧准备'),
        (4, 4, '松开准备'),
        (4, 5, '锁紧松开不在上极限时先驱'),
    ]

    print("--- Boolean Variables (current config) ---")
    for byte_off, bit_off, name in bool_vars:
        if byte_off < len(data):
            val = (data[byte_off] >> bit_off) & 0x01
            print(f"  Byte {byte_off}, Bit {bit_off}: {name} = {val}")

    print("\n--- Testing Int/DInt/Real at different offsets ---")
    test_offsets = [
        (7, 2, 'Int', '压机模式 (at 7)'),
        (62, 2, 'Int', '压机模式 (at 62)'),
        (65, 4, 'DInt', '润滑次数 (at 65)'),
        (69, 4, 'DInt', '润滑时间 (at 69)'),
        (73, 4, 'Real', '油超温温度 (at 73)'),
        (77, 4, 'Real', '油需冷却温度 (at 77)'),
    ]

    for offset, size, dtype, desc in test_offsets:
        if offset + size <= len(data):
            raw = data[offset:offset+size]
            if dtype == 'Int':
                val = int.from_bytes(raw, 'little', signed=True)
                print(f"  {desc}: {val}")
            elif dtype == 'DInt':
                val = int.from_bytes(raw, 'little', signed=True)
                print(f"  {desc}: {val}")
            elif dtype == 'Real':
                val = struct.unpack('<f', raw)[0]
                print(f"  {desc}: {val}")
        else:
            print(f"  {desc}: offset {offset} + size {size} > {len(data)}")

def read_and_display_db10(client):
    print("\n=== Reading DB10 (显示值) ===")
    data = client.db_read(10, 0, 105)
    print(f"DB10 raw data ({len(data)} bytes): {data.hex()}")
    print()

    print("--- Real values at various offsets ---")
    real_offsets = [
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
        (44, '滑块实际位移'),
        (48, '滑块中间缸压力T'),
        (52, '滑块侧缸压力T'),
        (56, '滑块总压T'),
        (60, '滑块速度'),
    ]

    for offset, name in real_offsets:
        if offset + 4 <= len(data):
            val = struct.unpack('<f', data[offset:offset+4])[0]
            print(f"  Byte {offset}: {name} = {val:.2f}")

    print("\n--- Int values ---")
    int_offsets = [
        (44, 2, '保压时间'),
        (48, 2, '左气阀顶出时间'),
        (50, 2, '右气阀顶出时间'),
    ]

    for offset, size, name in int_offsets:
        if offset + size <= len(data):
            val = int.from_bytes(data[offset:offset+size], 'little', signed=True)
            print(f"  Byte {offset}: {name} = {val}")

def read_and_display_db51(client):
    print("\n=== Reading DB51 (故障报警) ===")
    data = client.db_read(51, 0, 11)
    print(f"DB51 raw data ({len(data)} bytes): {data.hex()}")
    print()

    print("--- First 20 boolean values ---")
    for byte_idx in range(min(11, len(data))):
        byte_val = data[byte_idx]
        for bit_idx in range(8):
            val = (byte_val >> bit_idx) & 0x01
            if val != 0:
                print(f"  Byte {byte_idx}, Bit {bit_idx} = {val}")

def main():
    client = connect()
    print("Connected to PLC")

    read_and_display_db1(client)
    read_and_display_db10(client)
    read_and_display_db51(client)

    client.disconnect()
    print("\nDisconnected")

if __name__ == "__main__":
    main()