import snap7

plc_ip = "172.16.15.111"
db_num = 1

print(f"Connecting to {plc_ip}...")

client = snap7.client.Client()
try:
    client.connect(plc_ip, 0, 1)
    print(f"Connected!")

    print(f"Reading DB{db_num}...")
    data = client.db_read(db_num, 0, 50)

    print(f"Read {len(data)} bytes")
    print(f"Hex dump:")
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_str = ' '.join(f'{b:02x}' for b in chunk)
        print(f"  {i:4d}: {hex_str}")

    print(f"\nDisconnecting...")
    client.disconnect()
    print(f"Done!")

except Exception as e:
    print(f"Error: {e}")
