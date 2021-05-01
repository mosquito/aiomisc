from threading import RLock
from typing import Any, Hashable, Dict, Optional

from llist import dllist, dllistnode

from aiomisc.cache.base import CachePolicy
from aiomisc.cache.dllist import Item


class LRUCachePolicy(CachePolicy):
    """
        LRU cache implementation

        >>> cache = {}
        >>> lfu = LRUCachePolicy(cache, 3)
        >>> lfu.set("foo", "bar")
        >>> assert "foo" in lfu
        >>> lfu.get('foo')
        'bar'

        >>> lfu.remove('foo')
        >>> assert "foo" not in lfu
        >>> lfu.get("foo")
        Traceback (most recent call last):
        ...
        KeyError: 'foo'
        >>> lfu.remove("foo")

        >>> lfu.set("bar", "foo")
        >>> lfu.set("spam", "egg")
        >>> lfu.set("foo", "bar")
        >>> lfu.get("foo")
        'bar'
        >>> lfu.get("spam")
        'egg'
        >>> assert len(lfu) == 3
        >>> lfu.set("egg", "spam")
        >>> assert len(lfu) == 3, str(len(lfu)) + " is not 3"
    """

    lock: RLock
    usages: dllist

    __slots__ = 'lock', 'usages'

    def _on_init(self):
        self.usages: dllist = dllist()
        self.lock: RLock = RLock()

    def _on_overflow(self):
        with self.lock:
            while self._is_overflow():
                node: Optional[dllistnode] = self.usages.popleft()

                if node is None:
                    return

                item: Item = node.value
                self.cache.pop(item.key, None)

                del item.node
                del item.key
                del item.value

    def _is_overflow(self) -> bool:
        return len(self.cache) > self.max_size

    def get(self, key: Hashable):
        item: dllistnode = self.cache[key]

        with self.lock:
            self.usages.remove(item)
            self.usages.appendright(item.value)

        return item.value.value

    def remove(self, key: Hashable):
        with self.lock:
            node: Optional[dllistnode] = self.cache.pop(key, None)

            if node is None:
                return

            self.usages.remove(node)
            print(node)

    def set(self, key: Hashable, value: Any):
        with self.lock:
            item = Item(node=None, key=key, value=value)
            node = self.usages.appendright(item)
            item.node = node
            self.cache[key] = node

        if self._is_overflow():
            self._on_overflow()

    def __contains__(self, key: Hashable):
        return key in self.cache

    def __len__(self):
        return len(self.cache)
