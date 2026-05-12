
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.parsers.db_file_parser import DBFileParser
from typing import Dict, List, Any


def parse_single_db_file(file_path: str, db_num: int) -&gt; Dict:
    """解析单个DB文件，返回配置结构"""
    parser = DBFileParser()
    blocks = parser.parse_file(file_path)
    
    if db_num not in blocks:
        return {}
    
    db = blocks[db_num]
    
    config = {
        'db_number': db_num,
        'size': db.total_size,
        'bool_vars': {},
        'int_vars': {},
        'real_vars': {},
        'dint_vars': {}
    }
    
    # 按类型分组变量
    for var in db.variables:
        if var.data_type == 'BOOL':
            if var.byte_offset not in config['bool_vars']:
                config['bool_vars'][var.byte_offset] = []
            config['bool_vars'][var.byte_offset].append((var.bit_offset or 0, var.name))
        elif var.data_type == 'INT':
            config['int_vars'][var.byte_offset] = (var.name, 'Int')
        elif var.data_type == 'DINT':
            config['dint_vars'][var.byte_offset] = (var.name, 'DInt')
        elif var.data_type == 'REAL':
            config['real_vars'][var.byte_offset] = (var.name, 'Real')
    
    return config


def parse_complete_device(db_files: List[str], device_id: str, device_name: str, ip_address: str) -&gt; Dict:
    """解析完整设备配置"""
    db_definitions = []
    
    for file_path in db_files:
        filename = os.path.basename(file_path)
        
        # 判断DB编号
        db_num = 1  # 默认DB1（GLABAL）
        if '故障报警' in filename or 'Fault' in filename:
            db_num = 51
        elif '显示值' in filename or 'Display' in filename:
            db_num = 10
        elif 'GLABAL' in filename:
            db_num = 1
        
        db_config = parse_single_db_file(file_path, db_num)
        if db_config:
            db_definitions.append(db_config)
    
    return {
        'device_id': device_id,
        'device_name': device_name,
        'device_type': 'PLC_S7_1500',
        'ip_address': ip_address,
        'rack': 0,
        'slot': 1,
        'db_definitions': db_definitions
    }


def print_device_config(device_config: Dict):
    """打印设备配置"""
    print(f"{{")
    print(f"    'device_id': '{device_config['device_id']}',")
    print(f"    'device_name': '{device_config['device_name']}',")
    print(f"    'device_type': DeviceType.PLC_S7_1500,")
    print(f"    'ip_address': '{device_config['ip_address']}',")
    print(f"    'rack': 0,")
    print(f"    'slot': 1,")
    print(f"    'db_definitions': [")
    
    for db_def in device_config['db_definitions']:
        print(f"        {{")
        print(f"            'db_number': {db_def['db_number']},")
        
        if db_def.get('bool_vars'):
            print(f"            'bool_vars': {{")
            for byte_addr, bits in sorted(db_def['bool_vars'].items()):
                print(f"                {byte_addr}: {bits},")
            print(f"            }},")
        
        if db_def.get('int_vars'):
            print(f"            'int_vars': {{")
            for addr, (name, type_) in sorted(db_def['int_vars'].items()):
                print(f"                {addr}: ('{name}', '{type_}'),")
            print(f"            }},")
        
        if db_def.get('dint_vars'):
            print(f"            'dint_vars': {{")
            for addr, (name, type_) in sorted(db_def['dint_vars'].items()):
                print(f"                {addr}: ('{name}', '{type_}'),")
            print(f"            }},")
        
        if db_def.get('real_vars'):
            print(f"            'real_vars': {{")
            for addr, (name, type_) in sorted(db_def['real_vars'].items()):
                print(f"                {addr}: ('{name}', '{type_}'),")
            print(f"            }},")
        
        print(f"        }},")
    
    print(f"    ]")
    print(f"}},")


def main():
    plc_def_dir = os.path.join(os.path.dirname(__file__), '..', 'plc_definitions')
    
    # 设备映射
    devices = {
        'rxa800': {
            'id': 'plc_rxa800',
            'name': 'RXA800压机PLC',
            'ip': '172.15.14.141',
            'files': ['GLABAL（柔性A800）.db', '显示值.db', '故障报警.db']
        },
        'rxa1300': {
            'id': 'plc_001',
            'name': 'RXA1300压机PLC',
            'ip': '172.15.14.150',
            'files': ['GLABAL（柔性A1300）.db', '显示值.db', '故障报警.db']
        },
        'rxa630_1': {
            'id': 'plc_rxa630_1',
            'name': 'RXA630-1压机PLC',
            'ip': '172.15.14.176',
            'files': ['GLABAL（柔性A3630-1）.db', '显示值.db', '故障报警.db']
        },
        'rxa630_2': {
            'id': 'plc_rxa630_2',
            'name': 'RXA630-2压机PLC',
            'ip': '172.15.14.191',
            'files': ['GLABAL（柔性A3630-2）.db', '显示值.db', '故障报警.db']
        },
        'rxa630_3': {
            'id': 'plc_rxa630_3',
            'name': 'RXA630-3压机PLC',
            'ip': '172.15.14.206',
            'files': ['GLABAL（柔性A3630-3）.db', '显示值.db', '故障报警.db']
        },
        'rxa630_4': {
            'id': 'plc_rxa630_4',
            'name': 'RXA630-4压机PLC',
            'ip': '172.15.14.221',
            'files': ['GLABAL（柔性A3630-4）.db', '显示值.db', '故障报警.db']
        }
    }
    
    print("解析设备配置...\n")
    print("DEFAULT_DEVICES = [")
    
    for device_key, device_info in devices.items():
        db_files = []
        for file_name in device_info['files']:
            file_path = os.path.join(plc_def_dir, file_name)
            if os.path.exists(file_path):
                db_files.append(file_path)
        
        device_config = parse_complete_device(
            db_files,
            device_info['id'],
            device_info['name'],
            device_info['ip']
        )
        print_device_config(device_config)
        print()
    
    print("]")


if __name__ == '__main__':
    main()

