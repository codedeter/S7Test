import snap7
import time

plc_ip = "172.16.15.111"

def read_db(db_num):
    print(f"\nReading DB{db_num}...")

    client = snap7.client.Client()
    try:
        client.connect(plc_ip, 0, 1)
        time.sleep(0.5)
        data = client.db_read(db_num, 0, 100)
        print(f"DB{db_num}: Read {len(data)} bytes")

        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            hex_str = ' '.join(f'{b:02x}' for b in chunk)
            print(f"  {i:4d}: {hex_str}")

        client.disconnect()
        return data
    except Exception as e:
        print(f"DB{db_num}: Error - {e}")
        try:
            client.disconnect()
        except:
            pass
        return None

print("=" * 60)
print("RXB800 PLC Sequential Read Test")
print("=" * 60)

read_db(1)
time.sleep(1)
read_db(10)
time.sleep(1)
read_db(51)
