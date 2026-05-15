"""
设备配置加载器 - 支持从配置文件加载PLC设备配置
"""
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from src.devices.device_config import (
    DeviceConfig, DeviceType, DataBlock, DBVariable, AreaVariable
)


class DeviceConfigLoader:
    """设备配置加载器"""
    
    def __init__(self, config_dir: str = "./config/devices"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def load_all(self) -> List[DeviceConfig]:
        """
        加载所有设备配置
        
        Returns:
            List[DeviceConfig]: 设备配置列表
        """
        configs = []
        
        # 支持 YAML 和 JSON
        for ext in ['*.yml', '*.yaml', '*.json']:
            for file in self.config_dir.glob(ext):
                try:
                    cfg = self._load_single(file)
                    configs.append(cfg)
                    print(f"[DeviceConfigLoader] Loaded device: {cfg.device_id} from {file.name}")
                except Exception as e:
                    print(f"[DeviceConfigLoader] Error loading {file}: {e}")
        
        return configs
    
    def _load_single(self, file: Path) -> DeviceConfig:
        """
        加载单个配置文件
        
        Args:
            file: 配置文件路径
            
        Returns:
            DeviceConfig: 设备配置对象
        """
        if file.suffix in ('.yml', '.yaml'):
            with open(file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        else:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        return self._dict_to_config(data)
    
    def _dict_to_config(self, data: Dict) -> DeviceConfig:
        """
        将字典转换为 DeviceConfig 对象
        
        Args:
            data: 配置字典
            
        Returns:
            DeviceConfig: 设备配置对象
        """
        # 设备基础信息
        device_type = DeviceType(data.get('device_type', 's7_1500'))
        
        # 解析数据块定义
        data_blocks = []
        for db_data in data.get('db_definitions', []):
            db = self._parse_data_block(db_data)
            data_blocks.append(db)
        
        # 解析 M/I/Q 区域变量
        m_vars = self._parse_area_variables(data.get('m_variables', []), 'M')
        i_vars = self._parse_area_variables(data.get('i_variables', []), 'I')
        q_vars = self._parse_area_variables(data.get('q_variables', []), 'Q')
        
        # 创建配置对象
        return DeviceConfig(
            device_id=data['device_id'],
            device_name=data['device_name'],
            device_type=device_type,
            ip_address=data['ip_address'],
            rack=data.get('rack', 0),
            slot=data.get('slot', 1),
            connection_timeout=data.get('connection_timeout', 10000),
            retry_interval=data.get('retry_interval', 5000),
            max_retry_attempts=data.get('max_retry_attempts', 0),
            reconnect_backoff_enabled=data.get('reconnect_backoff_enabled', True),
            data_blocks=data_blocks,
            m_variables=m_vars,
            i_variables=i_vars,
            q_variables=q_vars,
            enabled=data.get('enabled', True),
            description=data.get('description', '')
        )
    
    def _parse_data_block(self, db_data: Dict) -> DataBlock:
        """解析数据块定义"""
        db_number = db_data.get('db_number', 1)
        db_size = db_data.get('size', 0)
        
        variables = []
        
        # 解析 Bool 变量
        for addr, bit_vars in db_data.get('bool_vars', {}).items():
            addr_int = int(addr)
            for (bit_offset, var_name) in bit_vars:
                variables.append(DBVariable(
                    name=var_name,
                    address=addr_int,
                    data_type='BOOL',
                    bit_offset=bit_offset
                ))
        
        # 解析 Int 变量
        for addr, (var_name, dtype) in db_data.get('int_vars', {}).items():
            addr_int = int(addr)
            variables.append(DBVariable(
                name=var_name,
                address=addr_int,
                data_type=dtype
            ))
        
        # 解析 DInt 变量
        for addr, (var_name, dtype) in db_data.get('dint_vars', {}).items():
            addr_int = int(addr)
            variables.append(DBVariable(
                name=var_name,
                address=addr_int,
                data_type=dtype
            ))
        
        # 解析 Real 变量
        for addr, (var_name, dtype) in db_data.get('real_vars', {}).items():
            addr_int = int(addr)
            variables.append(DBVariable(
                name=var_name,
                address=addr_int,
                data_type=dtype
            ))
        
        return DataBlock(
            number=db_number,
            name=f"DB{db_number}",
            variables=variables,
            size=db_size
        )
    
    def _parse_area_variables(self, vars_data: List, area: str) -> List[AreaVariable]:
        """解析区域变量 (M/I/Q)"""
        variables = []
        for var_data in vars_data:
            variables.append(AreaVariable(
                name=var_data.get('name', ''),
                area=area,
                offset=var_data.get('offset', 0),
                data_type=var_data.get('data_type', 'BOOL'),
                bit_offset=var_data.get('bit_offset', 0)
            ))
        return variables
    
    def save_config(self, config: DeviceConfig, filename: Optional[str] = None) -> Path:
        """
        保存配置到文件
        
        Args:
            config: 设备配置
            filename: 文件名（不含扩展名），默认使用 device_id
            
        Returns:
            Path: 保存的文件路径
        """
        if not filename:
            filename = config.device_id
        
        file_path = self.config_dir / f"{filename}.yml"
        
        data = self._config_to_dict(config)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        
        print(f"[DeviceConfigLoader] Saved config to {file_path}")
        return file_path
    
    def _config_to_dict(self, config: DeviceConfig) -> Dict:
        """将配置对象转换为字典"""
        data = {
            'device_id': config.device_id,
            'device_name': config.device_name,
            'device_type': config.device_type.value,
            'ip_address': config.ip_address,
            'rack': config.rack,
            'slot': config.slot,
            'connection_timeout': config.connection_timeout,
            'retry_interval': config.retry_interval,
            'max_retry_attempts': config.max_retry_attempts,
            'reconnect_backoff_enabled': config.reconnect_backoff_enabled,
            'enabled': config.enabled,
            'description': config.description,
            'db_definitions': []
        }
        
        # 转换数据块定义
        for db in config.data_blocks:
            db_dict = {
                'db_number': db.number,
                'size': db.size,
                'bool_vars': {},
                'int_vars': {},
                'dint_vars': {},
                'real_vars': {}
            }
            
            for var in db.variables:
                dtype = var.data_type.upper()
                if dtype == 'BOOL':
                    addr = var.address
                    if addr not in db_dict['bool_vars']:
                        db_dict['bool_vars'][addr] = []
                    db_dict['bool_vars'][addr].append((var.bit_offset, var.name))
                elif dtype == 'INT':
                    db_dict['int_vars'][var.address] = (var.name, 'INT')
                elif dtype == 'DINT':
                    db_dict['dint_vars'][var.address] = (var.name, 'DINT')
                elif dtype == 'REAL':
                    db_dict['real_vars'][var.address] = (var.name, 'REAL')
            
            data['db_definitions'].append(db_dict)
        
        return data


def create_device_loader(config_dir: str = "./config/devices") -> DeviceConfigLoader:
    """创建设备配置加载器"""
    return DeviceConfigLoader(config_dir)
