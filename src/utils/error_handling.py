import sys
import traceback
import time
import json
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock

sys.setrecursionlimit(10000)


class ErrorLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorType(Enum):
    CONNECTION_ERROR = "connection_error"
    DATA_READ_ERROR = "data_read_error"
    DATA_WRITE_ERROR = "data_write_error"
    PARSE_ERROR = "parse_error"
    VALIDATION_ERROR = "validation_error"
    CONFIG_ERROR = "config_error"
    RUNTIME_ERROR = "runtime_error"
    TIMEOUT_ERROR = "timeout_error"
    RESOURCE_ERROR = "resource_error"


@dataclass
class ErrorRecord:
    error_id: str
    error_type: ErrorType
    level: ErrorLevel
    message: str
    timestamp: float
    stack_trace: Optional[str] = None
    device_id: Optional[str] = None
    additional_info: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'error_id': self.error_id,
            'error_type': self.error_type.value,
            'level': self.level.value,
            'message': self.message,
            'timestamp': self.timestamp,
            'stack_trace': self.stack_trace,
            'device_id': self.device_id,
            'additional_info': self.additional_info
        }


class GlobalErrorHandler:
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._error_callbacks = []
                cls._recent_errors = []
                cls._max_recent_errors = 100
                cls._error_counts: Dict[str, int] = {}
                cls._enabled = True
            return cls._instance
    
    def add_error_callback(self, callback: Callable[[ErrorRecord], None]):
        self._error_callbacks.append(callback)
    
    def remove_error_callback(self, callback: Callable[[ErrorRecord], None]):
        if callback in self._error_callbacks:
            self._error_callbacks.remove(callback)
    
    def log_error(
        self,
        error_type: ErrorType,
        message: str,
        level: ErrorLevel = ErrorLevel.ERROR,
        device_id: Optional[str] = None,
        exception: Optional[Exception] = None,
        **additional_info
    ) -> ErrorRecord:
        if not self._enabled:
            return None
        
        stack_trace = None
        if exception:
            stack_trace = traceback.format_exc()
        
        error_id = f"err_{int(time.time() * 1000)}_{hash(message) % 10000}"
        
        record = ErrorRecord(
            error_id=error_id,
            error_type=error_type,
            level=level,
            message=message,
            timestamp=time.time(),
            stack_trace=stack_trace,
            device_id=device_id,
            additional_info=additional_info
        )
        
        self._record_error(record)
        self._notify_callbacks(record)
        self._print_error(record)
        
        return record
    
    def _record_error(self, record: ErrorRecord):
        self._recent_errors.insert(0, record)
        
        if len(self._recent_errors) > self._max_recent_errors:
            self._recent_errors.pop()
        
        error_type_str = record.error_type.value
        self._error_counts[error_type_str] = self._error_counts.get(error_type_str, 0) + 1
    
    def _notify_callbacks(self, record: ErrorRecord):
        for callback in self._error_callbacks:
            try:
                callback(record)
            except Exception as e:
                print(f"Error callback failed: {e}")
    
    def _print_error(self, record: ErrorRecord):
        device_prefix = f"[{record.device_id}] " if record.device_id else ""
        print(f"[{record.level.value.upper()}] {device_prefix}{record.message}")
        
        if record.stack_trace:
            print(f"Stack trace:\n{record.stack_trace}")
    
    def get_recent_errors(self, limit: int = 20) -> list:
        return [e.to_dict() for e in self._recent_errors[:limit]]
    
    def get_error_counts(self) -> Dict[str, int]:
        return self._error_counts.copy()
    
    def clear_errors(self):
        self._recent_errors = []
        self._error_counts = {}
    
    def disable(self):
        self._enabled = False
    
    def enable(self):
        self._enabled = True


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    error_handler = GlobalErrorHandler()
    
    error_type = ErrorType.RUNTIME_ERROR
    if issubclass(exc_type, ConnectionError):
        error_type = ErrorType.CONNECTION_ERROR
    elif issubclass(exc_type, TimeoutError):
        error_type = ErrorType.TIMEOUT_ERROR
    elif issubclass(exc_type, ValueError):
        error_type = ErrorType.VALIDATION_ERROR
    elif issubclass(exc_type, IOError):
        error_type = ErrorType.RESOURCE_ERROR
    
    error_handler.log_error(
        error_type=error_type,
        message=str(exc_value),
        level=ErrorLevel.CRITICAL,
        stack_trace=''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    )


sys.excepthook = handle_exception


def get_error_handler() -> GlobalErrorHandler:
    return GlobalErrorHandler()


def safe_execute(
    func: Callable,
    *args,
    error_type: ErrorType = ErrorType.RUNTIME_ERROR,
    device_id: Optional[str] = None,
    fallback=None,
    **kwargs
) -> Any:
    try:
        return func(*args, **kwargs)
    except Exception as e:
        error_handler = get_error_handler()
        error_handler.log_error(
            error_type=error_type,
            message=f"Safe execute failed: {str(e)}",
            device_id=device_id,
            exception=e,
            function=func.__name__
        )
        return fallback


def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
    error_type: ErrorType = ErrorType.RUNTIME_ERROR,
    device_id: Optional[str] = None,
    *args,
    **kwargs
) -> Any:
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            delay = base_delay * (backoff_factor ** attempt)
            
            error_handler = get_error_handler()
            error_handler.log_error(
                error_type=error_type,
                message=f"Retry attempt {attempt + 1}/{max_retries} failed: {str(e)}",
                level=ErrorLevel.WARNING,
                device_id=device_id
            )
            
            if attempt < max_retries - 1:
                time.sleep(delay)
    
    error_handler = get_error_handler()
    error_handler.log_error(
        error_type=error_type,
        message=f"All {max_retries} retries failed: {str(last_exception)}",
        level=ErrorLevel.CRITICAL,
        device_id=device_id,
        exception=last_exception
    )
    
    raise last_exception