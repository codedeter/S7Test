import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import snap7
from snap7.util import get_bool, get_int, get_dint, get_real

def read_db_data(plc_ip, db_num, size=200):
    print(f"\n{'='*60}")
    print(f"Reading DB{db_num} from {plc_ip}")
    print(f"{'='*60}")

    client = snap7.client.Client()
    try:
        client.connect(plc_ip, 0, 1)
        print(f"Connected!")
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    try:
        data = client.db_read(db_num, 0, size)
        print(f"Read {len(data)} bytes")

        print(f"\n--- Byte-level Analysis ---")
        for i in range(0, min(size, len(data)), 16):
            chunk = data[i:i+16]
            hex_str = ' '.join(f'{b:02x}' for b in chunk)
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            print(f"  {i:4d}: {hex_str:<48s} {ascii_str}")

        print(f"\n--- Bit Analysis (first 50 bytes) ---")
        bit_count = 0
        for byte_idx in range(min(50, len(data))):
            for bit_idx in range(8):
                if (data[byte_idx] >> bit_idx) & 1:
                    addr = byte_idx * 8 + bit_idx
                    print(f"  Bit {addr} (byte {byte_idx}.{bit_idx}) = 1")
                    bit_count += 1
                    if bit_count >= 50:
                        print("  ... (more bits set, showing first 50)")
                        break
            if bit_count >= 50:
                break

        print(f"\n--- Try parsing as different types ---")

        for start in [0, 2, 4, 8, 10, 12, 16, 20, 30, 50]:
            if start + 2 <= len(data):
                try:
                    val_int = get_int(data, start)
                    val_dint = get_dint(data, start)
                    val_real = get_real(data, start)
                    print(f"  Offset {start}: Int={val_int}, DInt={val_dint}, Real={val_real:.2f}" if val_real != 0 else f"  Offset {start}: Int={val_int}, DInt={val_dint}, Real={val_real}")

                except Exception as e:
                    print(f"  Offset {start}: Error parsing - {e}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            client.disconnect()
        except:
            pass

def main():
    print("=" * 60)
    print("PLC Data Block Reader")
    print("=" * 60)

    rxb800_ip = "172.16.15.111"

    print("\n" + "=" * 60)
    print(f"RXB800 ({rxb800_ip})")
    print("=" * 60)

    read_db_data(rxb800_ip, 1, 100)
    read_db_data(rxb800_ip, 10, 150)
    read_db_data(rxb800_ip, 51, 200)

if __name__ == '__main__':
    main()
