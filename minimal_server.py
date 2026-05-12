
import sys
import os
import threading
import time

sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify, make_response
from flask_socketio import SocketIO
from src.devices import create_device_manager, DeviceManager
from config.devices_config import create_device_configs

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# 创建并初始化设备管理器
print('Initializing device manager...')
device_manager = create_device_manager()
device_configs = create_device_configs()
for device_config in device_configs:
    device_manager.add_device(device_config)
print(f'Initialized {len(device_configs)} devices!')

# 后台数据采集和自动重连线程
def background_task():
    print('Starting connect_all...')
    # 先尝试连接所有设备
    device_manager.connect_all()
    print('connect_all completed!')
    
    # 然后启动数据采集
    def on_data_collected(data_list):
        try:
            # 广播设备状态
            devices = device_manager.list_devices()
            socketio.emit('devices_status', {'devices': devices})
            # 广播数据
            for data in data_list:
                socketio.emit('plc_data', {
                    'device_id': data.device_id,
                    'device_name': data.device_name,
                    'timestamp': data.timestamp,
                    'data': data.data,
                    'connected': data.connected
                })
        except Exception as e:
            print(f'Broadcast error: {e}')
    
    device_manager.set_data_callback(on_data_collected)
    device_manager.start_collection(interval=2.0)  # 每2秒采集一次

@app.route('/')
def index():
    html_path = os.path.join(os.path.dirname(__file__), 'public', 'index.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return make_response(content)

@app.route('/api/status')
def status():
    devices = device_manager.list_devices()
    return jsonify({
        'devices': devices,
        'total': len(devices)
    })

if __name__ == '__main__':
    print('Starting background task...')
    bg_thread = threading.Thread(target=background_task, daemon=True)
    bg_thread.start()
    
    print('Server starting at http://127.0.0.1:3000')
    socketio.run(app, host='127.0.0.1', port=3000, debug=True)
