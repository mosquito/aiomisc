from threading import RLock
from typing import Any, Hashable, Optional, Dict, Set
from aiomisc.cache.base import CachePolicy
from llist import dllist, dllistnode

from aiomisc.cache.dllist import Item


class LFUCachePolicy(CachePolicy):
    """
    LFU cache implementation

    >>> cache = {}
    >>> lfu = LFUCachePolicy(cache, 3)
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
    >>> assert len(lfu) == 3
    """

    __slots__ = "usages", "lock"

    def _on_init(self):
        self.usages: dllist = dllist()
        self.lock: RLock = RLock()

    def _update_usage(self, item: Item):
        with self.lock:
            pass

    def _item_remove(self, item: Item):
        with self.lock:
            if item in item.node.value:
                item.node.value.remove(item)

            item.node = None

    def _on_overflow(self):
        with self.lock:
            while self._is_overflow():
                if not self.usages.value:
                    if self.usages.next is not None:
                        self.usages.next.prev = None
                        self.usages = self.usages.next
                    else:
                        self.usages = Node(prev=None, next=None)
                    continue

                item = self.usages.value.pop()
                self.cache.pop(item.key, None)
                self._item_remove(item)

    def _is_overflow(self) -> bool:
        return len(self.cache) > self.max_size

    def __contains__(self, key: Hashable) -> Any:
        if key in self.cache:
            self._update_usage(self.cache[key])
            return True
        return False

    def __len__(self):
        return len(self.cache)

    def get(self, key: Hashable):
        item: Item = self.cache[key]
        self._update_usage(item)
        return item.value

    def remove(self, key: Hashable):
        with self.lock:
            item: Optional[Item] = self.cache.pop(key, None)
            if item is None:
                return

            self._item_remove(item)

    def set(self, key: Hashable, value: Any):
        with self.lock:
            node: Optional[Node] = self.usages

            if node is None:
                node = Node()
                self.usages = node

            item = Item(node=node, key=key, value=value)
            node.value.add(item)
            self.cache[key] = item

        if self._is_overflow():
            self._on_overflow()
