import time
import threading
from flask_socketio import SocketIO
from flask import request

from src.devices import DeviceManager
from src.services.data_processor import DataProcessor
from src.serialization import DataDelta, DataPacker, get_data_delta, get_data_packer
from src.socketio_handler.subscription_manager import get_subscription_manager
from config.config import config


class SocketIOHandler:
    def __init__(self, socketio: SocketIO, device_manager: DeviceManager, data_processor: DataProcessor):
        self.socketio = socketio
        self.device_manager = device_manager
        self.data_processor = data_processor
        self._running = False
        self._sending_thread = None
        self._last_device_status = {}
        self._sequence_counter: dict = {}
        
        self.data_delta = get_data_delta()
        self.data_packer = get_data_packer()
        self.subscription_manager = get_subscription_manager()
        
        self.device_manager.set_status_callback(self._on_device_status_change)
        
        self._init_sequences()
    
    def _init_sequences(self):
        for device_id in self.device_manager.devices:
            self._sequence_counter[device_id] = 0
    
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
        print(f"[SocketIO] Emitted device_status: {device_id} - {'connected' if connected else 'disconnected'}")
    
    def register_events(self):
        @self.socketio.on('connect')
        def handle_connect():
            sid = request.sid
            client_id = request.args.get('clientId', sid)
            
            print('[SocketIO] ========================================')
            print(f'[SocketIO] New client connected! SID: {sid}, ClientID: {client_id}')
            print('[SocketIO] ========================================')
            
            self.subscription_manager.add_client(sid, client_id)
            
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
                self.socketio.emit('device_status', status_info, to=sid)
                print(f"[SocketIO] Sent initial status to {client_id} - {device['device_id']}: {device['status']}")
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            sid = request.sid
            client = self.subscription_manager.get_client(sid)
            client_id = client.client_id if client else sid
            print(f'[SocketIO] Client disconnected: {client_id}')
            self.subscription_manager.remove_client(sid)
        
        @self.socketio.on('subscribe')
        def handle_subscribe(data):
            sid = request.sid
            devices = data.get('devices', [])
            tags = data.get('tags', [])
            subscribe_all_devices = data.get('subscribeAllDevices', True)
            subscribe_all_tags = data.get('subscribeAllTags', True)
            
            self.subscription_manager.set_subscribe_all_devices(sid, subscribe_all_devices)
            self.subscription_manager.set_subscribe_all_tags(sid, subscribe_all_tags)
            
            for device_id in devices:
                self.subscription_manager.subscribe_to_device(sid, device_id)
                print(f"[SocketIO] Client subscribed to device: {device_id}")
            
            for tag_name in tags:
                self.subscription_manager.subscribe_to_tag(sid, tag_name)
                print(f"[SocketIO] Client subscribed to tag: {tag_name}")
            
            self.socketio.emit('subscription_updated', {
                'success': True,
                'devices': devices,
                'tags': tags,
                'subscribeAllDevices': subscribe_all_devices,
                'subscribeAllTags': subscribe_all_tags
            }, to=sid)
        
        @self.socketio.on('unsubscribe')
        def handle_unsubscribe(data):
            sid = request.sid
            devices = data.get('devices', [])
            tags = data.get('tags', [])
            
            for device_id in devices:
                self.subscription_manager.unsubscribe_from_device(sid, device_id)
                print(f"[SocketIO] Client unsubscribed from device: {device_id}")
            
            for tag_name in tags:
                self.subscription_manager.unsubscribe_from_tag(sid, tag_name)
                print(f"[SocketIO] Client unsubscribed from tag: {tag_name}")
            
            self.socketio.emit('subscription_updated', {
                'success': True,
                'unsubscribed_devices': devices,
                'unsubscribed_tags': tags
            }, to=sid)
        
        @self.socketio.on('request_full_snapshot')
        def handle_request_full_snapshot(data):
            sid = request.sid
            device_id = data.get('deviceId')
            
            print(f"[SocketIO] Client requested full snapshot for: {device_id}")
            
            device_data_map = self.data_processor.prepare_socketio_data()
            
            if device_id in device_data_map:
                self.data_delta.clear_device_state(device_id)
                
                full_data = device_data_map[device_id]
                full_data['update_type'] = 'full'
                
                packet = self.data_packer.create_packet(
                    packet_type='data',
                    device_id=device_id,
                    payload=full_data,
                    sequence=self._get_next_sequence(device_id)
                )
                
                self.socketio.emit('data', packet, to=sid)
                print(f"[SocketIO] Sent full snapshot for {device_id}")
        
        @self.socketio.on('ping')
        def handle_ping():
            return {'timestamp': time.time()}
    
    def _get_next_sequence(self, device_id: str) -> int:
        if device_id not in self._sequence_counter:
            self._sequence_counter[device_id] = 0
        self._sequence_counter[device_id] += 1
        return self._sequence_counter[device_id]
    
    def start_sending_thread(self):
        self._running = True
        
        def sending_loop():
            while self._running:
                try:
                    self._check_and_send_device_status()
                    
                    device_data_map = self.data_processor.prepare_socketio_data()
                    
                    for device_id, full_data in device_data_map.items():
                        current_values = full_data.get('current_values', {})
                        
                        delta_values = self.data_delta.compute_delta(device_id, current_values)
                        
                        if delta_values:
                            sequence = self._get_next_sequence(device_id)
                            
                            packet_data = {
                                'device_id': device_id,
                                'device_name': full_data.get('device_name', device_id),
                                'current_values': delta_values,
                                'update_type': 'delta',
                                'sequence': sequence
                            }
                            
                            packet = self.data_packer.create_packet(
                                packet_type='data',
                                device_id=device_id,
                                payload=packet_data,
                                sequence=sequence
                            )
                            
                            self.socketio.emit('data', packet)
                            print(f"[SocketIO] Emitted delta for {device_id}: {len(delta_values)} values, seq={sequence}")
                        
                        fault_status = self.data_processor.get_fault_status()
                        if device_id in fault_status:
                            fault_packet = self.data_packer.create_packet(
                                packet_type='fault_status',
                                device_id=device_id,
                                payload=fault_status[device_id],
                                sequence=self._get_next_sequence(device_id)
                            )
                            self.socketio.emit('fault_status', fault_packet)
                    
                    self._send_pending_anomalies()
                    
                except Exception as e:
                    print(f'Data sending error: {e}')
                    import traceback
                    traceback.print_exc()
                
                time.sleep(config.DATA_SAMPLING_INTERVAL / 1000)
        
        self._sending_thread = threading.Thread(target=sending_loop, daemon=True)
        self._sending_thread.start()
        print('Data sending thread started')
    
    def _send_pending_anomalies(self):
        anomalies = self.data_processor.get_pending_anomalies()
        if anomalies:
            for anomaly in anomalies:
                packet = self.data_packer.create_packet(
                    packet_type='anomaly',
                    device_id=anomaly.get('device_id', 'unknown'),
                    payload=anomaly
                )
                self.socketio.emit('anomaly', packet)
                print(f"[SocketIO] Emitted anomaly: {anomaly.get('tag_name')}")
    
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
                
                status_packet = self.data_packer.create_packet(
                    packet_type='device_status',
                    device_id=device_id,
                    payload=status_info
                )
                
                self.socketio.emit('device_status', status_packet)
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