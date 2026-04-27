import snap7
import time

plc_ip = "172.16.15.111"

def quick_scan(max_db=60):
    print(f"Quick scan for PLC at {plc_ip}...")

    found = []

    for db_num in range(1, max_db + 1):
        try:
            client = snap7.client.Client()
            client.connect(plc_ip, 0, 1)
            time.sleep(0.2)

            data = client.db_read(db_num, 0, 1)
            found.append(db_num)
            print(f"DB{db_num}: OK", end="  ")

            client.disconnect()
            del client
            time.sleep(0.1)
        except:
            pass

    print(f"\n\nFound DBs: {found}")

print("=" * 60)
print("Quick DB Scan")
print("=" * 60)

quick_scan(60)
