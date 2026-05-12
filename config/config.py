"""
Configuration module for PLC Monitor System.

This module provides centralized configuration management with type hints
and support for environment variable overrides.
"""

import os
from typing import Optional, Dict


class Config:
    """
    Main configuration class for PLC Monitor System.
    
    All values can be overridden via environment variables:
    - PLC_HOST -> PLC_HOST
    - PLC_RACK -> PLC_RACK
    - PLC_SLOT -> PLC_SLOT
    - PLC_CONNECTION_TIMEOUT -> PLC_CONNECTION_TIMEOUT
    - PLC_RETRY_INTERVAL -> PLC_RETRY_INTERVAL
    - DATA_SAMPLING_INTERVAL -> DATA_SAMPLING_INTERVAL
    - DATA_HISTORY_DAYS -> DATA_HISTORY_DAYS
    - ANALYSIS_WINDOW_SIZE -> ANALYSIS_WINDOW_SIZE
    - ANALYSIS_THRESHOLD -> ANALYSIS_THRESHOLD
    - ANALYSIS_PREDICTION_INTERVAL -> ANALYSIS_PREDICTION_INTERVAL
    - SERVER_PORT -> SERVER_PORT
    - SERVER_HOST -> SERVER_HOST
    - LOGGING_LEVEL -> LOGGING_LEVEL
    - LOGGING_FILE -> LOGGING_FILE
    """
    
    # Base Paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    PLC_DEFINITIONS_DIR: str = os.path.join(BASE_DIR, 'plc_definitions')
    
    # Device ID to XLSX file mapping
    DEVICE_XLSX_MAPPING: Dict[str, str] = {
        'plc_001': 'RXA1300PLCTags.xlsx',
        'plc_002': 'RXB800PLCTags.xlsx',
        'plc_rxa800': 'RXA800PLCTags.xlsx',
        'plc_rxa630_1': 'RXA630-1PLCTags.xlsx',
        'plc_rxa630_2': 'RXA630-2PLCTags.xlsx',
        'plc_rxa630_3': 'RXA630-3PLCTags.xlsx',
        'plc_rxa630_4': 'RXA630-4PLCTags.xlsx',
    }
    
    # PLC Connection Settings
    PLC_HOST: str = os.environ.get('PLC_HOST', '172.15.14.150')
    PLC_RACK: int = int(os.environ.get('PLC_RACK', '0'))
    PLC_SLOT: int = int(os.environ.get('PLC_SLOT', '1'))
    PLC_CONNECTION_TIMEOUT: int = int(os.environ.get('PLC_CONNECTION_TIMEOUT', '10000'))
    PLC_RETRY_INTERVAL: int = int(os.environ.get('PLC_RETRY_INTERVAL', '5000'))
    PLC_MAX_RETRY_ATTEMPTS: int = int(os.environ.get('PLC_MAX_RETRY_ATTEMPTS', '0'))
    PLC_RECONNECT_BACKOFF_ENABLED: bool = bool(int(os.environ.get('PLC_RECONNECT_BACKOFF_ENABLED', '1')))
    
    # Data Collection Settings
    DATA_SAMPLING_INTERVAL: int = int(os.environ.get('DATA_SAMPLING_INTERVAL', '100'))
    DATA_HISTORY_DAYS: int = int(os.environ.get('DATA_HISTORY_DAYS', '30'))
    DATA_CACHE_MAX_SIZE: int = int(os.environ.get('DATA_CACHE_MAX_SIZE', '10000'))
    DATA_CACHE_EXPIRE_SECONDS: int = int(os.environ.get('DATA_CACHE_EXPIRE_SECONDS', '300'))
    
    # Analysis Settings
    ANALYSIS_WINDOW_SIZE: int = int(os.environ.get('ANALYSIS_WINDOW_SIZE', '60'))
    ANALYSIS_THRESHOLD: float = float(os.environ.get('ANALYSIS_THRESHOLD', '0.8'))
    ANALYSIS_PREDICTION_INTERVAL: int = int(os.environ.get('ANALYSIS_PREDICTION_INTERVAL', '5000'))
    ANALYSIS_ENABLED: bool = bool(int(os.environ.get('ANALYSIS_ENABLED', '1')))
    
    # Server Settings
    SERVER_PORT: int = int(os.environ.get('SERVER_PORT', '3000'))
    SERVER_HOST: str = os.environ.get('SERVER_HOST', '0.0.0.0')
    SERVER_DEBUG: bool = bool(int(os.environ.get('SERVER_DEBUG', '0')))
    SERVER_WORKERS: int = int(os.environ.get('SERVER_WORKERS', '1'))
    
    # Logging Settings
    LOGGING_LEVEL: str = os.environ.get('LOGGING_LEVEL', 'info').lower()
    LOGGING_FILE: str = os.environ.get('LOGGING_FILE', './logs/app.log')
    LOGGING_MAX_FILE_SIZE: int = int(os.environ.get('LOGGING_MAX_FILE_SIZE', '10485760'))  # 10MB
    LOGGING_BACKUP_COUNT: int = int(os.environ.get('LOGGING_BACKUP_COUNT', '5'))
    
    # SocketIO Settings
    SOCKETIO_ASYNC_MODE: str = os.environ.get('SOCKETIO_ASYNC_MODE', 'threading')
    SOCKETIO_CORS_ALLOWED_ORIGINS: str = os.environ.get('SOCKETIO_CORS_ALLOWED_ORIGINS', '*')
    SOCKETIO_TRANSPORTS: str = os.environ.get('SOCKETIO_TRANSPORTS', 'polling')
    
    # Database Settings
    DATABASE_PATH: str = os.environ.get('DATABASE_PATH', './database.db')
    DATABASE_TIMEOUT: int = int(os.environ.get('DATABASE_TIMEOUT', '30'))
    DATABASE_CACHE_SIZE: int = int(os.environ.get('DATABASE_CACHE_SIZE', '10000'))
    
    # Connection Pool Settings
    CONNECTION_POOL_MAX_WORKERS: int = int(os.environ.get('CONNECTION_POOL_MAX_WORKERS', '10'))
    CONNECTION_POOL_HEALTH_CHECK_INTERVAL: int = int(os.environ.get('CONNECTION_POOL_HEALTH_CHECK_INTERVAL', '10'))
    
    # Health Check Settings
    HEALTH_CHECK_ENABLED: bool = bool(int(os.environ.get('HEALTH_CHECK_ENABLED', '1')))
    HEALTH_CHECK_INTERVAL: int = int(os.environ.get('HEALTH_CHECK_INTERVAL', '30'))
    
    # Network Switch Settings
    NETWORK_SWITCH_TIMEOUT: int = int(os.environ.get('NETWORK_SWITCH_TIMEOUT', '5000'))
    AUTO_DETECT_INTERFACES: bool = bool(int(os.environ.get('AUTO_DETECT_INTERFACES', '1')))
    NETWORK_MONITOR_INTERVAL: int = int(os.environ.get('NETWORK_MONITOR_INTERVAL', '3000'))
    
    # Simulation Mode Settings
    SIMULATION_MODE: bool = bool(int(os.environ.get('SIMULATION_MODE', '1')))  # 默认启用模拟模式
    SIMULATION_DATA_ENABLED: bool = bool(int(os.environ.get('SIMULATION_DATA_ENABLED', '1')))  # 启用模拟数据生成
    
    def __repr__(self) -> str:
        return f"<Config PLC_HOST={self.PLC_HOST} SERVER_PORT={self.SERVER_PORT}>"
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary for inspection."""
        return {
            'plc': {
                'host': self.PLC_HOST,
                'rack': self.PLC_RACK,
                'slot': self.PLC_SLOT,
                'connection_timeout': self.PLC_CONNECTION_TIMEOUT,
                'retry_interval': self.PLC_RETRY_INTERVAL,
                'max_retry_attempts': self.PLC_MAX_RETRY_ATTEMPTS,
                'reconnect_backoff_enabled': self.PLC_RECONNECT_BACKOFF_ENABLED
            },
            'data': {
                'sampling_interval': self.DATA_SAMPLING_INTERVAL,
                'history_days': self.DATA_HISTORY_DAYS,
                'cache_max_size': self.DATA_CACHE_MAX_SIZE,
                'cache_expire_seconds': self.DATA_CACHE_EXPIRE_SECONDS
            },
            'analysis': {
                'window_size': self.ANALYSIS_WINDOW_SIZE,
                'threshold': self.ANALYSIS_THRESHOLD,
                'prediction_interval': self.ANALYSIS_PREDICTION_INTERVAL,
                'enabled': self.ANALYSIS_ENABLED
            },
            'server': {
                'host': self.SERVER_HOST,
                'port': self.SERVER_PORT,
                'debug': self.SERVER_DEBUG,
                'workers': self.SERVER_WORKERS
            },
            'logging': {
                'level': self.LOGGING_LEVEL,
                'file': self.LOGGING_FILE,
                'max_file_size': self.LOGGING_MAX_FILE_SIZE,
                'backup_count': self.LOGGING_BACKUP_COUNT
            },
            'socketio': {
                'async_mode': self.SOCKETIO_ASYNC_MODE,
                'cors_allowed_origins': self.SOCKETIO_CORS_ALLOWED_ORIGINS,
                'transports': self.SOCKETIO_TRANSPORTS
            },
            'database': {
                'path': self.DATABASE_PATH,
                'timeout': self.DATABASE_TIMEOUT,
                'cache_size': self.DATABASE_CACHE_SIZE
            },
            'connection_pool': {
                'max_workers': self.CONNECTION_POOL_MAX_WORKERS,
                'health_check_interval': self.CONNECTION_POOL_HEALTH_CHECK_INTERVAL
            },
            'health_check': {
                'enabled': self.HEALTH_CHECK_ENABLED,
                'interval': self.HEALTH_CHECK_INTERVAL
            }
        }


config = Config()


def get_config() -> Config:
    """Get the global configuration instance."""
    return config


def load_config_from_env(env_file: str = '.env') -> None:
    """
    Load configuration from environment file.
    
    Args:
        env_file: Path to the .env file (default: '.env')
    """
    if os.path.exists(env_file):
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
            print(f"Loaded environment variables from {env_file}")
        except Exception as e:
            print(f"Failed to load environment file {env_file}: {e}")
