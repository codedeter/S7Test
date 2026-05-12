from typing import Dict, Type, Any, Optional, Callable
from dataclasses import dataclass
import threading


@dataclass
class ServiceRegistration:
    type: Type
    instance: Any = None
    singleton: bool = True
    factory: Optional[Callable[[], Any]] = None


class DIContainer:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DIContainer, cls).__new__(cls)
                    cls._instance._services: Dict[str, ServiceRegistration] = {}
        return cls._instance

    def register(self, name: str, type: Type, singleton: bool = True):
        """
        注册服务类型
        
        Args:
            name: 服务名称
            type: 服务类型（类）
            singleton: 是否为单例（默认为True）
        """
        self._services[name] = ServiceRegistration(type=type, singleton=singleton)

    def register_singleton(self, name: str, instance: Any):
        """
        注册单例实例
        
        Args:
            name: 服务名称
            instance: 服务实例
        """
        self._services[name] = ServiceRegistration(
            type=type(instance),
            instance=instance,
            singleton=True
        )

    def register_factory(self, name: str, factory: Callable[[], Any], singleton: bool = True):
        """
        使用工厂函数注册服务
        
        Args:
            name: 服务名称
            factory: 工厂函数，返回服务实例
            singleton: 是否为单例（默认为True）
        """
        self._services[name] = ServiceRegistration(
            type=type(None),
            singleton=singleton,
            factory=factory
        )

    def get(self, name: str) -> Any:
        """
        获取服务实例
        
        Args:
            name: 服务名称
            
        Returns:
            服务实例
            
        Raises:
            ValueError: 如果服务未注册
        """
        registration = self._services.get(name)
        if not registration:
            raise ValueError(f"Service not registered: {name}")

        if registration.factory is not None:
            if registration.singleton and registration.instance is None:
                registration.instance = registration.factory()
            return registration.instance if registration.singleton else registration.factory()

        if registration.singleton and registration.instance is None:
            registration.instance = registration.type()

        return registration.instance if registration.singleton else registration.type()

    def has(self, name: str) -> bool:
        """
        检查服务是否已注册
        
        Args:
            name: 服务名称
            
        Returns:
            如果已注册返回True，否则返回False
        """
        return name in self._services

    def clear(self):
        """
        清除所有已注册的服务
        """
        self._services.clear()


def get_container() -> DIContainer:
    """
    获取全局依赖注入容器实例
    
    Returns:
        DIContainer实例
    """
    return DIContainer()
