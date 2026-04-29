import time
import enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable
from threading import Lock


class StartupPhase(enum.Enum):
    INITIALIZING = "initializing"
    DATABASE_INIT = "database_init"
    DEVICE_MANAGER_CREATE = "device_manager_create"
    DEVICES_INIT = "devices_init"
    FLASK_APP_CREATE = "flask_app_create"
    ROUTES_REGISTER = "routes_register"
    SERVICES_START = "services_start"
    BACKGROUND_CONNECT = "background_connect"
    RUNNING = "running"
    ERROR = "error"
    STOPPED = "stopped"


class StartupStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PhaseResult:
    status: StartupStatus
    message: str = ""
    error: Optional[Exception] = None
    duration_ms: float = 0.0


@dataclass
class StartupContext:
    phase_results: Dict[StartupPhase, PhaseResult] = field(default_factory=dict)
    current_phase: StartupPhase = StartupPhase.INITIALIZING
    start_time: float = 0.0
    end_time: float = 0.0
    overall_status: StartupStatus = StartupStatus.PENDING
    error_message: str = ""
    
    def mark_phase_start(self, phase: StartupPhase):
        self.current_phase = phase
        self.phase_results[phase] = PhaseResult(
            status=StartupStatus.IN_PROGRESS,
            message="Phase started"
        )
    
    def mark_phase_complete(self, phase: StartupPhase, message: str = ""):
        if phase in self.phase_results:
            duration = (time.time() * 1000) - self._get_phase_start_time(phase)
            self.phase_results[phase] = PhaseResult(
                status=StartupStatus.COMPLETED,
                message=message or "Phase completed",
                duration_ms=duration
            )
    
    def mark_phase_failed(self, phase: StartupPhase, error: Exception):
        duration = (time.time() * 1000) - self._get_phase_start_time(phase)
        self.phase_results[phase] = PhaseResult(
            status=StartupStatus.FAILED,
            message=str(error),
            error=error,
            duration_ms=duration
        )
        self.current_phase = phase
        self.overall_status = StartupStatus.FAILED
        self.error_message = str(error)
    
    def _get_phase_start_time(self, phase: StartupPhase) -> float:
        return self.start_time if phase == StartupPhase.INITIALIZING else time.time() * 1000
    
    def is_complete(self) -> bool:
        return self.current_phase == StartupPhase.RUNNING
    
    def is_failed(self) -> bool:
        return self.overall_status == StartupStatus.FAILED
    
    def get_progress(self) -> float:
        total_phases = len(StartupPhase) - 2
        completed_phases = sum(1 for r in self.phase_results.values() if r.status == StartupStatus.COMPLETED)
        return (completed_phases / total_phases) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'current_phase': self.current_phase.value,
            'overall_status': self.overall_status.value,
            'progress': round(self.get_progress(), 2),
            'start_time': self.start_time,
            'end_time': self.end_time,
            'error_message': self.error_message,
            'phase_details': {
                phase.value: {
                    'status': result.status.value,
                    'message': result.message,
                    'duration_ms': round(result.duration_ms, 2)
                }
                for phase, result in self.phase_results.items()
            }
        }


class StartupManager:
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._context = StartupContext()
                cls._instance._shutdown_callbacks = []
                cls._instance._startup_callbacks = []
                cls._instance._is_shutting_down = False
            return cls._instance
    
    @property
    def context(self) -> StartupContext:
        return self._context
    
    @property
    def is_running(self) -> bool:
        return self._context.current_phase == StartupPhase.RUNNING and not self._is_shutting_down
    
    @property
    def is_shutting_down(self) -> bool:
        return self._is_shutting_down
    
    def add_shutdown_callback(self, callback: Callable[[], None]):
        self._shutdown_callbacks.append(callback)
    
    def add_startup_callback(self, callback: Callable[[StartupPhase], None]):
        self._startup_callbacks.append(callback)
    
    def begin_startup(self):
        self._context.start_time = time.time()
        self._context.overall_status = StartupStatus.IN_PROGRESS
        self._notify_startup_callbacks(StartupPhase.INITIALIZING)
    
    def start_phase(self, phase: StartupPhase):
        self._context.mark_phase_start(phase)
        print(f"[Startup] [{phase.value}] Starting...")
        self._notify_startup_callbacks(phase)
    
    def complete_phase(self, phase: StartupPhase, message: str = ""):
        self._context.mark_phase_complete(phase, message)
        print(f"[Startup] [{phase.value}] OK Completed ({self._context.phase_results[phase].duration_ms:.2f}ms)")
    
    def fail_phase(self, phase: StartupPhase, error: Exception):
        self._context.mark_phase_failed(phase, error)
        print(f"[Startup] [{phase.value}] FAIL Failed: {error}")
    
    def finish_startup(self):
        self._context.end_time = time.time()
        self._context.current_phase = StartupPhase.RUNNING
        self._context.overall_status = StartupStatus.COMPLETED
        
        total_duration = (self._context.end_time - self._context.start_time) * 1000
        print(f"\n[Startup] ========================================")
        print(f"[Startup] Server started successfully!")
        print(f"[Startup] Total duration: {total_duration:.2f}ms")
        print(f"[Startup] ========================================")
        self._notify_startup_callbacks(StartupPhase.RUNNING)
    
    def shutdown(self):
        if self._is_shutting_down:
            return
        
        self._is_shutting_down = True
        self._context.current_phase = StartupPhase.STOPPED
        
        print("\n[Startup] Initiating shutdown...")
        
        for callback in self._shutdown_callbacks:
            try:
                callback()
            except Exception as e:
                print(f"[Startup] Error during shutdown callback: {e}")
        
        self._context.overall_status = StartupStatus.COMPLETED
        print("[Startup] Shutdown complete")
    
    def _notify_startup_callbacks(self, phase: StartupPhase):
        for callback in self._startup_callbacks:
            try:
                callback(phase)
            except Exception as e:
                print(f"[Startup] Error in startup callback: {e}")


def get_startup_manager() -> StartupManager:
    return StartupManager()