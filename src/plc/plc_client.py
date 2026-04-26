import snap7
from snap7.util import get_bool, get_int, get_dint, get_real, set_bool, set_int, set_dint, set_real
import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config.config import config

class PLCClient:
    def __init__(self):
        self.client = snap7.client.Client()
        self.connected = False
        self.connection_attempts = 0

    def connect(self):
        try:
            self.client.connect(config.PLC_HOST, config.PLC_RACK, config.PLC_SLOT)
            self.connected = True
            self.connection_attempts = 0
            print('PLC连接成功')
            return True
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
            data = self.client.db_read(db_number, start, size)
            return bytes(data)
        except Exception as e:
            print(f'读取DB失败: {e}')
            raise

    def read_m(self, start, size):
        if not self.connected:
            raise Exception('PLC未连接')

        try:
            data = self.client.mb_read(start, size)
            return bytes(data)
        except Exception as e:
            print(f'读取M区失败: {e}')
            raise

    def read_i(self, start, size):
        if not self.connected:
            raise Exception('PLC未连接')

        try:
            data = self.client.eb_read(start, size)
            return bytes(data)
        except Exception as e:
            print(f'读取输入失败: {e}')
            raise

    def read_q(self, start, size):
        if not self.connected:
            raise Exception('PLC未连接')

        try:
            data = self.client.ab_read(start, size)
            return bytes(data)
        except Exception as e:
            print(f'读取输出失败: {e}')
            raise

    def get_db_info(self, db_number):
        try:
            return self.client.get_db_info(db_number)
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
            self.client.db_write(db_number, start, data)
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
            self.client.db_write(db_number, start, data)
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
            self.client.db_write(db_number, start, data)
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
            self.client.db_write(db_number, start, data)
            return True
        except Exception as e:
            print(f'写入Real失败: {e}')
            return False