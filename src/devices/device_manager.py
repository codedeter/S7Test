import time
import threading
import struct
import sys
import os
import io
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import redirect_stderr

import snap7
from snap7.util import get_bool, get_int, get_dint, get_real, set_bool, set_int, set_dint, set_real

from .device_config import (
    DeviceConfig, DeviceStatus, DeviceType,
    ConnectionStatus, DataBlock, AreaVariable, DisconnectionRecord
)


@dataclass
class CollectedData:
    device_id: str
    device_name: str
    timestamp: float
    data: List[Dict[str, Any]]
    connected: bool


@dataclass
class BreakpointData:
    device_id: str
    timestamp: float
    data: List[Dict[str, Any]]
    quality: int = 0


class PLCClient:
    def __init__(self, config: DeviceConfig):
        self.config = config
        self.client = snap7.client.Client()
        self.connected = False
        self.connection_attempts = 0
        self.last_connection_time = None
        self.last_disconnect_time = None
        self._lock = threading.Lock()
        self._last_error = None

    def connect(self) -> bool:
        with self._lock:
            try:
                self._last_error = None
                
                self.client.set_connection_type(3)
                
                devnull = io.StringIO()
                with redirect_stderr(devnull):
                    self.client.connect(
                        self.config.ip_address,
                        self.config.rack,
                        self.config.slot
                    )
                
                self.connected = True
                self.connection_attempts = 0
                self.last_connection_time = time.time()
                print(f"[{self.config.device_id}] Connection successful to {self.config.ip_address}")
                return True
                
            except Exception as e:
                self.connected = False
                self.connection_attempts += 1
                self._last_error = str(e)
                print(f"[{self.config.device_id}] Connection failed (attempt {self.connection_attempts}): {e}")
                return False

    def disconnect(self):
        with self._lock:
            try:
                self.client.disconnect()
            except Exception as e:
                print(f"[{self.config.device_id}] Disconnect warning: {e}")
            finally:
                self.connected = False
                self.last_disconnect_time = time.time()

    def reconnect(self) -> bool:
        self.disconnect()
        base_interval = self.config.retry_interval / 1000
        
        if self.config.reconnect_backoff_enabled and self.connection_attempts > 0:
            backoff_factor = min(2 ** (self.connection_attempts - 1), 32)
            wait_time = base_interval * backoff_factor
        else:
            wait_time = base_interval
        
        print(f"[{self.config.device_id}] Waiting {wait_time:.2f}s before reconnect attempt {self.connection_attempts + 1}")
        time.sleep(wait_time)
        
        return self.connect()

    def check_connection(self) -> bool:
        with self._lock:
            if not self.connected:
                return False
            try:
                self.connected = self.client.get_connected()
                return self.connected
            except Exception as e:
                self.connected = False
                return False

    def read_db(self, db_number: int, start: int, size: int) -> Optional[bytes]:
        with self._lock:
            if not self.connected:
                try:
                    self.connected = self.client.get_connected()
                except:
                    self.connected = False
                if not self.connected:
                    return None
            try:
                devnull = io.StringIO()
                with redirect_stderr(devnull):
                    data = self.client.db_read(db_number, start, size)
                return bytes(data)
            except Exception as e:
                error_str = str(e)
                if "Address" in error_str or "range" in error_str or "CPU" in error_str:
                    return None
                self.connected = False
                self._last_error = error_str
                return None

    def read_m(self, start: int, size: int) -> Optional[bytes]:
        with self._lock:
            if not self.connected:
                return None
            try:
                data = self.client.mb_read(start, size)
                return bytes(data)
            except Exception as e:
                print(f"[{self.config.device_id}] Read M area failed: {e}")
                return None

    def read_i(self, start: int, size: int) -> Optional[bytes]:
        with self._lock:
            if not self.connected:
                return None
            try:
                data = self.client.eb_read(start, size)
                return bytes(data)
            except Exception as e:
                print(f"[{self.config.device_id}] Read I area failed: {e}")
                return None

    def read_q(self, start: int, size: int) -> Optional[bytes]:
        with self._lock:
            if not self.connected:
                return None
            try:
                data = self.client.ab_read(start, size)
                return bytes(data)
            except Exception as e:
                print(f"[{self.config.device_id}] Read Q area failed: {e}")
                return None

    def read_bool(self, db_number: int, start: int, bit_offset: int) -> Optional[bool]:
        data = self.read_db(db_number, start, 1)
        if data:
            return get_bool(data, start, bit_offset)
        return None

    def read_int(self, db_number: int, start: int) -> Optional[int]:
        data = self.read_db(db_number, start, 2)
        if data:
            return get_int(data, start)
        return None

    def read_dint(self, db_number: int, start: int) -> Optional[int]:
        data = self.read_db(db_number, start, 4)
        if data:
            return get_dint(data, start)
        return None

    def read_real(self, db_number: int, start: int) -> Optional[float]:
        data = self.read_db(db_number, start, 4)
        if data:
            return get_real(data, start)
        return None

    def get_last_error(self) -> Optional[str]:
        return self._last_error


