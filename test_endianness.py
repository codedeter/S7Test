import snap7
import struct

PLC_IP = "172.16.15.111"
RACK = 0
SLOT = 1

def connect():
    client = snap7.client.Client()
    client.connect(PLC_IP, RACK, SLOT)
    return client

def verify_endianness():
    client = connect()
    print("Connected to PLC\n")

    print("=== Testing Endianness ===\n")

    print("--- DB1 Tests ---")
    data = client.db_read(1, 0, 83)

    print("Byte 10-13 (DInt -润滑次数):")
    dint_bytes = data[10:14]
    print(f"  Raw bytes: {dint_bytes.hex()}")
    print(f"  Little-endian: {int.from_bytes(dint_bytes, 'little', signed=True)}")
    print(f"  Big-endian: {int.from_bytes(dint_bytes, 'big', signed=True)}")

    print("\nByte 18-21 (Real -油超温温度):")
    real_bytes = data[18:22]
    print(f"  Raw bytes: {real_bytes.hex()}")
    print(f"  Little-endian float: {struct.unpack('<f', real_bytes)[0]}")
    print(f"  Big-endian float: {struct.unpack('>f', real_bytes)[0]}")

    print("\n--- DB10 Tests ---")
    data10 = client.db_read(10, 0, 105)

    print("Byte 0-3 (Real -滑块左位移):")
    real_bytes = data10[0:4]
    print(f"  Raw bytes: {real_bytes.hex()}")
    print(f"  Little-endian float: {struct.unpack('<f', real_bytes)[0]}")
    print(f"  Big-endian float: {struct.unpack('>f', real_bytes)[0]}")

    print("\nByte 28-31 (Real -2M1实时电机速度):")
    real_bytes = data10[28:32]
    print(f"  Raw bytes: {real_bytes.hex()}")
    print(f"  Little-endian float: {struct.unpack('<f', real_bytes)[0]}")
    print(f"  Big-endian float: {struct.unpack('>f', real_bytes)[0]}")

    client.disconnect()
    print("\nDisconnected")

if __name__ == "__main__":
    verify_endianness()