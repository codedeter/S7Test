# PLC Monitor System - Main Package

# Core modules
from .server import main, create_app, register_routes

# Device management
from .devices import (
    DeviceManager,
    DeviceCollector,
    PLCClient,
    CollectedData,
    create_device_manager,
    ConnectionPool,
    ConnectionState,
    ConnectionConfig,
    ConnectionStats,
    create_connection_pool,
    DeviceConfig,
    DeviceStatus,
    ConnectionStatus,
    DeviceType,
    create_device_config
)

# Data processing
from .services import DataProcessor
from .data import DataStorage

# API
from .api.routes import register_routes

# Analysis
from .analysis import (
    DataAnalyzer,
    FaultDetectorRegistry,
    create_detector,
    SliderDownAbnormalDetector,
    create_slider_detector
)

# SocketIO
from .socketio_handler import SocketIOHandler, DataCollectionTask

# Startup
from .startup import StartupManager, get_startup_manager

# Utilities
from .utils import (
    GlobalErrorHandler,
    get_error_handler,
    safe_execute,
    retry_with_backoff,
    ErrorType,
    ErrorLevel,
    ConfigValidator,
    RuntimeChecker,
    get_validator,
    get_runtime_checker
)

# Serialization
from .serialization import DataSerializer, DataDelta, DataPacker

__all__ = [
    # Core
    'main',
    'create_app',
    'register_routes',
    
    # Device management
    'DeviceManager',
    'DeviceCollector',
    'PLCClient',
    'CollectedData',
    'create_device_manager',
    'ConnectionPool',
    'ConnectionState',
    'ConnectionConfig',
    'ConnectionStats',
    'create_connection_pool',
    'DeviceConfig',
    'DeviceStatus',
    'ConnectionStatus',
    'DeviceType',
    'create_device_config',
    
    # Data processing
    'DataProcessor',
    'DataStorage',
    
    # API
    'register_routes',
    
    # Analysis
    'DataAnalyzer',
    'FaultDetectorRegistry',
    'create_detector',
    'SliderDownAbnormalDetector',
    'create_slider_detector',
    
    # SocketIO
    'SocketIOHandler',
    'DataCollectionTask',
    
    # Startup
    'StartupManager',
    'get_startup_manager',
    
    # Utilities
    'GlobalErrorHandler',
    'get_error_handler',
    'safe_execute',
    'retry_with_backoff',
    'ErrorType',
    'ErrorLevel',
    'ConfigValidator',
    'RuntimeChecker',
    'get_validator',
    'get_runtime_checker',
    
    # Serialization
    'DataSerializer',
    'DataDelta',
    'DataPacker',
]