class DeviceCollector:
    def __init__(self, config: DeviceConfig, client: PLCClient):
        self.config = config
        self.client = client
        self._init_data_mappings()
        self.last_data_cache: List[Dict[str, Any]] = []

    def _init_data_mappings(self):
        self.db_mappings: Dict[int, Dict[int, List[tuple]]] = {}
        self.db_type_vars: Dict[int, Dict[str, List[tuple]]] = {}

        for db in self.config.data_blocks:
            self.db_mappings[db.number] = {}
            self.db_type_vars[db.number] = {}

            for var in db.variables:
                if var.address not in self.db_mappings[db.number]:
                    self.db_mappings[db.number][var.address] = []

                if var.bit_offset is not None:
                    self.db_mappings[db.number][var.address].append(
                        (var.bit_offset, var.name)
                    )

                type_key = var.data_type.upper()
                if type_key not in self.db_type_vars[db.number]:
                    self.db_type_vars[db.number][type_key] = []
                self.db_type_vars[db.number][type_key].append(
                    (var.address, var.name)
                )

        self.m_vars = [(v.name, v.area, v.offset, v.data_type, v.bit_offset)
                       for v in self.config.m_variables]
        self.i_vars = [(v.name, v.area, v.offset, v.data_type, v.bit_offset)
                       for v in self.config.i_variables]
        self.q_vars = [(v.name, v.area, v.offset, v.data_type, v.bit_offset)
                       for v in self.config.q_variables]

    def collect_all_data(self) -> List[Dict[str, Any]]:
        data = []

        for db in self.config.data_blocks:
            data.extend(self._read_data_block(db))

        data.extend(self._read_area(self.client.read_m, self.m_vars))
        data.extend(self._read_area(self.client.read_i, self.i_vars))
        data.extend(self._read_area(self.client.read_q, self.q_vars))

        self.last_data_cache = data.copy()
        return data

    def get_cached_data(self) -> List[Dict[str, Any]]:
        return self.last_data_cache.copy()

    def _read_data_block(self, db: DataBlock) -> List[Dict[str, Any]]:
        data = []
        if db.number not in self.db_mappings:
            return data

        mapping = self.db_mappings[db.number]
        type_vars = self.db_type_vars.get(db.number, {})

        max_addr = max((addr for addr in mapping.keys()), default=0)
        read_size = min(max_addr + 20, 256)

        if db.size > 0:
            read_size = db.size

        db_data = self.client.read_db(db.number, 0, read_size)
        if not db_data:
            return data

        for addr, bits in mapping.items():
            if addr < len(db_data):
                for bit_offset, var_name in bits:
                    val = (db_data[addr] >> bit_offset) & 0x01
                    data.append({
                        'db_number': db.number,
                        'address': addr * 8 + bit_offset,
                        'tag_name': var_name,
                        'value': val,
                        'quality': 1
                    })

        for dtype, vars_list in type_vars.items():
            for addr, var_name in vars_list:
                if dtype in ('INT', 'DINT', 'REAL'):
                    if addr + 4 <= len(db_data):
                        if dtype == 'INT':
                            val = int.from_bytes(db_data[addr:addr+2], 'big', signed=True)
                        elif dtype == 'DINT':
                            val = int.from_bytes(db_data[addr:addr+4], 'big', signed=True)
                        elif dtype == 'REAL':
                            val = struct.unpack('>f', db_data[addr:addr+4])[0]

                        data.append({
                            'db_number': db.number,
                            'address': addr,
                            'tag_name': var_name,
                            'value': val,
                            'quality': 1
                        })

        return data

    def _read_area(self, read_func, vars_cache) -> List[Dict[str, Any]]:
        data = []
        if not vars_cache:
            return data

        max_offset = max((v[2] for v in vars_cache), default=0)
        read_size = max_offset + 20

        if read_func == self.client.read_m:
            area_data = self.client.read_m(0, read_size)
        elif read_func == self.client.read_i:
            area_data = self.client.read_i(0, read_size)
        elif read_func == self.client.read_q:
            area_data = self.client.read_q(0, read_size)
        else:
            return data

        if not area_data:
            return data

        for name, area, offset, dtype, bit in vars_cache:
            if dtype.upper() == 'BOOL' and offset < len(area_data):
                val = (area_data[offset] >> bit) & 0x01
                data.append({
                    'db_number': 0,
                    'address': offset * 8 + bit,
                    'tag_name': name,
                    'value': val,
                    'quality': 1
                })
            elif dtype.upper() in ('BYTE', 'WORD', 'DWORD') and offset < len(area_data):
                data.append({
                    'db_number': 0,
                    'address': offset,
                    'tag_name': name,
                    'value': area_data[offset],
                    'quality': 1
                })

        return data


