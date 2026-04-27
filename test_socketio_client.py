import socketio
import time

sio = socketio.Client()

@sio.on('connect')
def on_connect():
    print('Connected to server!')

@sio.on('data')
def on_data(packet):
    print(f"\n=== Received data packet ===")
    print(f"Device: {packet.get('device_id')}")
    print(f"Device name: {packet.get('device_name')}")
    print(f"Current values count: {len(packet.get('current_values', {}))}")

    current_values = packet.get('current_values', {})
    print(f"\n--- First 20 tag names ---")
    for i, (key, item) in enumerate(list(current_values.items())[:20]):
        print(f"  {key}: tag_name={item.get('tag_name')}, value={item.get('value')}")

    print(f"\n--- Looking for specific tags ---")
    for key, item in current_values.items():
        tag = item.get('tag_name', '')
        if '油温' in tag or '压力' in tag or '位移' in tag or '速度' in tag:
            print(f"  Found: {key} = {item.get('value')}")

@sio.on('disconnect')
def on_disconnect():
    print('Disconnected from server')

try:
    print('Connecting to http://localhost:3000...')
    sio.connect('http://localhost:3000')
    sio.wait()
except Exception as e:
    print(f'Error: {e}')