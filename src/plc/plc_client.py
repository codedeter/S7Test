"""
PLC客户端 - 保持向后兼容性
适配旧API，内部使用device_manager中的PLCClient实现
"""
import snap7
from snap7.util import get_bool, get_int, get_dint, get_real, set_bool, set_int, set_dint, set_real
import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from config.config import config
from src.devices.device_config import DeviceConfig, DeviceType
from src.devices.device_manager import PLCClient as NewPLCClient


class LegacyPLCClient:
    """
    向后兼容的PLC客户端类
    为保持旧API兼容性而存在，内部使用新的PLCClient实现
    """
    def __init__(self):
        device_config = DeviceConfig(
            device_id='legacy_plc',
            device_name='Legacy PLC',
            device_type=DeviceType.PLC_S7_1200,
            ip_address=config.PLC_HOST,
            rack=config.PLC_RACK,
            slot=config.PLC_SLOT,
            retry_interval=config.PLC_RETRY_INTERVAL,
            enabled=True
        )
        self.client = NewPLCClient(device_config)
        self.connected = False
        self.connection_attempts = 0

    def connect(self):
        try:
            result = self.client.connect()
            self.connected = result
            self.connection_attempts = 0
            if result:
                print('PLC连接成功')
            return result
        except Exception as e:
            print(f'PLC连接失败: {e}')
            self.connected = False
            return False

    def reconnect(self):
        try:
            self.disconnect()
            time.sleep(config.PLC_RETRY_INTERVAL / 1000)
            return self.connect()
        except Exception as e:
            print(f'重连失败: {e}')
            return False

    def disconnect(self):
        try:
            self.client.disconnect()
            self.connected = False
        except:
            pass

    def read_db(self, db_number, start, size):
        if not self.connected:
            raise Exception('PLC未连接')
        try:
            data = self.client.read_db(db_number, start, size)
            if data is None:
                raise Exception('读取数据为空')
            return bytes(data)
        except Exception as e:
            print(f'读取DB失败: {e}')
            raise

    def read_m(self, start, size):
        if not self.connected:
            raise Exception('PLC未连接')
        try:
            data = self.client.read_m(start, size)
            if data is None:
                raise Exception('读取数据为空')
            return bytes(data)
        except Exception as e:
            print(f'读取M区失败: {e}')
            raise

    def read_i(self, start, size):
        if not self.connected:
            raise Exception('PLC未连接')
        try:
            data = self.client.read_i(start, size)
            if data is None:
                raise Exception('读取数据为空')
            return bytes(data)
        except Exception as e:
            print(f'读取输入失败: {e}')
            raise

    def read_q(self, start, size):
        if not self.connected:
            raise Exception('PLC未连接')
        try:
            data = self.client.read_q(start, size)
            if data is None:
                raise Exception('读取数据为空')
            return bytes(data)
        except Exception as e:
            print(f'读取输出失败: {e}')
            raise

    def get_db_info(self, db_number):
        try:
            return self.client.client.get_db_info(db_number)
        except Exception as e:
            print(f'获取DB信息失败: {e}')
            return None

    def read_bool(self, db_number, start, bit_offset):
        try:
            data = self.read_db(db_number, start, 1)
            return get_bool(data, start, bit_offset)
        except Exception as e:
            print(f'读取Bool失败: {e}')
            return None

    def write_bool(self, db_number, start, bit_offset, value):
        try:
            data = self.read_db(db_number, start, 1)
            set_bool(data, start, bit_offset, value)
            self.client.client.db_write(db_number, start, data)
            return True
        except Exception as e:
            print(f'写入Bool失败: {e}')
            return False

    def read_int(self, db_number, start):
        try:
            data = self.read_db(db_number, start, 2)
            return get_int(data, start)
        except Exception as e:
            print(f'读取Int失败: {e}')
            return None

    def write_int(self, db_number, start, value):
        try:
            data = bytearray(2)
            set_int(data, 0, value)
            self.client.client.db_write(db_number, start, data)
            return True
        except Exception as e:
            print(f'写入Int失败: {e}')
            return False

    def read_dint(self, db_number, start):
        try:
            data = self.read_db(db_number, start, 4)
            return get_dint(data, start)
        except Exception as e:
            print(f'读取DInt失败: {e}')
            return None

    def write_dint(self, db_number, start, value):
        try:
            data = bytearray(4)
            set_dint(data, 0, value)
            self.client.client.db_write(db_number, start, data)
            return True
        except Exception as e:
            print(f'写入DInt失败: {e}')
            return False

    def read_real(self, db_number, start):
        try:
            data = self.read_db(db_number, start, 4)
            return get_real(data, start)
        except Exception as e:
            print(f'读取Real失败: {e}')
            return None

    def write_real(self, db_number, start, value):
        try:
            data = bytearray(4)
            set_real(data, 0, value)
            self.client.client.db_write(db_number, start, data)
            return True
        except Exception as e:
            print(f'写入Real失败: {e}')
            return False


PLCClient = LegacyPLCClient
"""
保持向后兼容性的别名
旧代码中使用 PLCClient 类名的地方仍然可以正常工作
"""