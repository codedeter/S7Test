import snap7

plc_ip = "172.16.15.111"

def read_db(plc_ip, db_num, size=100):
    print(f"\nReading DB{db_num} from {plc_ip}...")

    client = snap7.client.Client()
    try:
        client.connect(plc_ip, 0, 1)
        data = client.db_read(db_num, 0, size)
        print(f"Read {len(data)} bytes")

        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            hex_str = ' '.join(f'{b:02x}' for b in chunk)
            print(f"  {i:4d}: {hex_str}")

        client.disconnect()
        return data
    except Exception as e:
        print(f"Error: {e}")
        return None

print("=" * 60)
print("RXB800 PLC Data Reader")
print("=" * 60)

read_db(plc_ip, 1, 80)
read_db(plc_ip, 10, 120)
read_db(plc_ip, 51, 100)
