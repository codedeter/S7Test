import snap7
import struct

PLC_IP = "172.16.15.111"
RACK = 0
SLOT = 1

def connect():
    client = snap7.client.Client()
    client.connect(PLC_IP, RACK, SLOT)
    return client

def find_int_values(client):
    print("\n=== Scanning DB1 for Int values ===")
    data = client.db_read(1, 0, 83)
    print(f"DB1 ({len(data)} bytes): {data.hex()}")

    print("\n--- Scanning for Int (2-byte) values ---")
    for i in range(0, min(83, len(data)) - 1, 2):
        raw = data[i:i+2]
        val_le = int.from_bytes(raw, 'little', signed=True)
        val_be = int.from_bytes(raw, 'big', signed=True)
        if -100 < val_le < 10000:
            print(f"  Offset {i}: little={val_le}, big={val_be}")

    print("\n--- Scanning for DInt (4-byte) values ---")
    for i in range(0, min(83, len(data)) - 3, 4):
        raw = data[i:i+4]
        val_le = int.from_bytes(raw, 'little', signed=True)
        if -100000 < val_le < 100000:
            print(f"  Offset {i}: {val_le}")

def find_real_values(client):
    print("\n=== Scanning DB10 for Real values ===")
    data = client.db_read(10, 0, 105)
    print(f"DB10 ({len(data)} bytes): {data.hex()}")

    print("\n--- Scanning for Real (4-byte) values ---")
    for i in range(0, min(105, len(data)) - 3, 4):
        raw = data[i:i+4]
        try:
            val = struct.unpack('<f', raw)[0]
            if 0 < val < 10000:
                print(f"  Offset {i}: {val:.2f}")
        except:
            pass

    print("\n--- Scanning for Int values in DB10 ---")
    for i in range(0, min(105, len(data)) - 1, 2):
        raw = data[i:i+2]
        val = int.from_bytes(raw, 'little', signed=True)
        if 0 <= val <= 1000:
            print(f"  Offset {i}: {val}")

def show_byte_map(client):
    print("\n=== DB1 Byte Map (first 30 bytes) ===")
    data = client.db_read(1, 0, 30)

    for i in range(len(data)):
        byte = data[i]
        bits = [(byte >> b) & 1 for b in range(7, -1, -1)]
        print(f"  Byte {i:2d}: 0x{byte:02X}  {bits[0]}{bits[1]}{bits[2]}{bits[3]}{bits[4]}{bits[5]}{bits[6]}{bits[7]}")

def main():
    client = connect()
    print("Connected to PLC")

    show_byte_map(client)
    find_int_values(client)
    find_real_values(client)

    client.disconnect()
    print("\nDisconnected")

if __name__ == "__main__":
    main()