"""轻量级依赖注入容器 — Service Locator 模式

用法：
    from app.core.container import Container

    # 注册
    Container.register("llm_client", LLMClient())
    Container.register("store", lambda: ProjectStore(Config.PROJECT_STORE_PATH))

    # 获取
    client = Container.get("llm_client")
    store = Container.resolve("store")  # 惰性创建
"""

from typing import Any, Callable, Dict, Optional
import threading


class Container:
    """全局依赖注入容器"""

    _services: Dict[str, Any] = {}
    _factories: Dict[str, Callable] = {}
    _singletons: Dict[str, Any] = {}
    _lock = threading.Lock()

    @classmethod
    def register(cls, name: str, service_or_factory: Any, singleton: bool = True):
        """注册服务实例或工厂函数。

        Args:
            name: 服务名称
            service_or_factory: 实例或返回实例的 callable
            singleton: 如果是工厂，是否单例模式
        """
        with cls._lock:
            if callable(service_or_factory) and not isinstance(service_or_factory, type):
                cls._factories[name] = service_or_factory
                if singleton:
                    pass  # 惰性创建，首次 get 时实例化
                else:
                    cls._services[name] = service_or_factory
            else:
                cls._services[name] = service_or_factory

    @classmethod
    def get(cls, name: str) -> Any:
        """获取已注册的服务实例。未注册返回 None。"""
        with cls._lock:
            if name in cls._services:
                return cls._services[name]
            if name in cls._singletons:
                return cls._singletons[name]
            if name in cls._factories:
                instance = cls._factories[name]()
                cls._singletons[name] = instance
                return instance
        return None

    @classmethod
    def resolve(cls, name: str, default: Any = None) -> Any:
        """获取服务，未注册时返回 default。"""
        result = cls.get(name)
        return result if result is not None else default

    @classmethod
    def has(cls, name: str) -> bool:
        """检查服务是否已注册。"""
        with cls._lock:
            return name in cls._services or name in cls._factories or name in cls._singletons

    @classmethod
    def reset(cls):
        """重置容器（测试用）。"""
        with cls._lock:
            cls._services.clear()
            cls._factories.clear()
            cls._singletons.clear()
