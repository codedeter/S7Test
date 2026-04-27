import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import snap7
from snap7.util import get_bool, get_int, get_dint, get_real
import struct

def read_and_parse_db(plc_ip, db_num, size=100):
    """读取并解析DB数据"""
    print(f"\n{'='*60}")
    print(f"Reading DB{db_num} from {plc_ip}")
    print(f"{'='*60}")

    client = snap7.client.Client()
    try:
        client.connect(plc_ip, 0, 1)
        print(f"Connected to {plc_ip}")
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    try:
        data = client.db_read(db_num, 0, size)
        print(f"Read {len(data)} bytes from DB{db_num}")

        print(f"\n--- Raw Hex Data ---")
        for i in range(0, min(len(data), 80), 16):
            chunk = data[i:i+16]
            hex_str = ' '.join(f'{b:02x}' for b in chunk)
            print(f"  {i:4d}: {hex_str}")

        print(f"\n--- Boolean Bits (byte.bit = value) ---")
        bit_count = 0
        for byte_idx in range(min(20, len(data))):
            for bit_idx in range(8):
                val = (data[byte_idx] >> bit_idx) & 1
                if val == 1:
                    addr = byte_idx * 8 + bit_idx
                    print(f"  Byte {byte_idx}.{bit_idx} (Bit {addr}) = 1")
                    bit_count += 1
                    if bit_count >= 30:
                        print("  ... (showing first 30 bits)")
                        break
            if bit_count >= 30:
                break

        print(f"\n--- Integer/Real Values at common offsets ---")
        for offset in [0, 2, 4, 8, 10, 12, 16, 20, 30, 40, 50]:
            if offset + 4 <= len(data):
                try:
                    int_val = get_int(data, offset)
                    dint_val = get_dint(data, offset)
                    real_val = get_real(data, offset)
                    if abs(real_val) > 0.0001 or int_val != 0 or dint_val != 0:
                        print(f"  Offset {offset:2d}: Int={int_val:6d}, DInt={dint_val:8d}, Real={real_val:12.2f}")
                except Exception as e:
                    print(f"  Offset {offset}: Error - {e}")

    except Exception as e:
        print(f"Error reading DB{db_num}: {e}")
    finally:
        try:
            client.disconnect()
        except:
            pass

def main():
    plc_ip = "172.16.15.111"

    print("=" * 60)
    print(f"RXB800 PLC Data Reader Test")
    print(f"PLC IP: {plc_ip}")
    print("=" * 60)

    read_and_parse_db(plc_ip, 1, 83)
    read_and_parse_db(plc_ip, 10, 105)
    read_and_parse_db(plc_ip, 51, 11)

if __name__ == '__main__':
    main()
