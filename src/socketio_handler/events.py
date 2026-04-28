import time
import threading
from flask_socketio import SocketIO

from src.devices import DeviceManager
from src.services.data_processor import DataProcessor
from config.config import config


class SocketIOHandler:
    def __init__(self, socketio: SocketIO, device_manager: DeviceManager, data_processor: DataProcessor):
        self.socketio = socketio
        self.device_manager = device_manager
        self.data_processor = data_processor
        self._running = False
        self._sending_thread = None
        self._last_device_status = {}

        self.device_manager.set_status_callback(self._on_device_status_change)

    def _on_device_status_change(self, device_id: str, connected: bool, message: str):
        device_config = self.device_manager.get_device_config(device_id)
        device_status = self.device_manager.get_device_status(device_id)
        
        status_info = {
            'device_id': device_id,
            'device_name': device_config.device_name if device_config else device_id,
            'connected': connected,
            'message': message
        }
        
        if device_status:
            status_info.update({
                'last_disconnection_duration': device_status.last_disconnection_duration,
                'reconnection_count': device_status.reconnection_count,
                'total_disconnection_duration': device_status.total_disconnection_duration
            })
        
        self.socketio.emit('device_status', status_info)
        print(f"[SocketIO] Emitted device_status: {device_id} - {'connected' if connected else 'disconnected'} - {message}")

    def register_events(self):
        @self.socketio.on('connect')
        def handle_connect():
            print('[SocketIO] ========================================')
            print('[SocketIO] New client connected!')
            print('[SocketIO] ========================================')
            
            # 新客户端连接时，立即发送所有设备当前状态
            current_status = self.device_manager.list_devices()
            for device in current_status:
                status_info = {
                    'device_id': device['device_id'],
                    'device_name': device['device_name'],
                    'connected': device['connected'],
                    'status': device['status']
                }
                if 'last_disconnection_duration' in device:
                    status_info['last_disconnection_duration'] = device['last_disconnection_duration']
                if 'reconnection_count' in device:
                    status_info['reconnection_count'] = device['reconnection_count']
                self.socketio.emit('device_status', status_info)
                print(f"[SocketIO] Sent initial status to new client - {device['device_id']}: {device['status']}")

        @self.socketio.on('disconnect')
        def handle_disconnect():
            print('[SocketIO] Client disconnected')

        @self.socketio.on('switch_device')
        def handle_switch_device(data):
            device_id = data.get('deviceId')
            if device_id:
                print(f'Client switched to device: {device_id}')

                with self.data_processor.buffer_lock:
                    for buffer_item in list(self.data_processor.data_buffer):
                        if buffer_item.get('device_id') == device_id:
                            self.socketio.emit('data', {
                                'timestamp': buffer_item.get('timestamp', time.time() * 1000),
                                'device_id': buffer_item.get('device_id'),
                                'device_name': buffer_item.get('device_name'),
                                'current_values': {},
                                'history_data': []
                            })
                            latest_data = buffer_item.get('data', [])
                            for item in latest_data:
                                tag_name = item.get('tag_name')
                                if tag_name:
                                    key = f"{device_id}:{tag_name}"
                                    self.socketio.emit('data', {
                                        'timestamp': buffer_item.get('timestamp', time.time() * 1000),
                                        'device_id': buffer_item.get('device_id'),
                                        'device_name': buffer_item.get('device_name'),
                                        'current_values': {key: item},
                                        'history_data': []
                                    })

    def start_sending_thread(self):
        self._running = True
        
        def sending_loop():
            while self._running:
                try:
                    self._check_and_send_device_status()
                    
                    device_data_map = self.data_processor.prepare_socketio_data()
                    
                    for device_id, packet_data in device_data_map.items():
                        print(f"[SocketIO] Emitting data for {device_id}: {len(packet_data.get('current_values', {}))} values")
                        self.socketio.emit('data', packet_data)
                        
                        fault_status = self.data_processor.get_fault_status()
                        if device_id in fault_status:
                            print(f"[SocketIO] Emitting fault_status for {device_id}")
                            self.socketio.emit('fault_status', fault_status[device_id])

                except Exception as e:
                    print(f'Data sending error: {e}')
                    import traceback
                    traceback.print_exc()

                time.sleep(0.2)

        self._sending_thread = threading.Thread(target=sending_loop, daemon=True)
        self._sending_thread.start()
        print('Data sending thread started')

    def _check_and_send_device_status(self):
        current_status = self.device_manager.list_devices()
        
        for device in current_status:
            device_id = device['device_id']
            key = f"{device_id}:{device['status']}"
            
            if self._last_device_status.get(device_id) != key:
                self._last_device_status[device_id] = key
                
                status_info = {
                    'device_id': device_id,
                    'device_name': device['device_name'],
                    'connected': device['connected'],
                    'status': device['status']
                }
                
                if 'last_disconnection_duration' in device:
                    status_info['last_disconnection_duration'] = device['last_disconnection_duration']
                if 'reconnection_count' in device:
                    status_info['reconnection_count'] = device['reconnection_count']
                
                self.socketio.emit('device_status', status_info)
                print(f"[SocketIO] Status changed - {device_id}: {device['status']}")

    def stop_sending_thread(self):
        self._running = False
        if self._sending_thread:
            self._sending_thread.join(timeout=2)


class DataCollectionTask:
    def __init__(self, device_manager: DeviceManager, data_processor: DataProcessor):
        self.device_manager = device_manager
        self.data_processor = data_processor
        self._running = False
        self._collection_thread = None

    def start(self):
        self._running = True
        
        def collection_loop():
            print("Data collection thread started...")
            while self._running:
                try:
                    all_device_data = self.device_manager.collect_all_data()
                    if all_device_data:
                        for device_data in all_device_data:
                            print(f"[{device_data.device_id}] Collected {len(device_data.data)} points, connected={device_data.connected}")
                        self.data_processor.process_device_data(all_device_data)
                    else:
                        print("No data collected")
                except Exception as e:
                    print(f'Data collection error: {e}')
                    import traceback
                    traceback.print_exc()

                time.sleep(config.DATA_SAMPLING_INTERVAL / 1000)

        self._collection_thread = threading.Thread(target=collection_loop, daemon=True)
        self._collection_thread.start()
        print('Data collection thread started')

    def stop(self):
        self._running = False
        if self._collection_thread:
            self._collection_thread.join(timeout=2)