"""
优化的Socket.IO事件处理器

解决ping timeout和数据传输效率问题
"""

import time
import threading
from typing import Dict, List, Any, Optional, Callable
from flask_socketio import SocketIO
from flask import request

from src.devices import DeviceManager
from src.services.data_processor import DataProcessor
from src.serialization import DataDelta, DataPacker, get_data_delta, get_data_packer
from src.socketio_handler.subscription_manager import get_subscription_manager
from src.services.data_batch_processor import (
    create_batch_processor,
    create_incremental_manager,
    BatchConfig,
    DataPacket
)
from config.config import config
from config.socketio_config import get_socketio_config


class OptimizedSocketIOHandler:
    """
    优化的Socket.IO处理器

    优化点：
    1. 智能心跳配置
    2. 批量数据传输
    3. 增量更新
    4. 前端节流
    5. 性能监控
    """

    def __init__(self, socketio: SocketIO, device_manager: DeviceManager,
                 data_processor: DataProcessor):
        self.socketio = socketio
        self.device_manager = device_manager
        self.data_processor = data_processor

        # 配置
        self.socketio_config = get_socketio_config()

        # 序列号
        self._sequence_counter: dict = {}
        self._last_device_status = {}

        # 组件初始化
        self.data_delta = get_data_delta()
        self.data_packer = get_data_packer()
        self.subscription_manager = get_subscription_manager()

        # 批量处理器
        self.batch_processor = create_batch_processor(BatchConfig(
            batch_size=self.socketio_config.BATCH_SIZE,
            batch_timeout_ms=self.socketio_config.BATCH_TIMEOUT_MS,
            max_batch_delay_ms=self.socketio_config.MAX_BATCH_DELAY_MS,
            enable_compression=self.socketio_config.ENABLE_COMPRESSION,
            compression_threshold=self.socketio_config.COMPRESSION_THRESHOLD
        ))
        self.batch_processor.set_send_callback(self._on_batch_send)
        self.batch_processor.start()

        # 增量管理器
        self.incremental_manager = create_incremental_manager(
            threshold=self.socketio_config.VALUE_CHANGE_THRESHOLD
        )

        # 性能统计
        self._stats = {
            'packets_sent': 0,
            'bytes_sent': 0,
            'full_updates': 0,
            'delta_updates': 0,
            'clients_connected': 0,
            'last_stats_time': time.time()
        }
        self._stats_lock = threading.Lock()

        # 回调
        self.device_manager.set_status_callback(self._on_device_status_change)

        # 初始化序列号
        self._init_sequences()

        # 启动发送线程
        self._running = False
        self._sending_thread: Optional[threading.Thread] = None
        self.start_sending_thread()

    def _init_sequences(self):
        """初始化序列号"""
        for device_id in self.device_manager.devices:
            self._sequence_counter[device_id] = 0

    def _get_next_sequence(self, device_id: str) -> int:
        """获取下一个序列号"""
        if device_id not in self._sequence_counter:
            self._sequence_counter[device_id] = 0
        self._sequence_counter[device_id] += 1
        return self._sequence_counter[device_id]

    def _on_batch_send(self, packet: DataPacket):
        """批量发送回调"""
        try:
            # 准备发送数据
            payload = packet.data
            if isinstance(payload, bytes):
                # 压缩数据
                import base64
                payload = {
                    '_compressed': True,
                    '_data': base64.b64encode(payload).decode('ascii')
                }

            send_data = {
                'type': 'batch',
                'device_id': packet.device_id,
                'sequence': packet.sequence,
                'timestamp': packet.timestamp,
                'count': len(packet.data) if isinstance(packet.data, list) else 1,
                'compressed': packet.compressed,
                'size': packet.size_bytes,
                'payload': payload
            }

            self.socketio.emit('data', send_data)

            # 更新统计
            with self._stats_lock:
                self._stats['packets_sent'] += 1
                self._stats['bytes_sent'] += packet.size_bytes

        except Exception as e:
            print(f"Batch send error: {e}")

    def _on_device_status_change(self, device_id: str, connected: bool, message: str):
        """设备状态变更回调"""
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
        print(f"[OptimizedSocketIO] Device status: {device_id} - {'connected' if connected else 'disconnected'}")

    def register_events(self):
        """注册Socket.IO事件"""

        @self.socketio.on('connect')
        def handle_connect():
            sid = request.sid
            client_id = request.args.get('clientId', sid)

            print('[OptimizedSocketIO] Client connected:', client_id)

            # 注册客户端
            self.subscription_manager.add_client(sid, client_id)

            # 发送客户端配置
            self.socketio.emit('client_config', self.socketio_config.to_dict(), to=sid)

            # 发送设备状态
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

            with self._stats_lock:
                self._stats['clients_connected'] += 1

        @self.socketio.on('disconnect')
        def handle_disconnect():
            sid = request.sid
            client = self.subscription_manager.get_client(sid)
            client_id = client.client_id if client else sid

            print(f'[OptimizedSocketIO] Client disconnected: {client_id}')
            self.subscription_manager.remove_client(sid)

            with self._stats_lock:
                self._stats['clients_connected'] = max(0, self._stats['clients_connected'] - 1)

        @self.socketio.on('subscribe')
        def handle_subscribe(data):
            """订阅设备数据"""
            sid = request.sid
            devices = data.get('devices', [])
            tags = data.get('tags', [])
            subscribe_all_devices = data.get('subscribeAllDevices', True)
            subscribe_all_tags = data.get('subscribeAllTags', True)

            self.subscription_manager.set_subscribe_all_devices(sid, subscribe_all_devices)
            self.subscription_manager.set_subscribe_all_tags(sid, subscribe_all_tags)

            for device_id in devices:
                self.subscription_manager.subscribe_to_device(sid, device_id)

            for tag_name in tags:
                self.subscription_manager.subscribe_to_tag(sid, tag_name)

            self.socketio.emit('subscription_updated', {
                'success': True,
                'devices': devices,
                'tags': tags
            }, to=sid)

        @self.socketio.on('unsubscribe')
        def handle_unsubscribe(data):
            """取消订阅"""
            sid = request.sid
            devices = data.get('devices', [])
            tags = data.get('tags', [])

            for device_id in devices:
                self.subscription_manager.unsubscribe_from_device(sid, device_id)

            for tag_name in tags:
                self.subscription_manager.unsubscribe_from_tag(sid, tag_name)

        @self.socketio.on('request_full_snapshot')
        def handle_request_full_snapshot(data):
            """请求全量快照"""
            sid = request.sid
            device_id = data.get('deviceId')

            print(f"[OptimizedSocketIO] Full snapshot requested for: {device_id}")

            # 清除增量状态
            if device_id:
                self.incremental_manager.clear_device(device_id)

            device_data_map = self.data_processor.prepare_socketio_data()

            if device_id in device_data_map:
                full_data = device_data_map[device_id]
                full_data['update_type'] = 'full'

                packet = self.data_packer.create_packet(
                    packet_type='data',
                    device_id=device_id,
                    payload=full_data,
                    sequence=self._get_next_sequence(device_id)
                )

                self.socketio.emit('data', packet, to=sid)

                with self._stats_lock:
                    self._stats['full_updates'] += 1

                print(f"[OptimizedSocketIO] Sent full snapshot for {device_id}")

        @self.socketio.on('request_stats')
        def handle_request_stats():
            """请求性能统计"""
            sid = request.sid
            stats = self.get_stats()
            batch_stats = self.batch_processor.get_stats()

            self.socketio.emit('server_stats', {
                **stats,
                'batch': batch_stats
            }, to=sid)

        @self.socketio.on('ping')
        def handle_ping():
            """心跳响应"""
            return {'timestamp': time.time(), 'server_time': time.time()}

    def start_sending_thread(self):
        """启动数据发送线程"""
        self._running = True

        def sending_loop():
            while self._running:
                try:
                    # 检查设备状态
                    self._check_and_send_device_status()

                    # 获取数据
                    device_data_map = self.data_processor.prepare_socketio_data()

                    # 处理每个设备的数据
                    for device_id, full_data in device_data_map.items():
                        current_values = full_data.get('current_values', {})

                        if not current_values:
                            continue

                        sequence = self._get_next_sequence(device_id)

                        # 智能更新策略
                        should_send_full = (
                            sequence % self.socketio_config.FULL_UPDATE_INTERVAL == 0 or
                            not self.socketio_config.ENABLE_DELTA_UPDATES
                        )

                        if should_send_full:
                            # 全量更新
                            packet_data = {
                                'device_id': device_id,
                                'device_name': full_data.get('device_name', device_id),
                                'current_values': current_values,
                                'update_type': 'full',
                                'sequence': sequence
                            }

                            with self._stats_lock:
                                self._stats['full_updates'] += 1

                        else:
                            # 增量更新
                            delta_values = self.incremental_manager.update(
                                device_id, current_values
                            )

                            if not delta_values:
                                continue  # 没有变化

                            packet_data = {
                                'device_id': device_id,
                                'device_name': full_data.get('device_name', device_id),
                                'current_values': delta_values,
                                'update_type': 'delta',
                                'sequence': sequence
                            }

                            with self._stats_lock:
                                self._stats['delta_updates'] += 1

                        # 创建并发送包
                        packet = self.data_packer.create_packet(
                            packet_type='data',
                            device_id=device_id,
                            payload=packet_data,
                            sequence=sequence
                        )

                        self.socketio.emit('data', packet)

                    # 发送故障状态
                    self._send_pending_anomalies()

                except Exception as e:
                    print(f'Data sending error: {e}')
                    import traceback
                    traceback.print_exc()

                # 使用配置的采样间隔
                time.sleep(config.DATA_SAMPLING_INTERVAL / 1000)

        self._sending_thread = threading.Thread(target=sending_loop, daemon=True)
        self._sending_thread.start()
        print('[OptimizedSocketIO] Sending thread started')

    def _check_and_send_device_status(self):
        """检查并发送设备状态"""
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

    def _send_pending_anomalies(self):
        """发送待处理的异常"""
        anomalies = self.data_processor.get_pending_anomalies()
        if anomalies:
            for anomaly in anomalies:
                packet = self.data_packer.create_packet(
                    packet_type='anomaly',
                    device_id=anomaly.get('device_id', 'unknown'),
                    payload=anomaly
                )
                self.socketio.emit('anomaly', packet)

    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        with self._stats_lock:
            stats = self._stats.copy()

            # 计算时间间隔
            time_elapsed = time.time() - stats['last_stats_time']
            if time_elapsed > 0:
                stats['packets_per_second'] = stats['packets_sent'] / time_elapsed
                stats['bytes_per_second'] = stats['bytes_sent'] / time_elapsed

            return stats

    def stop_sending_thread(self):
        """停止发送线程"""
        self._running = False
        self.batch_processor.stop()

        if self._sending_thread:
            self._sending_thread.join(timeout=2)


def create_optimized_socketio_handler(socketio: SocketIO,
                                      device_manager: DeviceManager,
                                      data_processor: DataProcessor) -> OptimizedSocketIOHandler:
    """创建优化的Socket.IO处理器"""
    return OptimizedSocketIOHandler(socketio, device_manager, data_processor)
