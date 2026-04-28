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

    def register_events(self):
        @self.socketio.on('connect')
        def handle_connect():
            print('New client connected')

        @self.socketio.on('disconnect')
        def handle_disconnect():
            print('Client disconnected')

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
                    device_data_map = self.data_processor.prepare_socketio_data()
                    
                    for device_id, packet_data in device_data_map.items():
                        print(f"[SocketIO] Emitting data to clients: {device_id}, {len(packet_data.get('current_values'))} values")
                        self.socketio.emit('data', packet_data)

                    anomalies = self.data_processor.get_pending_anomalies()
                    for anomaly in anomalies:
                        self.socketio.emit('anomaly', anomaly)

                    drools_results = self.data_processor.get_pending_drools_results()
                    for result in drools_results:
                        self.socketio.emit('drools_result', result)

                    slider_results = self.data_processor.get_pending_slider_results()
                    for result in slider_results:
                        self.socketio.emit('slider_fault', result)

                    fault_status = self.data_processor.get_fault_status()
                    for device_id, fault_data in fault_status.items():
                        self.socketio.emit('fault_status', fault_data)

                    active_anomalies = self.data_processor.get_active_anomalies()
                    for anomaly in active_anomalies:
                        self.socketio.emit('anomaly_update', anomaly)

                except Exception as e:
                    print(f'Data sending error: {e}')

                time.sleep(0.2)

        self._sending_thread = threading.Thread(target=sending_loop, daemon=True)
        self._sending_thread.start()
        print('Data sending thread started')

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
                            print(f"[{device_data.device_id}] Collected {len(device_data.data)} data points, connected={device_data.connected}")
                        self.data_processor.process_device_data(all_device_data)
                    else:
                        print("No data collected from any device")
                except Exception as e:
                    print(f'Data collection error: {e}')

                time.sleep(config.DATA_SAMPLING_INTERVAL / 1000)

        self._collection_thread = threading.Thread(target=collection_loop, daemon=True)
        self._collection_thread.start()
        print('Data collection thread started')

    def stop(self):
        self._running = False
        if self._collection_thread:
            self._collection_thread.join(timeout=2)