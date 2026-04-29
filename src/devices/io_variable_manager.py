import os
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from src.parsers.xlsx_variable_parser import (
    XLSXVariableParser,
    PLCVariable,
    parse_xlsx_variable_file
)


class IOArea(Enum):
    INPUT = "I"
    OUTPUT = "Q"
    MEMORY = "M"
    DB = "DB"


@dataclass
class DeviceIOConfig:
    device_id: str
    input_vars: Dict[str, PLCVariable] = field(default_factory=dict)
    output_vars: Dict[str, PLCVariable] = field(default_factory=dict)
    memory_vars: Dict[str, PLCVariable] = field(default_factory=dict)
    db_vars: Dict[int, Dict[str, PLCVariable]] = field(default_factory=dict)
    source_file: Optional[str] = None
    loaded_at: Optional[float] = None
    
    def get_summary(self) -> Dict[str, Any]:
        db_count = sum(len(vars) for vars in self.db_vars.values())
        return {
            'device_id': self.device_id,
            'input_count': len(self.input_vars),
            'output_count': len(self.output_vars),
            'memory_count': len(self.memory_vars),
            'db_count': db_count,
            'db_blocks': list(self.db_vars.keys()),
            'total': len(self.input_vars) + len(self.output_vars) + len(self.memory_vars) + db_count
        }


class IOVariableManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._device_io_configs: Dict[str, DeviceIOConfig] = {}
        self._io_to_fault_mapping: Dict[str, List[str]] = {}
        self._fault_to_io_mapping: Dict[str, List[str]] = {}
        self._lock = threading.Lock()
        self._initialized = True
    
    def load_io_variables(self, device_id: str, file_path: str, sheet_name: str = None) -> bool:
        """从XLSX文件加载设备的IO变量"""
        if not os.path.exists(file_path):
            print(f"IO variables file not found: {file_path}")
            return False
        
        try:
            variables = parse_xlsx_variable_file(file_path, sheet_name)
            print(f"Loaded {len(variables)} variables from {file_path}")
        except Exception as e:
            print(f"Error loading IO variables: {e}")
            return False
        
        io_config = DeviceIOConfig(
            device_id=device_id,
            source_file=file_path,
            loaded_at=os.path.getmtime(file_path)
        )
        
        for name, var in variables.items():
            if var.area == 'I':
                io_config.input_vars[name] = var
            elif var.area == 'Q':
                io_config.output_vars[name] = var
            elif var.area == 'M':
                io_config.memory_vars[name] = var
            elif var.db_number is not None:
                if var.db_number not in io_config.db_vars:
                    io_config.db_vars[var.db_number] = {}
                io_config.db_vars[var.db_number][name] = var
        
        with self._lock:
            self._device_io_configs[device_id] = io_config
        
        print(f"IO variables loaded for device {device_id}:")
        summary = io_config.get_summary()
        print(f"  Inputs: {summary['input_count']}")
        print(f"  Outputs: {summary['output_count']}")
        print(f"  Memory: {summary['memory_count']}")
        print(f"  DB Blocks: {len(summary['db_blocks'])}")
        
        return True
    
    def load_io_variables_from_dict(self, device_id: str, io_data: Dict[str, Any]) -> bool:
        """从字典加载设备的IO变量"""
        io_config = DeviceIOConfig(device_id=device_id)
        
        for var_data in io_data.get('input_vars', []):
            var = PLCVariable(
                name=var_data['name'],
                logical_address=var_data.get('logical_address', ''),
                data_type=var_data.get('data_type', 'BOOL'),
                byte_offset=var_data.get('byte_offset'),
                bit_offset=var_data.get('bit_offset'),
                area='I',
                description=var_data.get('description', '')
            )
            io_config.input_vars[var.name] = var
        
        for var_data in io_data.get('output_vars', []):
            var = PLCVariable(
                name=var_data['name'],
                logical_address=var_data.get('logical_address', ''),
                data_type=var_data.get('data_type', 'BOOL'),
                byte_offset=var_data.get('byte_offset'),
                bit_offset=var_data.get('bit_offset'),
                area='Q',
                description=var_data.get('description', '')
            )
            io_config.output_vars[var.name] = var
        
        for var_data in io_data.get('memory_vars', []):
            var = PLCVariable(
                name=var_data['name'],
                logical_address=var_data.get('logical_address', ''),
                data_type=var_data.get('data_type', 'BOOL'),
                byte_offset=var_data.get('byte_offset'),
                bit_offset=var_data.get('bit_offset'),
                area='M',
                description=var_data.get('description', '')
            )
            io_config.memory_vars[var.name] = var
        
        for db_num, db_data in io_data.get('db_vars', {}).items():
            db_num = int(db_num)
            io_config.db_vars[db_num] = {}
            for var_data in db_data:
                var = PLCVariable(
                    name=var_data['name'],
                    logical_address=var_data.get('logical_address', ''),
                    data_type=var_data.get('data_type', 'BOOL'),
                    db_number=db_num,
                    byte_offset=var_data.get('byte_offset'),
                    bit_offset=var_data.get('bit_offset'),
                    area='DB',
                    description=var_data.get('description', '')
                )
                io_config.db_vars[db_num][var.name] = var
        
        with self._lock:
            self._device_io_configs[device_id] = io_config
        
        return True
    
    def get_device_io_config(self, device_id: str) -> Optional[DeviceIOConfig]:
        """获取设备的IO配置"""
        with self._lock:
            return self._device_io_configs.get(device_id)
    
    def get_input_variables(self, device_id: str) -> Dict[str, PLCVariable]:
        """获取设备的输入变量"""
        config = self.get_device_io_config(device_id)
        return config.input_vars if config else {}
    
    def get_output_variables(self, device_id: str) -> Dict[str, PLCVariable]:
        """获取设备的输出变量"""
        config = self.get_device_io_config(device_id)
        return config.output_vars if config else {}
    
    def get_memory_variables(self, device_id: str) -> Dict[str, PLCVariable]:
        """获取设备的内存变量"""
        config = self.get_device_io_config(device_id)
        return config.memory_vars if config else {}
    
    def get_db_variables(self, device_id: str, db_number: int = None) -> Dict[str, PLCVariable]:
        """获取设备的DB变量"""
        config = self.get_device_io_config(device_id)
        if not config:
            return {}
        
        if db_number is not None:
            return config.db_vars.get(db_number, {})
        
        all_db_vars = {}
        for db_vars in config.db_vars.values():
            all_db_vars.update(db_vars)
        return all_db_vars
    
    def register_io_fault_mapping(self, io_name: str, fault_names: List[str]):
        """注册IO变量与故障的映射关系"""
        with self._lock:
            self._io_to_fault_mapping[io_name] = fault_names
            for fault_name in fault_names:
                if fault_name not in self._fault_to_io_mapping:
                    self._fault_to_io_mapping[fault_name] = []
                if io_name not in self._fault_to_io_mapping[fault_name]:
                    self._fault_to_io_mapping[fault_name].append(io_name)
    
    def get_faults_for_io(self, io_name: str) -> List[str]:
        """获取与IO变量相关的故障列表"""
        with self._lock:
            return self._io_to_fault_mapping.get(io_name, [])
    
    def get_ios_for_fault(self, fault_name: str) -> List[str]:
        """获取与故障相关的IO变量列表"""
        with self._lock:
            return self._fault_to_io_mapping.get(fault_name, [])
    
    def get_device_summary(self, device_id: str) -> Optional[Dict[str, Any]]:
        """获取设备的IO变量摘要"""
        config = self.get_device_io_config(device_id)
        return config.get_summary() if config else None
    
    def get_all_device_summaries(self) -> Dict[str, Dict[str, Any]]:
        """获取所有设备的IO变量摘要"""
        with self._lock:
            return {
                device_id: config.get_summary()
                for device_id, config in self._device_io_configs.items()
            }
    
    def is_io_available(self, device_id: str, io_name: str) -> bool:
        """检查IO变量是否存在"""
        config = self.get_device_io_config(device_id)
        if not config:
            return False
        
        return (
            io_name in config.input_vars or
            io_name in config.output_vars or
            io_name in config.memory_vars
        )
    
    def get_io_variable(self, device_id: str, io_name: str) -> Optional[PLCVariable]:
        """获取指定的IO变量"""
        config = self.get_device_io_config(device_id)
        if not config:
            return None
        
        if io_name in config.input_vars:
            return config.input_vars[io_name]
        elif io_name in config.output_vars:
            return config.output_vars[io_name]
        elif io_name in config.memory_vars:
            return config.memory_vars[io_name]
        
        for db_vars in config.db_vars.values():
            if io_name in db_vars:
                return db_vars[io_name]
        
        return None
    
    def get_variables_by_type(self, device_id: str, data_type: str) -> List[PLCVariable]:
        """按数据类型获取变量"""
        config = self.get_device_io_config(device_id)
        if not config:
            return []
        
        result = []
        data_type = data_type.upper()
        
        for var in config.input_vars.values():
            if var.data_type == data_type:
                result.append(var)
        
        for var in config.output_vars.values():
            if var.data_type == data_type:
                result.append(var)
        
        for var in config.memory_vars.values():
            if var.data_type == data_type:
                result.append(var)
        
        for db_vars in config.db_vars.values():
            for var in db_vars.values():
                if var.data_type == data_type:
                    result.append(var)
        
        return result
    
    def remove_device(self, device_id: str):
        """移除设备的IO配置"""
        with self._lock:
            if device_id in self._device_io_configs:
                del self._device_io_configs[device_id]
    
    def clear_all(self):
        """清空所有设备配置"""
        with self._lock:
            self._device_io_configs.clear()
            self._io_to_fault_mapping.clear()
            self._fault_to_io_mapping.clear()


def get_io_manager() -> IOVariableManager:
    """获取IO变量管理器单例"""
    return IOVariableManager()


def load_io_for_device(device_id: str, file_path: str, sheet_name: str = None) -> bool:
    """为设备加载IO变量"""
    manager = get_io_manager()
    return manager.load_io_variables(device_id, file_path, sheet_name)