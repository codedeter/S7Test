from typing import Dict, Type, Any, Optional, Callable, get_type_hints
from dataclasses import dataclass
import threading


@dataclass
class ServiceRegistration:
    type: Type
    instance: Any = None
    singleton: bool = True
    factory: Optional[Callable[[], Any]] = None
    dependencies: list = None


class EnhancedDIContainer:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(EnhancedDIContainer, cls).__new__(cls)
                    cls._instance._services: Dict[str, ServiceRegistration] = {}
        return cls._instance

    def register(self, name: str, type: Type, singleton: bool = True):
        hints = get_type_hints(type.__init__)
        
        import inspect
        sig = inspect.signature(type.__init__)
        dependencies = []
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            if param.default == inspect.Parameter.empty:
                dependencies.append(param_name)

        self._services[name] = ServiceRegistration(
            type=type,
            singleton=singleton,
            dependencies=dependencies
        )

    def register_singleton(self, name: str, instance: Any):
        self._services[name] = ServiceRegistration(
            type=type(instance),
            instance=instance,
            singleton=True
        )

    def register_factory(self, name: str, factory: Callable[..., Any], singleton: bool = True):
        hints = get_type_hints(factory)
        dependencies = [k for k in hints.keys() if k != 'return']

        self._services[name] = ServiceRegistration(
            type=type(None),
            singleton=singleton,
            factory=factory,
            dependencies=dependencies
        )

    def get(self, name: str) -> Any:
        registration = self._services.get(name)
        if not registration:
            raise ValueError(f"Service not registered: {name}")

        if registration.singleton and registration.instance is not None:
            return registration.instance

        resolved_deps = {}
        if registration.dependencies:
            for dep_name in registration.dependencies:
                resolved_deps[dep_name] = self.get(dep_name)

        if registration.factory:
            instance = registration.factory(**resolved_deps)
        else:
            instance = registration.type(**resolved_deps)

        if registration.singleton:
            registration.instance = instance

        return instance

    def has(self, name: str) -> bool:
        return name in self._services

    def clear(self):
        self._services.clear()


def get_container() -> EnhancedDIContainer:
    return EnhancedDIContainer()