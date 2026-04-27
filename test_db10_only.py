import snap7
import time

plc_ip = "172.16.15.111"

def read_single_db(db_num, size=100):
    print(f"Reading DB{db_num} from {plc_ip}...")

    try:
        client = snap7.client.Client()
        client.connect(plc_ip, 0, 1)
        time.sleep(0.5)

        data = client.db_read(db_num, 0, size)
        print(f"DB{db_num}: SUCCESS - Read {len(data)} bytes")

        for i in range(0, min(len(data), 80), 16):
            chunk = data[i:i+16]
            hex_str = ' '.join(f'{b:02x}' for b in chunk)
            print(f"  {i:4d}: {hex_str}")

        client.disconnect()
        return data
    except Exception as e:
        print(f"DB{db_num}: FAILED - {e}")
        return None

print("Testing DB10 only...")
read_single_db(10, 120)
