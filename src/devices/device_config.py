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
class DeviceConfig:
    device_id: str
    device_name: str
    device_type: DeviceType
    ip_address: str
    rack: int = 0
    slot: int = 1
    connection_timeout: int = 5000
    retry_interval: int = 3000
    data_blocks: List[DataBlock] = field(default_factory=list)
    m_variables: List[AreaVariable] = field(default_factory=list)
    i_variables: List[AreaVariable] = field(default_factory=list)
    q_variables: List[AreaVariable] = field(default_factory=list)
    enabled: bool = True
    description: str = ""

    @property
    def connection_string(self) -> str:
        return f"{self.ip_address}:{self.rack}/{self.slot}"


@dataclass
class DeviceStatus:
    device_id: str
    status: ConnectionStatus
    connected: bool = False
    last_error: Optional[str] = None
    last_update: Optional[float] = None
    data_count: int = 0


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
