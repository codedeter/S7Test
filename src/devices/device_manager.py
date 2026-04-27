import time
import threading
import struct
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

import snap7
from snap7.util import get_bool, get_int, get_dint, get_real, set_bool, set_int, set_dint, set_real

from .device_config import (
    DeviceConfig, DeviceStatus, DeviceType,
    ConnectionStatus, DataBlock, AreaVariable
)


@dataclass
class CollectedData:
    device_id: str
    device_name: str
    timestamp: float
    data: List[Dict[str, Any]]
    connected: bool


class PLCClient:
    def __init__(self, config: DeviceConfig):
        self.config = config
        self.client = snap7.client.Client()
        self.connected = False
        self.connection_attempts = 0

    def connect(self) -> bool:
        try:
            self.client.connect(
                self.config.ip_address,
                self.config.rack,
                self.config.slot
            )
            self.connected = True
            self.connection_attempts = 0
            return True
        except Exception as e:
            print(f"[{self.config.device_id}] Connection failed: {e}")
            self.connected = False
            return False

    def disconnect(self):
        try:
            self.client.disconnect()
        except:
            pass
        finally:
            self.connected = False

    def reconnect(self) -> bool:
        self.disconnect()
        time.sleep(self.config.retry_interval / 1000)
        return self.connect()

    def read_db(self, db_number: int, start: int, size: int) -> Optional[bytes]:
        if not self.connected:
            try:
                self.connected = self.client.get_connected()
            except:
                self.connected = False
            if not self.connected:
                return None
        try:
            data = self.client.db_read(db_number, start, size)
            return bytes(data)
        except Exception as e:
            error_str = str(e)
            if "Address" in error_str or "range" in error_str or "CPU" in error_str:
                return None
            self.connected = False
            return None

    def read_m(self, start: int, size: int) -> Optional[bytes]:
        if not self.connected:
            return None
        try:
            data = self.client.mb_read(start, size)
            return bytes(data)
        except Exception as e:
            print(f"[{self.config.device_id}] Read M area failed: {e}")
            return None

    def read_i(self, start: int, size: int) -> Optional[bytes]:
        if not self.connected:
            return None
        try:
            data = self.client.eb_read(start, size)
            return bytes(data)
        except Exception as e:
            print(f"[{self.config.device_id}] Read I area failed: {e}")
            return None

    def read_q(self, start: int, size: int) -> Optional[bytes]:
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


class DeviceCollector:
    def __init__(self, config: DeviceConfig, client: PLCClient):
        self.config = config
        self.client = client
        self._init_data_mappings()

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

        return data

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
        self._running = False
        self._collection_thread: Optional[threading.Thread] = None

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

            print(f"Device {config.device_id} ({config.device_name}) added")
            return True

    def remove_device(self, device_id: str) -> bool:
        with self._lock:
            if device_id not in self.devices:
                return False

            if device_id in self.clients:
                self.clients[device_id].disconnect()

            del self.devices[device_id]
            del self.clients[device_id]
            del self.collectors[device_id]
            del self.statuses[device_id]

            return True

    def connect_device(self, device_id: str) -> bool:
        with self._lock:
            if device_id not in self.clients:
                return False

            client = self.clients[device_id]
            self.statuses[device_id].status = ConnectionStatus.CONNECTING

            if client.connect():
                self.statuses[device_id].status = ConnectionStatus.CONNECTED
                self.statuses[device_id].connected = True
                print(f"Device {device_id} connected")
                return True
            else:
                self.statuses[device_id].status = ConnectionStatus.ERROR
                self.statuses[device_id].connected = False
                return False

    def connect_all(self) -> Dict[str, bool]:
        results = {}
        for device_id in self.devices:
            results[device_id] = self.connect_device(device_id)
        return results

    def disconnect_device(self, device_id: str):
        with self._lock:
            if device_id in self.clients:
                self.clients[device_id].disconnect()
                self.statuses[device_id].status = ConnectionStatus.DISCONNECTED
                self.statuses[device_id].connected = False

    def disconnect_all(self):
        for device_id in self.devices:
            self.disconnect_device(device_id)

    def collect_data(self, device_id: str) -> Optional[CollectedData]:
        with self._lock:
            if device_id not in self.devices:
                print(f"[{device_id}] Device not found in manager")
                return None

            config = self.devices[device_id]
            collector = self.collectors.get(device_id)
            client = self.clients.get(device_id)

            if not collector or not client:
                print(f"[{device_id}] No collector or client")
                return None

        if not client.connected:
            print(f"[{device_id}] Client not connected, skipping...")
            return None

        print(f"[{device_id}] Collecting data... (connected={client.connected})")
        data = collector.collect_all_data()
        print(f"[{device_id}] Collected {len(data)} data points")

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

    def collect_all_data(self) -> List[CollectedData]:
        results = []
        device_ids = list(self.devices.keys())
        print(f"[DeviceManager] Starting collection for {len(device_ids)} devices: {device_ids}")
        for device_id in device_ids:
            try:
                collected = self.collect_data(device_id)
                if collected:
                    results.append(collected)
                    print(f"[DeviceManager] Device {device_id} collected {len(collected.data)} points")
                else:
                    print(f"[DeviceManager] Device {device_id} returned no data")
            except Exception as e:
                print(f"[DeviceManager] Error collecting from {device_id}: {e}")
        print(f"[DeviceManager] Collection complete: {len(results)} devices with data")
        return results

    def set_data_callback(self, callback: Callable[[List[CollectedData]], None]):
        self._data_callback = callback

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

    def get_device_status(self, device_id: str) -> Optional[DeviceStatus]:
        return self.statuses.get(device_id)

    def get_all_statuses(self) -> Dict[str, DeviceStatus]:
        return self.statuses.copy()

    def get_device_config(self, device_id: str) -> Optional[DeviceConfig]:
        return self.devices.get(device_id)

    def list_devices(self) -> List[Dict[str, Any]]:
        return [
            {
                'device_id': d.device_id,
                'device_name': d.device_name,
                'device_type': d.device_type.value,
                'ip_address': d.ip_address,
                'connection_string': d.connection_string,
                'enabled': d.enabled,
                'status': self.statuses[d.device_id].status.value if d.device_id in self.statuses else 'unknown'
            }
            for d in self.devices.values()
        ]


def create_device_manager() -> DeviceManager:
    return DeviceManager()
