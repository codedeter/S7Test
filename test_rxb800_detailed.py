import snap7
import time

PLC_IP = "172.16.15.111"
RACK = 0
SLOT = 1
DB_NUM = 1
SIZE = 83

def test_read_with_params(db_num, size, start=0):
    client = snap7.client.Client()
    try:
        print(f"Connecting to {PLC_IP}...")
        client.connect(PLC_IP, RACK, SLOT)
        print(f"Connected, reading DB{db_num} from byte {start} size {size}...")
        data = client.db_read(db_num, start, size)
        print(f"Success! Data length: {len(data)}, hex: {data.hex()[:40]}...")
        client.disconnect()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_multiple_connections():
    print("\n=== Testing multiple sequential connections ===")
    for i in range(3):
        print(f"\n--- Connection attempt {i+1} ---")
        success = test_read_with_params(DB_NUM, SIZE)
        if not success:
            print("Failed!")
            break
        time.sleep(0.5)

def test_with_wrong_params():
    print("\n=== Testing with various parameters ===")
    test_cases = [
        (1, 0, 83, "DB1, start=0, size=83"),
        (1, 0, 100, "DB1, start=0, size=100 (too big)"),
        (1, 0, 1, "DB1, start=0, size=1"),
        (1, 1, 82, "DB1, start=1, size=82"),
        (10, 0, 105, "DB10, start=0, size=105"),
        (51, 0, 11, "DB51, start=0, size=11"),
    ]

    for db_num, start, size, desc in test_cases:
        print(f"\n--- {desc} ---")
        client = snap7.client.Client()
        try:
            client.connect(PLC_IP, RACK, SLOT)
            data = client.db_read(db_num, start, size)
            print(f"Success! Data: {data.hex()[:30]}...")
            client.disconnect()
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(0.2)

if __name__ == "__main__":
    test_multiple_connections()
    test_with_wrong_params()
    print("\nDone!")