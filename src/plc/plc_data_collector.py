"""
PLC数据采集模块
根据GLABAL.db定义和PLCValues.xlsx变量表读取PLC数据
"""

import sys
import os
import struct
from typing import List, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.plc.plc_client import PLCClient
from src.analysis.plc_variable_loader import load_plc_tags

class PLCDataCollector:
    def __init__(self):
        self.plc = PLCClient()
        self.variable_loader = load_plc_tags()
        self.connected = False
        self._init_mappings()
        self._cache_m_variables()
        self._cache_i_variables()
        self._cache_q_variables()

    def _init_mappings(self):
        self.db1_mapping = {
            0: [(0, '保压选择'), (1, '双手合格'), (2, '电机启动主控'), (3, '滑块上限'), 
                (4, '关断上循环泵'), (5, '反行程检查'), (6, '允许下行'), (7, '回程停止位1')],
            1: [(0, '回程停止位2'), (1, '回程停止位3'), (2, '回程停止位4'), (3, '滑块快转慢位'),
                (4, '滑块下限位'), (5, '压制力达到'), (6, '主缸泄压到位'), (7, '滑块合模位')],
            2: [(0, '移动台机内落下到位指示'), (1, '移动台机内提升到位指示'),
                (2, '移动台移入到位指示'), (3, '下行主控'), (4, '滑块下行前条件检查'),
                (5, '保压'), (6, '泄压'), (7, '静止按钮')],
            3: [(0, '回程按钮'), (1, '滑块下行'), (2, '单次连续压制力到达'), (3, '回程主控'),
                (4, '锁紧松开驱动滑块回程'), (5, '滑块回程准备'), (6, '滑块回程'), (7, '润滑安全条件')],
            4: [(0, '开机润滑完成'), (1, '开机润滑'), (2, '润滑次数到'), (3, '润滑泵开始运行'),
                (4, '锁紧准备'), (5, '松开准备'), (6, '锁紧松开不在上极限时先驱'), (7, '左移动台故障')],
            5: [(0, '班产复位'), (1, '气阀手动顶出'), (2, '动态调压启用'), (3, '二次泄压启用'),
                (4, '锁紧到位'), (5, '松开到位'), (6, '压制力达到指示'), (7, '气阀手动退回')],
            6: [(0, '润滑上升沿'), (1, '电磁铁主控'), (2, '驱动器正常'), (3, '系统Error'),
                (4, '润滑强制开启'), (5, '上循环强制开启'), (6, '下循环强制开启'), (7, '弹出急停画面')],
            7: [(0, '关闭上油加热'), (1, '移动台夹紧力上限'), (2, '移动台夹紧力下限'), (3, '延时移出移动台'),
                (4, '延时移入移动台'), (5, '打开充液阀'), (6, '下模夹紧压力达到'), (7, '上模夹紧压力达到')],
            8: [(0, '合模位'), (1, '滑块慢下'), (2, '二次泄压位'), (3, '70%切泵'),
                (4, '80%切泵'), (5, '90%切泵'), (6, '90%关断泵口'), (7, '3Y1')],
            9: [(0, '3Y6.2开启'), (1, '动态切缸'), (2, '油阀手动顶出'), (3, '油阀手动退回'),
                (4, '启动电机过渡2M1'), (5, '启动电机过渡2M2'), (6, '启动电机过渡2M3'), (7, '启动电机过渡2M4')],
            10: [(0, '关断下循环泵'), (1, '安全爪主控'), (2, '安全爪打开到位'), (3, '安全爪回程'),
                (4, '安全爪关闭到位'), (5, '移动台合格'), (6, '启用主台'), (7, '启用副台')],
            11: [(0, '远程调压启用'), (1, '移动台提升到位指示'), (2, '移动台落下到位指示'),
                (3, '控制5Y1压力'), (4, '移动台夹紧压力上限'), (5, '移动台夹紧压力下限'),
                (6, '夹紧置位'), (7, '提升落下主控')],
            12: [(0, '移入移出主控'), (1, '左移入准备'), (2, '左移出准备'), (3, '右移入准备'),
                (4, '右移出准备'), (5, '左移出慢速'), (6, '左移入慢速'), (7, '右移出慢速')],
            13: [(0, '右移入慢速'), (1, '左台慢速'), (2, '右台慢速'), (3, '回程启动垫位'),
                (4, '垫顶出钮'), (5, '垫退回钮'), (6, '选择液压垫'), (7, '选择顶出器')],
            14: [(0, '左前双手合格'), (1, '左后双手合格'), (2, '右前双手合格'), (3, '右后双手合格'),
                (4, '急停合格'), (5, '安全栓退回到位'), (6, '安全栓移入到位'), (7, '一缸')],
            15: [(0, '两缸'), (1, '左前按钮站选择'), (2, '左后按钮站选择'), (3, '右前按钮站选择'),
                (4, '右后按钮站选择'), (5, '左台气阀测试顶出'), (6, '右台气阀测试顶出'), (7, '左台下模泄压')],
            16: [(0, '右台下模泄压'), (1, '左台下模夹紧力到达'), (2, '右台下模夹紧力到达'),
                (3, '左台下模夹紧'), (4, '右台下模夹紧'), (5, '使用夹板'), (6, '左模具有料'), (7, '左模具无料')],
            17: [(0, '右模具有料'), (1, '右模具无料'), (2, '左模具板料检测信号不合格'),
                (3, '右模具板料检测信号不合格'), (4, '左台车变频器复位'), (5, '右台车变频器复位'),
                (6, '左光栅复位'), (7, '右光栅复位')],
        }

        self.db1_int_vars = {
            32: ('压机模式', 'Int'), 36: ('润滑次数', 'DInt'), 40: ('润滑时间', 'DInt'),
            44: ('油超温温度', 'Real'), 48: ('油需冷却温度', 'Real'), 72: ('上油加热关闭温度', 'Real'),
            76: ('上油需加热温度', 'Real'),
        }

        self.db10_mapping = {
            0: ('2M1实时电机速度', 'Real'), 4: ('2M2实时电机速度', 'Real'), 8: ('2M3实时电机速度', 'Real'),
            12: ('2M4实时电机速度', 'Real'), 16: ('液压垫位移传感器', 'Real'), 20: ('压力传感器3S201', 'Real'),
            24: ('压力传感器3S202', 'Real'), 28: ('油温传感器', 'Real'), 32: ('压力传感器3S203', 'Real'),
            36: ('水温传感器', 'Real'), 40: ('流量传感器', 'Real'), 44: ('垫压力传感器4B201', 'Real'),
            48: ('垫压力传感器4B202', 'Real'), 52: ('移动台提升压力Mpa', 'Real'), 56: ('移动台压力传感器', 'Real'),
            60: ('4B201压力显示T', 'Real'), 64: ('4B202压力显示T', 'Real'), 68: ('滑块实际位移', 'Real'),
            72: ('滑块中间缸压力T', 'Real'), 76: ('滑块侧缸压力T', 'Real'), 80: ('滑块总压力T', 'Real'),
            84: ('滑块速度', 'Real'), 88: ('垫压力', 'Real'), 92: ('保压时间', 'Int'),
            96: ('左台变频器转速', 'Real'), 100: ('右台变频器转速', 'Real'), 104: ('顶出时间', 'Int'),
            108: ('3Y10压力反馈', 'Real'), 112: ('左气阀顶出时间', 'Int'), 114: ('右气阀顶出时间', 'Int'),
        }

    def _cache_m_variables(self):
        self.m_variables = []
        if self.variable_loader:
            for name, var in self.variable_loader.variables.items():
                addr = str(var.get('logical_address', ''))
                if addr.startswith('%M'):
                    parsed = self._parse_address(addr)
                    if parsed:
                        self.m_variables.append((name, parsed))

    def _cache_i_variables(self):
        self.i_variables = []
        if self.variable_loader:
            for name, var in self.variable_loader.variables.items():
                addr = str(var.get('logical_address', ''))
                if addr.startswith('%I'):
                    parsed = self._parse_address(addr)
                    if parsed:
                        self.i_variables.append((name, parsed))

    def _cache_q_variables(self):
        self.q_variables = []
        if self.variable_loader:
            for name, var in self.variable_loader.variables.items():
                addr = str(var.get('logical_address', ''))
                if addr.startswith('%Q'):
                    parsed = self._parse_address(addr)
                    if parsed:
                        self.q_variables.append((name, parsed))

    def connect(self):
        return self.plc.connect()

    def disconnect(self):
        self.plc.disconnect()

    def collect_all_data(self) -> List[Dict[str, Any]]:
        data = []
        data.extend(self._read_db1())
        data.extend(self._read_db10())
        data.extend(self._read_m_area())
        data.extend(self._read_i_area())
        data.extend(self._read_q_area())
        return data

    def _parse_address(self, addr):
        addr = addr.strip()
        if addr.startswith('%M'):
            return self._parse_area_addr(addr[2:], 'M')
        elif addr.startswith('%I'):
            return self._parse_area_addr(addr[2:], 'I')
        elif addr.startswith('%Q'):
            return self._parse_area_addr(addr[2:], 'Q')
        return None

    def _parse_area_addr(self, rest, area):
        if rest.startswith('D'):
            return (area, int(rest[1:]), 'DWord', 0)
        elif rest.startswith('W'):
            return (area, int(rest[1:]), 'Word', 0)
        elif rest.startswith('B'):
            return (area, int(rest[1:]), 'Byte', 0)
        elif '.' in rest:
            parts = rest.split('.')
            return (area, int(parts[0]), 'Bit', int(parts[1]))
        return (area, int(rest), 'Bit', 0)

    def _read_db1(self):
        data = []
        try:
            db_data = None
            for size in [100, 80, 60, 40, 20]:
                try:
                    db_data = self.plc.read_db(1, 0, size)
                    break
                except:
                    continue
            
            if not db_data:
                print('DB1读取失败')
                return data
            
            for byte_addr, bits in self.db1_mapping.items():
                if byte_addr < len(db_data):
                    byte_val = db_data[byte_addr]
                    for bit_offset, var_name in bits:
                        val = (byte_val >> bit_offset) & 0x01
                        data.append({
                            'db_number': 1, 'address': byte_addr * 8 + bit_offset,
                            'tag_name': var_name, 'value': val, 'quality': 1
                        })
            
            for addr, (var_name, var_type) in self.db1_int_vars.items():
                if addr + 4 <= len(db_data):
                    if var_type == 'Int':
                        val = int.from_bytes(db_data[addr:addr+2], 'little', signed=True)
                    elif var_type == 'DInt':
                        val = int.from_bytes(db_data[addr:addr+4], 'little', signed=True)
                    elif var_type == 'Real':
                        val = struct.unpack('<f', db_data[addr:addr+4])[0]
                    else:
                        continue
                    data.append({
                        'db_number': 1, 'address': addr, 'tag_name': var_name,
                        'value': val, 'quality': 1
                    })
        except Exception as e:
            print(f'读取DB1失败: {e}')
        return data

    def _read_db10(self):
        data = []
        try:
            db_data = None
            actual_size = 0
            for size in [120, 100, 80, 60, 40, 20]:
                try:
                    db_data = self.plc.read_db(10, 0, size)
                    actual_size = size
                    break
                except:
                    continue
            
            if not db_data:
                print('DB10读取失败')
                return data
            
            for addr, (var_name, var_type) in self.db10_mapping.items():
                if addr + 4 <= len(db_data):
                    if var_type == 'Real':
                        val = struct.unpack('>f', db_data[addr:addr+4])[0]
                    elif var_type == 'Int':
                        val = int.from_bytes(db_data[addr:addr+2], 'big', signed=True)
                    else:
                        continue
                    data.append({
                        'db_number': 10, 'address': addr, 'tag_name': var_name,
                        'value': val, 'quality': 1
                    })
        except Exception as e:
            print(f'读取DB10失败: {e}')
        return data

    def _read_m_area(self):
        data = []
        try:
            m_data = self.plc.read_m(0, 20)
            data.extend(self._process_area_vars(m_data, self.m_variables, 0))
        except Exception as e:
            print(f'读取M区失败: {e}')
        return data

    def _read_i_area(self):
        data = []
        try:
            i_data = self.plc.read_i(0, 50)
            data.extend(self._process_area_vars(i_data, self.i_variables, 0))
        except Exception as e:
            print(f'读取I区失败: {e}')
        return data

    def _read_q_area(self):
        data = []
        try:
            q_data = self.plc.read_q(0, 50)
            data.extend(self._process_area_vars(q_data, self.q_variables, 0))
        except Exception as e:
            print(f'读取Q区失败: {e}')
        return data

    def _process_area_vars(self, area_data, vars_cache, db_num):
        data = []
        for name, (area, offset, dtype, bit) in vars_cache:
            if dtype == 'Bit' and offset < len(area_data):
                val = (area_data[offset] >> bit) & 0x01
                data.append({
                    'db_number': db_num, 'address': offset * 8 + bit,
                    'tag_name': name, 'value': val, 'quality': 1
                })
            elif dtype == 'Byte' and offset < len(area_data):
                data.append({
                    'db_number': db_num, 'address': offset, 'tag_name': name,
                    'value': area_data[offset], 'quality': 1
                })
            elif dtype == 'Word' and offset + 2 <= len(area_data):
                val = int.from_bytes(area_data[offset:offset+2], 'little', signed=True)
                data.append({
                    'db_number': db_num, 'address': offset, 'tag_name': name,
                    'value': val, 'quality': 1
                })
            elif dtype == 'DWord' and offset + 4 <= len(area_data):
                val = int.from_bytes(area_data[offset:offset+4], 'little', signed=True)
                data.append({
                    'db_number': db_num, 'address': offset, 'tag_name': name,
                    'value': val, 'quality': 1
                })
        return data

def create_data_collector():
    return PLCDataCollector()
