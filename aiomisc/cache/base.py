from abc import ABC, abstractmethod
from typing import Any, Hashable, Dict


class CachePolicy(ABC):
    __slots__ = "max_size", "cache"

    def __init__(self, cache: Dict[Hashable, Any], max_size: int = 0):
        self.max_size = max_size
        self.cache = cache
        self._on_init()

    def _on_init(self):
        pass

    @abstractmethod
    def get(self, key: Hashable):
        raise NotImplementedError

    @abstractmethod
    def remove(self, key: Hashable):
        raise NotImplementedError

    @abstractmethod
    def set(self, key: Hashable, value: Any):
        raise NotImplementedError

    @abstractmethod
    def __contains__(self, key: Hashable):
        raise NotImplementedError

    @abstractmethod
    def __len__(self):
        raise NotImplementedError