class DeviceManager:
    def __init__(self):
        self.devices: Dict[str, DeviceConfig] = {}
        self.clients: Dict[str, PLCClient] = {}
        self.collectors: Dict[str, DeviceCollector] = {}
        self.statuses: Dict[str, DeviceStatus] = {}
        self._lock = threading.Lock()
        self._data_callback: Optional[Callable] = None
        self._status_callback: Optional[Callable] = None
        self._running = False
        self._collection_thread: Optional[threading.Thread] = None
        self._reconnect_threads: Dict[str, threading.Thread] = {}
        self._reconnecting: Dict[str, bool] = {}
        self._breakpoint_data: List[BreakpointData] = []
        self._max_breakpoint_count = 1000
        self._thread_pool = ThreadPoolExecutor(max_workers=10)

    def add_device(self, config: DeviceConfig) -> bool:
        with self._lock:
            if config.device_id in self.devices:
                print(f"Device {config.device_id} already exists")
                return False

            self.devices[config.device_id] = config
            self.clients[config.device_id] = PLCClient(config)
            self.collectors[config.device_id] = DeviceCollector(config, self.clients[config.device_id])
            self.statuses[config.device_id] = DeviceStatus(
                device_id=config.device_id,
                status=ConnectionStatus.DISCONNECTED,
                connected=False
            )
            self._reconnecting[config.device_id] = False

            print(f"Device {config.device_id} ({config.device_name}) added")
            return True

    def remove_device(self, device_id: str) -> bool:
        with self._lock:
            if device_id not in self.devices:
                return False

            if device_id in self.clients:
                self.clients[device_id].disconnect()

            if device_id in self._reconnect_threads:
                self._reconnecting[device_id] = False
                if self._reconnect_threads[device_id].is_alive():
                    self._reconnect_threads[device_id].join(timeout=2)

            del self.devices[device_id]
            del self.clients[device_id]
            del self.collectors[device_id]
            del self.statuses[device_id]
            del self._reconnecting[device_id]

            return True

    def _on_connection_lost(self, device_id: str, reason: str = ""):
        with self._lock:
            if device_id in self.statuses:
                self.statuses[device_id].start_disconnection()
                self.statuses[device_id].last_error = reason
                self.statuses[device_id].consecutive_failure_count += 1
                
                collector = self.collectors.get(device_id)
                if collector:
                    cached_data = collector.get_cached_data()
                    if cached_data:
                        self._save_breakpoint_data(device_id, cached_data, quality=0)

        print(f"[{device_id}] Connection lost: {reason}")
        
        if self._status_callback:
            try:
                self._status_callback(device_id, False, reason)
            except Exception as e:
                print(f"[{device_id}] Status callback error: {e}")

    def _on_connection_restored(self, device_id: str):
        with self._lock:
            if device_id in self.statuses:
                duration = self.statuses[device_id].get_current_disconnection_duration()
                self.statuses[device_id].end_disconnection()
                self.statuses[device_id].last_update = time.time()
                
                print(f"[{device_id}] Connection restored after {duration:.2f} seconds")
                
                if self._status_callback:
                    try:
                        self._status_callback(device_id, True, f"Reconnected after {duration:.2f}s")
                    except Exception as e:
                        print(f"[{device_id}] Status callback error: {e}")

    def _save_breakpoint_data(self, device_id: str, data: List[Dict[str, Any]], quality: int = 0):
        breakpoint_data = BreakpointData(
            device_id=device_id,
            timestamp=time.time(),
            data=data,
            quality=quality
        )
        self._breakpoint_data.append(breakpoint_data)
        
        if len(self._breakpoint_data) > self._max_breakpoint_count:
            self._breakpoint_data.pop(0)

    def get_breakpoint_data(self, device_id: str = None) -> List[BreakpointData]:
        if device_id:
            return [b for b in self._breakpoint_data if b.device_id == device_id]
        return self._breakpoint_data.copy()

    def connect_device(self, device_id: str) -> bool:
        with self._lock:
            if device_id not in self.clients:
                print(f"[{device_id}] Device not found")
                return False

            client = self.clients[device_id]
            self.statuses[device_id].status = ConnectionStatus.CONNECTING

        try:
            success = client.connect()
            
            with self._lock:
                if success:
                    self.statuses[device_id].status = ConnectionStatus.CONNECTED
                    self.statuses[device_id].connected = True
                    self.statuses[device_id].last_update = time.time()
                    print(f"[{device_id}] Device connected successfully")
                    return True
                else:
                    # 连接失败后保持 CONNECTING 状态，因为会启动重连循环
                    self.statuses[device_id].status = ConnectionStatus.CONNECTING
                    self.statuses[device_id].connected = False
                    self._on_connection_lost(device_id, f"Connection failed: {client.get_last_error()}")
                    self._start_reconnect_loop(device_id)
                    return False
                    
        except Exception as e:
            with self._lock:
                # 异常后也保持 CONNECTING 状态
                self.statuses[device_id].status = ConnectionStatus.CONNECTING
                self.statuses[device_id].connected = False
                self._on_connection_lost(device_id, f"Connection exception: {e}")
                self._start_reconnect_loop(device_id)
            return False

    def _start_reconnect_loop(self, device_id: str):
        if self._reconnecting.get(device_id, False):
            return

        self._reconnecting[device_id] = True
        
        # 更新状态为"正在连接"
        with self._lock:
            if device_id in self.statuses:
                self.statuses[device_id].status = ConnectionStatus.CONNECTING
        
        def reconnect_loop():
            config = self.devices.get(device_id)
            if not config:
                return

            max_attempts = config.max_retry_attempts
            
            while self._reconnecting.get(device_id, False):
                try:
                    client = self.clients.get(device_id)
                    if not client:
                        break

                    print(f"[{device_id}] Attempting reconnect...")
                    
                    if client.reconnect():
                        self._on_connection_restored(device_id)
                        self._reconnecting[device_id] = False
                        break
                    
                    if max_attempts > 0 and client.connection_attempts >= max_attempts:
                        print(f"[{device_id}] Max reconnect attempts ({max_attempts}) reached")
                        # 达到最大尝试次数后，状态设置为 ERROR 而不是退出
                        with self._lock:
                            if device_id in self.statuses:
                                self.statuses[device_id].status = ConnectionStatus.ERROR
                        self._reconnecting[device_id] = False
                        break
                        
                except Exception as e:
                    print(f"[{device_id}] Reconnect error: {e}")
                # 每次尝试后都等待一下
                try:
                    time.sleep(config.retry_interval / 1000)
                except:
                    time.sleep(3)

        thread = threading.Thread(target=reconnect_loop, daemon=True)
        self._reconnect_threads[device_id] = thread
        thread.start()

    def connect_all(self) -> Dict[str, bool]:
        results = {}
        futures = {}
        
        for device_id in self.devices:
            future = self._thread_pool.submit(self.connect_device, device_id)
            futures[future] = device_id
        
        for future in as_completed(futures):
            device_id = futures[future]
            try:
                results[device_id] = future.result(timeout=30)
            except Exception as e:
                results[device_id] = False
                print(f"[{device_id}] Connection timeout: {e}")
        
        return results

    def disconnect_device(self, device_id: str):
        with self._lock:
            if device_id in self.clients:
                self._reconnecting[device_id] = False
                if device_id in self._reconnect_threads:
                    if self._reconnect_threads[device_id].is_alive():
                        self._reconnect_threads[device_id].join(timeout=2)
                
                self.clients[device_id].disconnect()
                self._on_connection_lost(device_id, "Manually disconnected")
                self.statuses[device_id].status = ConnectionStatus.DISCONNECTED
                self.statuses[device_id].connected = False

    def disconnect_all(self):
        for device_id in self.devices:
            self.disconnect_device(device_id)

    def collect_data(self, device_id: str) -> Optional[CollectedData]:
        with self._lock:
            if device_id not in self.devices:
                return None

            config = self.devices[device_id]
            collector = self.collectors.get(device_id)
            client = self.clients.get(device_id)

            if not collector or not client:
                print(f"[{device_id}] No collector or client")
                return None

        if not client.connected:
            cached_data = collector.get_cached_data()
            if cached_data:
                return CollectedData(
                    device_id=device_id,
                    device_name=config.device_name,
                    timestamp=time.time(),
                    data=cached_data,
                    connected=False
                )
            print(f"[{device_id}] Not connected and no cached data")
            return None

        try:
            data = collector.collect_all_data()
            print(f"[{device_id}] Collected {len(data)} data points from PLC")

            with self._lock:
                self.statuses[device_id].data_count += len(data)
                self.statuses[device_id].last_update = time.time()

            return CollectedData(
                device_id=device_id,
                device_name=config.device_name,
                timestamp=time.time(),
                data=data,
                connected=client.connected
            )
        except Exception as e:
            print(f"[{device_id}] Error collecting data: {e}")
            self._on_connection_lost(device_id, str(e))
            if not self._reconnecting.get(device_id, False):
                self._start_reconnect_loop(device_id)
            
            cached_data = collector.get_cached_data()
            if cached_data:
                return CollectedData(
                    device_id=device_id,
                    device_name=config.device_name,
                    timestamp=time.time(),
                    data=cached_data,
                    connected=False
                )
            return None

    def collect_all_data(self) -> List[CollectedData]:
        results = []
        for device_id in list(self.devices.keys()):
            try:
                collected = self.collect_data(device_id)
                if collected:
                    results.append(collected)
                    print(f"[DeviceManager] {device_id}: collected {len(collected.data)} points, connected={collected.connected}")
            except Exception as e:
                print(f"[DeviceManager] {device_id}: collection error: {e}")
        return results

    def set_data_callback(self, callback: Callable[[List[CollectedData]], None]):
        self._data_callback = callback

    def set_status_callback(self, callback: Callable[[str, bool, str], None]):
        self._status_callback = callback

    def start_collection(self, interval: float = 0.1):
        self._running = True

        def collection_loop():
            while self._running:
                try:
                    all_data = self.collect_all_data()
                    if self._data_callback and all_data:
                        self._data_callback(all_data)
                except Exception as e:
                    print(f"Collection error: {e}")

                time.sleep(interval)

        self._collection_thread = threading.Thread(target=collection_loop, daemon=True)
        self._collection_thread.start()

    def stop_collection(self):
        self._running = False
        if self._collection_thread:
            self._collection_thread.join(timeout=2)
        
        for device_id in self._reconnecting:
            self._reconnecting[device_id] = False
        
        for thread in self._reconnect_threads.values():
            if thread.is_alive():
                thread.join(timeout=2)

    def get_device_status(self, device_id: str) -> Optional[DeviceStatus]:
        return self.statuses.get(device_id)

    def get_all_statuses(self) -> Dict[str, DeviceStatus]:
        return self.statuses.copy()

    def get_device_config(self, device_id: str) -> Optional[DeviceConfig]:
        return self.devices.get(device_id)

    def list_devices(self) -> List[Dict[str, Any]]:
        result = []
        for d in self.devices.values():
            status = self.statuses.get(d.device_id)
            status_info = {
                'device_id': d.device_id,
                'device_name': d.device_name,
                'device_type': d.device_type.value,
                'ip_address': d.ip_address,
                'connection_string': d.connection_string,
                'enabled': d.enabled,
                'status': status.status.value if status else 'unknown',
                'connected': status.connected if status else False,
            }
            if status:
                status_info.update({
                    'last_disconnection_duration': status.last_disconnection_duration,
                    'reconnection_count': status.reconnection_count,
                    'total_disconnection_duration': status.total_disconnection_duration,
                    'last_error': status.last_error,
                })
            result.append(status_info)
        return result


def create_device_manager() -> DeviceManager:
    return DeviceManager()