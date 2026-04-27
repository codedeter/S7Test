import snap7

PLC_IP = "172.16.15.111"
RACK = 0
SLOT = 1

def test_connection():
    client = snap7.client.Client()
    try:
        print(f"Connecting to {PLC_IP}...")
        client.connect(PLC_IP, RACK, SLOT)
        print(f"Connected! CPU info: {client.get_cpu_info()}")
        print(f"CPU state: {client.get_cpu_state()}")
        return client
    except Exception as e:
        print(f"Connection failed: {e}")
        return None

def test_db_read(client, db_num, start=0, size=10):
    try:
        print(f"  Reading DB{db_num} from byte {start} size {size}...")
        data = client.db_read(db_num, start, size)
        print(f"    Success! Data: {data.hex()}")
        return data
    except Exception as e:
        error_str = str(e)
        if "Address" in error_str or "range" in error_str:
            print(f"    Address out of range error")
        else:
            print(f"    Error: {e}")
        return None

def probe_db_blocks(client):
    print("\n=== Probing DB blocks ===")

    for db_num in range(1, 100):
        try:
            info = client.db_get(db_num)
            print(f"DB{db_num}: exists, size={len(info)}")
        except Exception as e:
            error_str = str(e)
            if "Address" in error_str or "range" in error_str or "does not exist" in error_str or "Not found" in error_str:
                continue
            print(f"DB{db_num}: Error - {e}")

def main():
    client = test_connection()
    if not client:
        return

    print("\n=== Testing small reads at different start positions ===")
    for start in [0, 1, 2, 3, 4, 5]:
        test_db_read(client, 1, start, 1)

    print("\n=== Testing DB1 with different sizes ===")
    for size in [1, 2, 4, 8, 10, 20, 50, 83, 100]:
        test_db_read(client, 1, 0, size)

    print("\n=== Testing DB10 ===")
    for size in [1, 2, 4, 10, 20, 50, 100, 105]:
        test_db_read(client, 10, 0, size)

    print("\n=== Testing DB51 ===")
    for size in [1, 2, 4, 10, 11]:
        test_db_read(client, 51, 0, size)

    probe_db_blocks(client)

    client.disconnect()
    print("\nDisconnected.")

if __name__ == "__main__":
    main()