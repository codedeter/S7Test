import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class DeviceType(Enum):
    PLC_S7_1200 = "s7_1200"
    PLC_S7_1500 = "s7_1500"
    PLC_S7_300 = "s7_300"
    PLC_S7_400 = "s7_400"
    PLC_S7_200 = "s7_200"


class ConnectionStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class DBVariable:
    name: str
    address: int
    data_type: str
    bit_offset: Optional[int] = None
    struct_name: Optional[str] = None
    description: str = ""


@dataclass
class DataBlock:
    number: int
    name: str
    variables: List[DBVariable] = field(default_factory=list)
    size: int = 0
    byte_order: str = "little"


@dataclass
class AreaVariable:
    name: str
    area: str
    offset: int
    data_type: str
    bit_offset: int = 0


@dataclass
class NetworkInterface:
    name: str
    ip_address: str
    subnet_mask: str = ""
    gateway: str = ""
    priority: int = 10
    enabled: bool = True

    def __repr__(self) -> str:
        return f"NetworkInterface(name={self.name}, ip={self.ip_address}, priority={self.priority})"


@dataclass
class DeviceConfig:
    device_id: str
    device_name: str
    device_type: DeviceType
    ip_address: str
    rack: int = 0
    slot: int = 1
    connection_timeout: int = 10000
    retry_interval: int = 5000
    max_retry_attempts: int = 0
    reconnect_backoff_enabled: bool = True
    data_blocks: List[DataBlock] = field(default_factory=list)
    m_variables: List[AreaVariable] = field(default_factory=list)
    i_variables: List[AreaVariable] = field(default_factory=list)
    q_variables: List[AreaVariable] = field(default_factory=list)
    enabled: bool = True
    description: str = ""
    
    ip_addresses: List[str] = field(default_factory=list)
    network_interfaces: List[NetworkInterface] = field(default_factory=list)
    auto_detect_interfaces: bool = False
    network_switch_timeout: int = 5000
    preferred_interface: Optional[str] = None

    @property
    def connection_string(self) -> str:
        return f"{self.ip_address}:{self.rack}/{self.slot}"
    
    @property
    def all_ip_addresses(self) -> List[str]:
        ips = [self.ip_address] if self.ip_address else []
        ips.extend(self.ip_addresses)
        for iface in self.network_interfaces:
            if iface.enabled and iface.ip_address not in ips:
                ips.append(iface.ip_address)
        return ips
    
    def get_preferred_ips(self) -> List[str]:
        if self.preferred_interface:
            for iface in self.network_interfaces:
                if iface.name == self.preferred_interface and iface.enabled:
                    return [iface.ip_address] + [ip for ip in self.all_ip_addresses if ip != iface.ip_address]
        sorted_interfaces = sorted(self.network_interfaces, key=lambda x: x.priority)
        ips = [iface.ip_address for iface in sorted_interfaces if iface.enabled]
        if self.ip_address and self.ip_address not in ips:
            ips.insert(0, self.ip_address)
        ips.extend([ip for ip in self.ip_addresses if ip not in ips])
        return ips


@dataclass
class DeviceStatus:
    device_id: str
    status: ConnectionStatus
    connected: bool = False
    last_error: Optional[str] = None
    last_update: Optional[float] = None
    data_count: int = 0
    
    disconnection_start_time: Optional[float] = None
    total_disconnection_duration: float = 0
    consecutive_failure_count: int = 0
    last_reconnection_time: Optional[float] = None
    last_disconnection_duration: float = 0
    reconnection_count: int = 0
    
    def start_disconnection(self):
        if not self.disconnection_start_time:
            self.disconnection_start_time = time.time()
            self.status = ConnectionStatus.DISCONNECTED
            self.connected = False
    
    def end_disconnection(self):
        if self.disconnection_start_time:
            duration = time.time() - self.disconnection_start_time
            self.last_disconnection_duration = duration
            self.total_disconnection_duration += duration
            self.disconnection_start_time = None
            self.consecutive_failure_count = 0
            self.last_reconnection_time = time.time()
            self.reconnection_count += 1
            self.status = ConnectionStatus.CONNECTED
            self.connected = True
    
    def get_current_disconnection_duration(self) -> float:
        if self.disconnection_start_time:
            return time.time() - self.disconnection_start_time
        return 0


@dataclass
class DisconnectionRecord:
    device_id: str
    start_time: float
    end_time: Optional[float] = None
    duration: float = 0
    reason: str = ""
    reconnected: bool = False


def create_device_config(
    device_id: str,
    device_name: str,
    ip_address: str,
    device_type: DeviceType = DeviceType.PLC_S7_1200,
    rack: int = 0,
    slot: int = 1,
    db_numbers: List[int] = None,
    m_range: tuple = None,
    i_range: tuple = None,
    q_range: tuple = None
) -> DeviceConfig:
    config = DeviceConfig(
        device_id=device_id,
        device_name=device_name,
        device_type=device_type,
        ip_address=ip_address,
        rack=rack,
        slot=slot
    )
    return config
