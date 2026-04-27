import snap7
import time

plc_ip = "172.16.15.111"

def read_db_single_connection(db_num, size=100):
    """每次读取使用独立的连接"""
    print(f"\nReading DB{db_num}...")

    try:
        client = snap7.client.Client()
        client.connect(plc_ip, 0, 1)
        time.sleep(0.3)

        data = client.db_read(db_num, 0, size)
        print(f"DB{db_num}: SUCCESS - Read {len(data)} bytes")

        for i in range(0, min(len(data), 80), 16):
            chunk = data[i:i+16]
            hex_str = ' '.join(f'{b:02x}' for b in chunk)
            print(f"  {i:4d}: {hex_str}")

        client.disconnect()
        del client
        return data
    except Exception as e:
        print(f"DB{db_num}: FAILED - {e}")
        return None

print("=" * 60)
print("RXB800 PLC Individual DB Read Test")
print("=" * 60)

read_db_single_connection(1, 80)
time.sleep(2)
read_db_single_connection(10, 120)
time.sleep(2)
read_db_single_connection(51, 100)
