import socketio
import time

sio = socketio.Client()
found_tags = {}

@sio.on('connect')
def on_connect():
    print('Connected to server!')

@sio.on('data')
def on_data(packet):
    device_id = packet.get('device_id')
    current_values = packet.get('current_values', {})

    for key, item in current_values.items():
        tag_name = item.get('tag_name')
        value = item.get('value')

        if tag_name and ('油温' in tag_name or '压力' in tag_name or '位移' in tag_name or '速度' in tag_name):
            if tag_name not in found_tags:
                found_tags[tag_name] = value
                print(f"Found tag: '{tag_name}' = {value}")

@sio.on('disconnect')
def on_disconnect():
    print('Disconnected')
    print(f"\nTotal found: {len(found_tags)} tags")
    for tag, val in found_tags.items():
        print(f"  {tag}: {val}")

try:
    sio.connect('http://localhost:3000')
    time.sleep(5)
    sio.disconnect()
except Exception as e:
    print(f'Error: {e}')