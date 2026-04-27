import snap7
import struct

PLC_IP = "172.16.15.111"
RACK = 0
SLOT = 1

def verify_big_endian():
    client = snap7.client.Client()
    client.connect(PLC_IP, RACK, SLOT)
    print("Connected to PLC\n")

    print("=== DB1 Tests (Big Endian) ===")
    data = client.db_read(1, 0, 83)

    print("Byte 10-13 (DInt -润滑次数):")
    dint_bytes = data[10:14]
    print(f"  Raw bytes: {dint_bytes.hex()}")
    print(f"  Big-endian: {int.from_bytes(dint_bytes, 'big', signed=True)}")

    print("Byte 18-21 (Real -油超温温度):")
    real_bytes = data[18:22]
    print(f"  Raw bytes: {real_bytes.hex()}")
    print(f"  Big-endian float: {struct.unpack('>f', real_bytes)[0]}")

    print("\n=== DB10 Tests (Big Endian) ===")
    data10 = client.db_read(10, 0, 105)

    print("Byte 0-3 (Real -滑块左位移):")
    real_bytes = data10[0:4]
    print(f"  Raw bytes: {real_bytes.hex()}")
    print(f"  Big-endian float: {struct.unpack('>f', real_bytes)[0]}")

    print("\nByte 28-31 (Real -2M1实时电机速度):")
    real_bytes = data10[28:32]
    print(f"  Raw bytes: {real_bytes.hex()}")
    print(f"  Big-endian float: {struct.unpack('>f', real_bytes)[0]}")

    print("\n--- All DB10 Real values (Big Endian) ---")
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
    for offset, name in real_tests:
        raw = data10[offset:offset+4]
        val = struct.unpack('>f', raw)[0]
        print(f"  Byte {offset}: {name} = {val:.2f}")

    client.disconnect()
    print("\nDisconnected")

if __name__ == "__main__":
    verify_big_endian()