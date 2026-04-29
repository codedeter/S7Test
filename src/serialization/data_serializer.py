import json
import zlib
import msgpack
from typing import Any, Dict, List, Optional
from datetime import datetime


class DataSerializer:
    @staticmethod
    def json_serialize(data: Any, indent: int = None) -> bytes:
        return json.dumps(data, indent=indent, ensure_ascii=False).encode('utf-8')
    
    @staticmethod
    def json_deserialize(data: bytes) -> Any:
        return json.loads(data.decode('utf-8'))
    
    @staticmethod
    def msgpack_serialize(data: Any) -> bytes:
        return msgpack.packb(data, use_bin_type=True)
    
    @staticmethod
    def msgpack_deserialize(data: bytes) -> Any:
        return msgpack.unpackb(data, raw=False)
    
    @staticmethod
    def compress(data: bytes) -> bytes:
        return zlib.compress(data, level=zlib.Z_BEST_COMPRESSION)
    
    @staticmethod
    def decompress(data: bytes) -> bytes:
        return zlib.decompress(data)


class DataDelta:
    def __init__(self):
        self.last_values: Dict[str, Any] = {}
        self.last_send_time: Dict[str, float] = {}
    
    def compute_delta(self, device_id: str, current_values: Dict[str, Any]) -> Dict[str, Any]:
        delta = {}
        device_key = f"device:{device_id}"
        
        for key, value in current_values.items():
            full_key = f"{device_key}:{key}" if not key.startswith(device_id) else key
            
            if full_key not in self.last_values or self.last_values[full_key] != value:
                delta[key] = value
                self.last_values[full_key] = value
        
        self.last_send_time[device_id] = datetime.now().timestamp()
        return delta
    
    def get_full_snapshot(self, device_id: str, current_values: Dict[str, Any]) -> Dict[str, Any]:
        device_key = f"device:{device_id}"
        
        for key, value in current_values.items():
            full_key = f"{device_key}:{key}" if not key.startswith(device_id) else key
            self.last_values[full_key] = value
        
        self.last_send_time[device_id] = datetime.now().timestamp()
        return current_values
    
    def clear_device_state(self, device_id: str):
        device_key = f"device:{device_id}"
        keys_to_remove = [k for k in self.last_values.keys() if k.startswith(device_key)]
        for k in keys_to_remove:
            del self.last_values[k]
        
        if device_id in self.last_send_time:
            del self.last_send_time[device_id]


class DataPacker:
    @staticmethod
    def pack_data(data: Dict[str, Any], use_compression: bool = True, use_msgpack: bool = True) -> bytes:
        if use_msgpack:
            serialized = DataSerializer.msgpack_serialize(data)
        else:
            serialized = DataSerializer.json_serialize(data)
        
        if use_compression:
            return DataSerializer.compress(serialized)
        
        return serialized
    
    @staticmethod
    def unpack_data(packed_data: bytes, use_compression: bool = True, use_msgpack: bool = True) -> Dict[str, Any]:
        if use_compression:
            data = DataSerializer.decompress(packed_data)
        else:
            data = packed_data
        
        if use_msgpack:
            return DataSerializer.msgpack_deserialize(data)
        else:
            return DataSerializer.json_deserialize(data)
    
    @staticmethod
    def create_packet(
        packet_type: str,
        device_id: str,
        payload: Dict[str, Any],
        sequence: int = 0,
        timestamp: Optional[float] = None
    ) -> Dict[str, Any]:
        return {
            'type': packet_type,
            'device_id': device_id,
            'sequence': sequence,
            'timestamp': timestamp or datetime.now().timestamp(),
            'payload': payload
        }


def get_serializer() -> DataSerializer:
    return DataSerializer()


def get_data_delta() -> DataDelta:
    return DataDelta()


def get_data_packer() -> DataPacker:
    return DataPacker()