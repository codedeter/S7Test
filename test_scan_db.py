import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import snap7

def scan_plc_db_blocks(plc_ip, rack=0, slot=1, max_db=100):
    print(f"\nScanning PLC at {plc_ip}...")

    client = snap7.client.Client()
    found_dbs = []

    try:
        client.connect(plc_ip, rack, slot)
        print(f"Connected!")
    except Exception as e:
        print(f"Connection failed: {e}")
        return []

    for db_num in range(1, max_db + 1):
        try:
            data = client.db_read(db_num, 0, 1)
            found_dbs.append(db_num)
            print(f"  DB{db_num}: FOUND (first byte: 0x{data[0]:02x})")
        except Exception as e:
            pass

    try:
        client.disconnect()
    except:
        pass

    print(f"\n>>> Found {len(found_dbs)} data blocks: {found_dbs}")
    return found_dbs

def read_db_preview(plc_ip, db_num, size=50):
    print(f"\nReading DB{db_num} preview ({size} bytes)...")

    client = snap7.client.Client()
    try:
        client.connect(plc_ip, 0, 1)
        data = client.db_read(db_num, 0, size)

        non_zero_bytes = [(i, data[i]) for i in range(len(data)) if data[i] != 0]

        print(f"  Total bytes read: {len(data)}")
        print(f"  Non-zero bytes: {len(non_zero_bytes)}")

        if non_zero_bytes:
            print(f"  First 10 non-zero bytes:")
            for idx, (pos, val) in enumerate(non_zero_bytes[:10]):
                print(f"    Offset {pos}: 0x{val:02x} ({val})")

            byte_values = [data[i] for i in range(min(20, len(data)))]
            print(f"  First 20 bytes: {' '.join(f'{b:02x}' for b in byte_values)}")

        return data
    except Exception as e:
        print(f"  Error: {e}")
        return None
    finally:
        try:
            client.disconnect()
        except:
            pass

def main():
    print("=" * 60)
    print("PLC Data Block Scanner")
    print("=" * 60)

    print("\n" + "=" * 60)
    print("Scanning RXB800 (172.16.15.111)")
    print("=" * 60)
    rxb800_dbs = scan_plc_db_blocks("172.16.15.111")

    print("\n" + "=" * 60)
    print("Scanning RXA1300 (172.15.14.150)")
    print("=" * 60)
    rxa1300_dbs = scan_plc_db_blocks("172.15.14.150")

    print("\n" + "=" * 60)
    print("DB Preview for RXB800")
    print("=" * 60)
    for db in rxb800_dbs[:10]:
        read_db_preview("172.16.15.111", db, 30)

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"RXB800 (172.16.15.111): {rxb800_dbs}")
    print(f"RXA1300 (172.15.14.150): {rxa1300_dbs}")

if __name__ == '__main__':
    main()
