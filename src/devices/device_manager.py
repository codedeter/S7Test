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
    ConnectionStatus, DataBlock, AreaVariable, DisconnectionRecord, NetworkInterface
)
from .connection_manager import ConnectionPool, ConnectionState, ConnectionConfig, create_connection_pool
from .network_monitor import get_network_monitor, NetworkStatus
from src.utils import get_error_handler, ErrorType, ErrorLevel, safe_execute


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
        self._lock = threading.RLock()  # 使用可重入锁，避免死�?
        self._last_error = None
        
        self._current_ip = config.ip_address
        self._ip_index = 0
        self._last_switch_time = None
        self._switch_count = 0
        self._connection_history = []
        
        self._latency_samples = []
        self._max_latency_samples = 10
    
    def _get_next_ip(self) -> str:
        ips = self.config.get_preferred_ips()
        if not ips:
            return self.config.ip_address
        
        self._ip_index = (self._ip_index + 1) % len(ips)
        return ips[self._ip_index]
    
    def _try_connect_to_ip(self, ip: str, timeout: int = 3) -> bool:
        try:
            self._last_error = None
            self.client.set_connection_type(3)
            
            import socket
            old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(timeout)
            
            try:
                devnull = io.StringIO()
                with redirect_stderr(devnull):
                    self.client.connect(ip, self.config.rack, self.config.slot)
                return True
            finally:
                socket.setdefaulttimeout(old_timeout)
                
        except socket.timeout:
            self._last_error = f"Connection timeout ({timeout}s)"
            return False
        except Exception as e:
            self._last_error = str(e)
            return False
    
    def connect(self) -> bool:
        with self._lock:
            if self.connected:
                return True
            
            ips = self.config.get_preferred_ips()
            if not ips:
                return False
        
        result = [False]
        error = [None]
        
        def connect_task():
            try:
                for ip in ips:
                    try:
                        if self._try_connect_to_ip(ip):
                            with self._lock:
                                self.connected = True
                                self.connection_attempts = 0
                                self.last_connection_time = time.time()
                                self._current_ip = ip
                                self._ip_index = ips.index(ip)
                                self._connection_history.append((ip, time.time(), True))
                            result[0] = True
                            return
                        else:
                            with self._lock:
                                self.connection_attempts += 1
                                self._connection_history.append((ip, time.time(), False))
                    except Exception as e:
                        with self._lock:
                            self.connection_attempts += 1
                            self._last_error = str(e)
                            self._connection_history.append((ip, time.time(), False))
            except Exception as e:
                error[0] = e
        
        connect_thread = threading.Thread(target=connect_task, daemon=True)
        connect_thread.start()
        connect_thread.join(timeout=15)  # 15秒超�?
        
        if connect_thread.is_alive():
            return False
        
        if error[0]:
            return False
        
        with self._lock:
            self.connected = result[0]
        
        return result[0]
    
    def connect_with_ip(self, ip: str) -> bool:
        with self._lock:
            if self.connected:
                self.disconnect()
            
            try:
                if self._try_connect_to_ip(ip):
                    self.connected = True
                    self.connection_attempts = 0
                    self.last_connection_time = time.time()
                    self._current_ip = ip
                    self._connection_history.append((ip, time.time(), True))
                    return True
                else:
                    self.connection_attempts += 1
                    self._connection_history.append((ip, time.time(), False))
                    return False
            except Exception as e:
                self.connection_attempts += 1
                self._last_error = str(e)
                self._connection_history.append((ip, time.time(), False))
                return False
    
    def disconnect(self):
        with self._lock:
            try:
                self.client.disconnect()
            except Exception:
                pass
            finally:
                self.connected = False
                self.last_disconnect_time = time.time()
                self._last_error = None
    
    def reconnect(self) -> bool:
        self.disconnect()
        base_interval = self.config.retry_interval / 1000
        
        if self.config.reconnect_backoff_enabled and self.connection_attempts > 0:
            backoff_factor = min(2 ** (self.connection_attempts - 1), 32)
            wait_time = base_interval * backoff_factor
        else:
            wait_time = base_interval
        
        time.sleep(wait_time)
        
        return self.connect()
    
    def switch_network(self) -> bool:
        if not self.connected:
            return self.connect()
        
        with self._lock:
            ips = self.config.get_preferred_ips()
            if len(ips) < 2:
                return False
            
            if self._last_switch_time and (time.time() - self._last_switch_time) < (self.config.network_switch_timeout / 1000):
                return False
            
            old_ip = self._current_ip
            new_ip = self._get_next_ip()
            
            if new_ip == old_ip:
                new_ip = self._get_next_ip()
            
            
            try:
                self.disconnect()
                
                time.sleep(0.5)
                
                if self._try_connect_to_ip(new_ip):
                    self.connected = True
                    self.connection_attempts = 0
                    self.last_connection_time = time.time()
                    self._current_ip = new_ip
                    self._last_switch_time = time.time()
                    self._switch_count += 1
                    self._connection_history.append((new_ip, time.time(), True))
                    return True
                else:
                    if self._try_connect_to_ip(old_ip):
                        self.connected = True
                        self._current_ip = old_ip
                        self._connection_history.append((old_ip, time.time(), True))
                        return True
                    else:
                        self.connected = False
                        return False
            except Exception as e:
                self.connected = False
                return False
    
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
    
    def _record_latency(self, latency_ms: float):
        self._latency_samples.append(latency_ms)
        if len(self._latency_samples) > self._max_latency_samples:
            self._latency_samples.pop(0)
    
    def get_average_latency(self) -> float:
        if not self._latency_samples:
            return 0.0
        return sum(self._latency_samples) / len(self._latency_samples)
    
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
                start_time = time.time()
                devnull = io.StringIO()
                with redirect_stderr(devnull):
                    data = self.client.db_read(db_number, start, size)
                latency_ms = (time.time() - start_time) * 1000
                self._record_latency(latency_ms)
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
                return None
    
    def read_i(self, start: int, size: int) -> Optional[bytes]:
        with self._lock:
            if not self.connected:
                return None
            try:
                data = self.client.eb_read(start, size)
                return bytes(data)
            except Exception as e:
                return None
    
    def read_q(self, start: int, size: int) -> Optional[bytes]:
        with self._lock:
            if not self.connected:
                return None
            try:
                data = self.client.ab_read(start, size)
                return bytes(data)
            except Exception as e:
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
    
    def get_current_ip(self) -> str:
        return self._current_ip
    
    def get_switch_count(self) -> int:
        return self._switch_count
    
    def get_connection_history(self) -> list:
        return self._connection_history.copy()


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
        
        # 计算需要读取的精确大小
        max_addr = 0
        
        # 检�?bool 变量地址
        for addr in mapping.keys():
            if addr > max_addr:
                max_addr = addr
        
        # 检查其他类型变量的地址（考虑数据类型长度�?
        type_length_map = {'INT': 2, 'DINT': 4, 'REAL': 4}
        for dtype, vars_list in type_vars.items():
            for addr, var_name in vars_list:
                length = type_length_map.get(dtype, 1)
                if addr + length > max_addr:
                    max_addr = addr + length
        
        # 确定读取大小，使用更保守的策略
        read_size = min(max_addr + 5, 128)  # 安全上限 128 字节
        if db.size > 0:
            read_size = min(db.size, 128)
        
        # 读取数据，带错误处理和安全策�?
        db_data = None
        current_size = read_size
        while current_size > 0 and db_data is None:
            try:
                db_data = self.client.read_db(db.number, 0, current_size)
            except Exception:
                                # 失败，尝试读取更小的大小
                current_size = max(1, current_size // 2)
        
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
        
        # 计算需要读取的精确大小，考虑数据类型长度
        max_offset = 0
        area_type_length_map = {'BYTE': 1, 'WORD': 2, 'DWORD': 4}
        
        for v in vars_cache:
            name, area, offset, dtype, bit = v
            dtype_upper = dtype.upper()
            length = area_type_length_map.get(dtype_upper, 1)
            if offset + length > max_offset:
                max_offset = offset + length
        
        # 安全的读取大小上�?
        max_safe_size = 256
        read_size = min(max_offset + 10, max_safe_size)
        
        # 安全的读取策略：如果失败就逐步减少要读取的大小
        area_data = None
        current_size = read_size
        while current_size > 0 and area_data is None:
            try:
                if read_func == self.client.read_m:
                    area_data = self.client.read_m(0, current_size)
                elif read_func == self.client.read_i:
                    area_data = self.client.read_i(0, current_size)
                elif read_func == self.client.read_q:
                    area_data = self.client.read_q(0, current_size)
                else:
                    break
            except Exception:
                                # 失败，尝试读取更小的大小
                current_size = max(1, current_size // 2)
        
        if not area_data:
            return data
        
        area_type_length_map = {'BYTE': 1, 'WORD': 2, 'DWORD': 4}
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
            elif dtype.upper() in ('BYTE', 'WORD', 'DWORD'):
                dtype_upper = dtype.upper()
                required_len = area_type_length_map.get(dtype_upper, 1)
                if offset + required_len <= len(area_data):
                    if dtype_upper == 'BYTE':
                        val = area_data[offset]
                    elif dtype_upper == 'WORD':
                        val = int.from_bytes(area_data[offset:offset+2], 'big')
                    elif dtype_upper == 'DWORD':
                        val = int.from_bytes(area_data[offset:offset+4], 'big')
                    else:
                        val = area_data[offset]
                    
                    data.append({
                        'db_number': 0,
                        'address': offset,
                        'tag_name': name,
                        'value': val,
                        'quality': 1
                    })
        
        return data


class DeviceManager:
    def __init__(self):
        self.devices: Dict[str, DeviceConfig] = {}
        self.clients: Dict[str, PLCClient] = {}
        self.collectors: Dict[str, DeviceCollector] = {}
        self.statuses: Dict[str, DeviceStatus] = {}
        self._lock = threading.RLock()  # 使用可重入锁，避免死�?
        self._data_callback: Optional[Callable] = None
        self._status_callback: Optional[Callable] = None
        self._running = False
        self._collection_thread: Optional[threading.Thread] = None
        self._reconnect_threads: Dict[str, threading.Thread] = {}
        self._reconnecting: Dict[str, bool] = {}
        self._breakpoint_data: List[BreakpointData] = []
        self._max_breakpoint_count = 1000
        self._thread_pool = ThreadPoolExecutor(max_workers=10)
        
        self._connection_pool = create_connection_pool()
        
        self._network_monitor = get_network_monitor()
        self._network_monitor.add_callback(self._on_network_status_change)
        self._network_monitor.start(check_interval=3.0)
    
    def add_device(self, config: DeviceConfig) -> bool:
        with self._lock:
            if config.device_id in self.devices:
                return False
            
            client = PLCClient(config)
            
            self.devices[config.device_id] = config
            self.clients[config.device_id] = client
            self.collectors[config.device_id] = DeviceCollector(config, client)
            self.statuses[config.device_id] = DeviceStatus(
                device_id=config.device_id,
                status=ConnectionStatus.DISCONNECTED,
                connected=False
            )
            self._reconnecting[config.device_id] = False
            
            self._connection_pool.add_connection(config.device_id, client)
            
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
            
            self._connection_pool.remove_connection(device_id)
            
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
        
        self._connection_pool.set_state(device_id, ConnectionState.RECONNECTING, reason)

        if self._status_callback:
            try:
                self._status_callback(device_id, False, reason)
            except Exception as e:
                pass

    def _on_connection_restored(self, device_id: str):
        with self._lock:
            if device_id in self.statuses:
                duration = self.statuses[device_id].get_current_disconnection_duration()
                self.statuses[device_id].end_disconnection()
                self.statuses[device_id].last_update = time.time()

                if self._status_callback:
                    try:
                        self._status_callback(device_id, True, f"Reconnected after {duration:.2f}s")
                    except Exception as e:
                        pass

        self._connection_pool.set_state(device_id, ConnectionState.CONNECTED, "Connection restored")
    
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
                return False
            
            client = self.clients[device_id]
            self.statuses[device_id].status = ConnectionStatus.CONNECTING
        
        self._connection_pool.set_state(device_id, ConnectionState.CONNECTING)
        
        try:
            success = client.connect()
            
            with self._lock:
                if success:
                    self.statuses[device_id].status = ConnectionStatus.CONNECTED
                    self.statuses[device_id].connected = True
                    self.statuses[device_id].last_update = time.time()
                    self._connection_pool.set_state(device_id, ConnectionState.CONNECTED)
                    return True
                else:
                    self.statuses[device_id].status = ConnectionStatus.CONNECTING
                    self.statuses[device_id].connected = False
                    self._on_connection_lost(device_id, f"Connection failed: {client.get_last_error()}")
                    self._start_reconnect_loop(device_id)
                    return False
                    
        except Exception as e:
            with self._lock:
                self.statuses[device_id].status = ConnectionStatus.CONNECTING
                self.statuses[device_id].connected = False
                self._on_connection_lost(device_id, f"Connection exception: {e}")
                self._start_reconnect_loop(device_id)
            return False
    
    def _start_reconnect_loop(self, device_id: str):
        if self._reconnecting.get(device_id, False):
            return
        
        self._reconnecting[device_id] = True
        
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
                    
                    retry_interval = self._connection_pool.get_retry_interval(client.connection_attempts)
                    time.sleep(retry_interval)
                    
                    
                    if client.connect():
                        self._on_connection_restored(device_id)
                        self._reconnecting[device_id] = False
                        break
                    
                    if max_attempts > 0 and client.connection_attempts >= max_attempts:
                        with self._lock:
                            if device_id in self.statuses:
                                self.statuses[device_id].status = ConnectionStatus.ERROR
                        self._connection_pool.set_state(device_id, ConnectionState.ERROR, "Max retries reached")
                        self._reconnecting[device_id] = False
                        break
                        
                except Exception as e:
                    pass
        
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
                
                self._connection_pool.set_state(device_id, ConnectionState.DISCONNECTED, "Manually disconnected")
    
    def disconnect_all(self):
        for device_id in self.devices:
            self.disconnect_device(device_id)
    
    def collect_data(self, device_id: str) -> Optional[CollectedData]:
        error_handler = get_error_handler()
        
        try:
            with self._lock:
                if device_id not in self.devices:
                    error_handler.log_error(
                        error_type=ErrorType.VALIDATION_ERROR,
                        message=f"Device not found: {device_id}",
                        level=ErrorLevel.WARNING,
                        device_id=device_id
                    )
                    return None
                
                config = self.devices[device_id]
                collector = self.collectors.get(device_id)
                client = self.clients.get(device_id)
                
                if not collector or not client:
                    error_handler.log_error(
                        error_type=ErrorType.CONFIG_ERROR,
                        message=f"No collector or client for device: {device_id}",
                        level=ErrorLevel.WARNING,
                        device_id=device_id
                    )
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
                error_handler.log_error(
                    error_type=ErrorType.CONNECTION_ERROR,
                    message=f"Device not connected and no cached data: {device_id}",
                    level=ErrorLevel.WARNING,
                    device_id=device_id
                )
                return None
    
            # 添加超时保护
            data = None
            data_error = None
            
            def collect_task():
                nonlocal data, data_error
                try:
                    data = safe_execute(
                        collector.collect_all_data,
                        error_type=ErrorType.DATA_READ_ERROR,
                        device_id=device_id
                    )
                except Exception as e:
                    data_error = e
            
            collection_thread = threading.Thread(target=collect_task, daemon=True)
            collection_thread.start()
            collection_thread.join(timeout=10)  # 10秒超�?
            
            if collection_thread.is_alive():
                error_handler.log_error(
                    error_type=ErrorType.DATA_READ_ERROR,
                    message=f"Data collection timeout for device: {device_id}",
                    level=ErrorLevel.WARNING,
                    device_id=device_id
                )
                return None
            
            if data_error:
                error_handler.log_error(
                    error_type=ErrorType.DATA_READ_ERROR,
                    message=f"Error collecting data: {str(data_error)}",
                    level=ErrorLevel.ERROR,
                    device_id=device_id,
                    exception=data_error
                )
                return None
            
            if data is None:
                error_handler.log_error(
                    error_type=ErrorType.DATA_READ_ERROR,
                    message=f"Failed to collect data from device: {device_id}",
                    level=ErrorLevel.ERROR,
                    device_id=device_id
                )
                raise RuntimeError("Data collection returned None")
            
            
            with self._lock:
                self.statuses[device_id].data_count += len(data)
                self.statuses[device_id].last_update = time.time()
            
            self._connection_pool.get_stats(device_id).record_read(True, len(data) * 2)
            
            return CollectedData(
                device_id=device_id,
                device_name=config.device_name,
                timestamp=time.time(),
                data=data,
                connected=client.connected
            )
        
        except Exception as e:
            error_handler.log_error(
                error_type=ErrorType.DATA_READ_ERROR,
                message=f"Error collecting data: {str(e)}",
                level=ErrorLevel.ERROR,
                device_id=device_id,
                exception=e
            )
            
            self._connection_pool.get_stats(device_id).record_read(False)
            self._on_connection_lost(device_id, str(e))
            
            if not self._reconnecting.get(device_id, False):
                self._start_reconnect_loop(device_id)
            
            try:
                collector = self.collectors.get(device_id)
                if collector:
                    cached_data = collector.get_cached_data()
                    if cached_data:
                        return CollectedData(
                            device_id=device_id,
                            device_name=self.devices[device_id].device_name,
                            timestamp=time.time(),
                            data=cached_data,
                            connected=False
                        )
            except Exception as cache_e:
                error_handler.log_error(
                    error_type=ErrorType.DATA_READ_ERROR,
                    message=f"Failed to get cached data: {str(cache_e)}",
                    level=ErrorLevel.WARNING,
                    device_id=device_id
                )
            
            return None
    
    def collect_all_data(self) -> List[CollectedData]:
        results = []
        for device_id in list(self.devices.keys()):
            try:
                collected = self.collect_data(device_id)
                if collected:
                    results.append(collected)
            except Exception:
                pass
        return results
    
    def set_data_callback(self, callback: Callable[[List[CollectedData]], None]):
        self._data_callback = callback
    
    def set_status_callback(self, callback: Callable[[str, bool, str], None]):
        self._status_callback = callback
    
    def start_collection(self, interval: float = 0.1):
        self._running = True
        self._connection_pool.start_health_check()
        
        def collection_loop():
            while self._running:
                try:
                    all_data = self.collect_all_data()
                    if self._data_callback and all_data:
                        self._data_callback(all_data)
                except Exception as e:
                    pass
                
                time.sleep(interval)
        
        self._collection_thread = threading.Thread(target=collection_loop, daemon=True)
        self._collection_thread.start()
    
    def stop_collection(self):
        self._running = False
        self._connection_pool.stop_health_check()
        
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
            pool_stats = self._connection_pool.get_stats(d.device_id)
            
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
            
            if pool_stats:
                status_info.update({
                    'connection_rate': pool_stats.get_connection_rate(),
                    'read_success_rate': pool_stats.get_read_success_rate(),
                    'total_connections': pool_stats.total_connections,
                    'successful_connections': pool_stats.successful_connections,
                    'total_data_reads': pool_stats.total_data_reads,
                    'bytes_read': pool_stats.bytes_read,
                })
            
            result.append(status_info)
        return result
    
    def get_connection_pool_summary(self) -> Dict[str, Any]:
        return self._connection_pool.get_pool_summary()
    
    def get_device_connection_stats(self, device_id: str) -> Optional[Dict[str, Any]]:
        stats = self._connection_pool.get_stats(device_id)
        if stats:
            return {
                'total_connections': stats.total_connections,
                'successful_connections': stats.successful_connections,
                'failed_connections': stats.failed_connections,
                'connection_rate': stats.get_connection_rate(),
                'total_data_reads': stats.total_data_reads,
                'successful_reads': stats.successful_reads,
                'failed_reads': stats.failed_reads,
                'read_success_rate': stats.get_read_success_rate(),
                'bytes_read': stats.bytes_read,
                'total_disconnection_duration': stats.total_disconnection_duration,
            }
        return None


    def _on_network_status_change(self, iface_name: str, status: NetworkStatus, reason: str):
        
        if status == NetworkStatus.DOWN:
            for device_id, client in self.clients.items():
                current_ip = client.get_current_ip()
                config = self.devices.get(device_id)
                
                if config:
                    for iface in config.network_interfaces:
                        if iface.name == iface_name and iface.ip_address == current_ip:
                            if client.connected:
                                client.switch_network()
                            break
    
    def switch_device_network(self, device_id: str) -> bool:
        client = self.clients.get(device_id)
        if not client:
            return False
        
        return client.switch_network()
    
    def connect_device_with_ip(self, device_id: str, ip_address: str) -> bool:
        client = self.clients.get(device_id)
        if not client:
            return False
        
        return client.connect_with_ip(ip_address)
    
    def get_device_network_info(self, device_id: str) -> Optional[Dict[str, Any]]:
        client = self.clients.get(device_id)
        config = self.devices.get(device_id)
        
        if not client or not config:
            return None
        
        return {
            'device_id': device_id,
            'current_ip': client.get_current_ip(),
            'available_ips': config.get_preferred_ips(),
            'switch_count': client.get_switch_count(),
            'average_latency_ms': client.get_average_latency(),
            'network_interfaces': [
                {
                    'name': iface.name,
                    'ip_address': iface.ip_address,
                    'priority': iface.priority,
                    'enabled': iface.enabled
                } for iface in config.network_interfaces
            ],
            'auto_detect_interfaces': config.auto_detect_interfaces,
            'preferred_interface': config.preferred_interface
        }
    
    def get_all_network_interfaces(self) -> List[Dict[str, Any]]:
        interfaces = self._network_monitor.get_all_interface_statuses()
        result = []
        for iface_name, status in interfaces.items():
            result.append({
                'name': iface_name,
                'ip_address': status.ip_address,
                'status': status.status.value,
                'last_check': status.last_check,
                'latency_ms': status.latency_ms
            })
        return result
    
    def update_device_interfaces(self, device_id: str, interfaces: List[NetworkInterface]):
        with self._lock:
            if device_id in self.devices:
                self.devices[device_id].network_interfaces = interfaces
    
    def refresh_device_interfaces(self, device_id: str):
        with self._lock:
            if device_id in self.devices:
                available_ifaces = self._network_monitor.get_available_interfaces()
                self.devices[device_id].network_interfaces = available_ifaces


def create_device_manager() -> DeviceManager:
    return DeviceManager()