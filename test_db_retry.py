import snap7
from snap7.util import get_bool, get_int, get_dint, get_real
import time

plc_ip = "172.16.15.111"

def read_db_with_retry(db_num, size, retries=3):
    """带重试的DB读取"""
    for attempt in range(retries):
        print(f"\n--- Attempt {attempt + 1} for DB{db_num} ---")

        client = snap7.client.Client()
        try:
            print(f"Connecting to {plc_ip}...")
            client.connect(plc_ip, 0, 1)
            time.sleep(1)

            print(f"Reading DB{db_num}...")
            data = client.db_read(db_num, 0, size)
            print(f"SUCCESS: Read {len(data)} bytes")

            print(f"\nHex dump:")
            for i in range(0, min(len(data), 80), 16):
                chunk = data[i:i+16]
                hex_str = ' '.join(f'{b:02x}' for b in chunk)
                print(f"  {i:4d}: {hex_str}")

            print(f"\nNon-zero bits (byte.bit = value):")
            bit_count = 0
            for byte_idx in range(min(20, len(data))):
                for bit_idx in range(8):
                    val = (data[byte_idx] >> bit_idx) & 1
                    if val == 1:
                        print(f"  Byte {byte_idx}.{bit_idx} = 1")
                        bit_count += 1
                        if bit_count >= 20:
                            print("  ...")
                            break
                if bit_count >= 20:
                    break

            return data

        except Exception as e:
            print(f"FAILED: {e}")
            try:
                client.disconnect()
            except:
                pass
            if attempt < retries - 1:
                print(f"Waiting 3 seconds before retry...")
                time.sleep(3)
        finally:
            del client
            time.sleep(1)

    return None

print("=" * 60)
print("RXB800 DB Reader with Retry")
print("=" * 60)

read_db_with_retry(1, 83)
read_db_with_retry(10, 105)
read_db_with_retry(51, 11)
