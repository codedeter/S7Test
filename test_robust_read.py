import snap7
import time

plc_ip = "172.16.15.111"

def read_with_retry(db_num, max_retries=3):
    for attempt in range(max_retries):
        try:
            client = snap7.client.Client()
            client.set_connection_params(plc_ip, 0, 1)
            client.connect()
            time.sleep(0.3)

            data = client.db_read(db_num, 0, 100)

            client.disconnect()
            del client
            time.sleep(0.1)

            return data
        except Exception as e:
            print(f"  Attempt {attempt + 1} failed: {e}")
            try:
                client.disconnect()
            except:
                pass
            del client
            time.sleep(0.5)

    return None

def main():
    print("=" * 60)
    print("Robust DB Reader with Retry")
    print("=" * 60)

    dbs_to_read = [1, 10, 51]

    for db in dbs_to_read:
        print(f"\nReading DB{db}...")
        data = read_with_retry(db)

        if data:
            print(f"  SUCCESS - Read {len(data)} bytes")
            hex_str = ' '.join(f'{b:02x}' for b in data[:16])
            print(f"  First 16 bytes: {hex_str}")
        else:
            print(f"  FAILED after {3} attempts")

if __name__ == '__main__':
    main()
