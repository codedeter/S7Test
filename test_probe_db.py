import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import snap7
from snap7.util import get_bool

def probe_db_addresses(plc_ip, db_number, sample_size=100):
    print(f"\nProbing DB{db_number} at {plc_ip}...")
    print(f"Reading first {sample_size} bytes to find valid data...")

    client = snap7.client.Client()
    try:
        client.connect(plc_ip, 0, 1)
        print(f"Connected!")

        data = client.db_read(db_number, 0, sample_size)
        print(f"Read {len(data)} bytes from DB{db_number}")

        non_zero_count = 0
        for i in range(len(data)):
            if data[i] != 0:
                non_zero_count += 1
                if non_zero_count <= 20:
                    print(f"  Byte {i}: 0x{data[i]:02x} ({data[i]})")

        print(f"\nTotal non-zero bytes: {non_zero_count}/{len(data)}")

        print("\nBit-level scan (showing any non-zero bits):")
        bit_results = []
        for byte_idx in range(min(20, len(data))):
            for bit_idx in range(8):
                val = (data[byte_idx] >> bit_idx) & 1
                if val == 1:
                    addr = byte_idx * 8 + bit_idx
                    bit_results.append(addr)
                    print(f"  Bit {addr} (byte {byte_idx}.{bit_idx}) = 1")

        if bit_results:
            print(f"\nFound {len(bit_results)} set bits in first 20 bytes")
            print(f"First 10 set bit addresses: {bit_results[:10]}")
        else:
            print("\nNo set bits found in first 20 bytes")

        print("\nTrying to read specific DB areas:")
        for start in [0, 50, 100, 200, 500, 1000]:
            try:
                size = min(20, sample_size - start) if start < sample_size else 20
                if size > 0:
                    area_data = client.db_read(db_number, start, size)
                    non_zero = sum(1 for b in area_data if b != 0)
                    print(f"  DB{db_number}.{start}-{start+size}: {'Has data' if non_zero > 0 else 'Empty'}")
            except Exception as e:
                print(f"  DB{db_number}.{start}-{start+size}: Error - {e}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            client.disconnect()
        except:
            pass

def main():
    print("=" * 60)
    print("PLC Data Block Address Prober")
    print("=" * 60)

    plc_ip = "172.16.15.111"

    print("\n" + "=" * 60)
    print("Testing RXB800 (172.16.15.111)")
    print("=" * 60)

    probe_db_addresses(plc_ip, 1, 200)
    probe_db_addresses(plc_ip, 10, 200)
    probe_db_addresses(plc_ip, 51, 200)

    print("\n" + "=" * 60)
    print("Testing RXA1300 (172.15.14.150)")
    print("=" * 60)

    probe_db_addresses("172.15.14.150", 1, 200)
    probe_db_addresses("172.15.14.150", 10, 200)

if __name__ == '__main__':
    main()
