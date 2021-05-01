from multiprocessing import RLock
from typing import Optional, Any, Hashable, Type


class Node:
    __slots__ = 'prev', 'next', 'value', 'parent'

    prev: Optional["Node"]
    next: Optional["Node"]
    parent: "DLList"

    def __init__(self, parent: "DLList", prev: "Node" = None,
                 next: "Node" = None):
        self.parent = parent
        self.prev = prev
        self.next = next
        self.value = None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} " \
               f"{id(self)}: next={id(self.next)} " \
               f"prev={id(self.prev)}>"

    def remove(self):
        if self.next is None:
            return

        with self.parent.lock:
            self.prev.next = self.next
            self.prev = None
            self.next = None

    def append_left(self, node: "Node") -> "Node":
        """
        Appends node before the parent node

        before:

            ... <-> [self] <-> ...

        after:

            ... <-> [node] <-> [self] <-> ...

        """
        with self.parent.lock:
            self.parent.nodes.add(node)
            node.next = self

            if self.prev is not None:
                node.prev = self.prev

            self.prev = node
            return node

    def append_right(self, node: "Node") -> "Node":
        """
        Appends node after parent node

        before:

            ... <-> [self] <-> ...

        after:

            ... <-> [self] <-> [node] <-> ...

        """

        with self.parent.lock:
            self.parent.nodes.add(node)
            node.prev = self

            if self.next is not None:
                node.next = self.next

            self.next = node
            return node

    def swap(self, other: "Node"):
        """
        Swaps two Nodes and change neighbor links

        Example: doubly linked list looks like:

              [x] <-> [self]    <->    [z]   <->  [other]  <->    [y]
            node x    node self      node z    node other     node y
            p    n    p       n    p        n    p        n    p      n
            -------------------------------------------------------
            - self    x       z    self other    z        y    other  -

        After swap should looks like:

              [x]  <->  [other] <->    [z]  <->  [self]   <->   [y]
            node  x    node other    node  z    node self     node y
            p     n    p        n    p     n    p       n    p      n
            --------------------------------------------------------
            - other    x        z    other b    z       y    other  -

        That's means we should make 8 changes

            # 4 for "a" and "b"
            a.prev, a.next, b.prev, b.next = b.prev, b.next, a.prev, a.next

            # 4 for neighbors
            x.next, z.prev, z.next, y.prev = b, b, a, a

        After general case is should be:

            a.prev.next, a.next.prev, b.prev.next, b.next.prev = b, b, a, a
            a.prev, a.next, b.prev, b.next = b.prev, b.next, a.prev, a.next

        """
        with self.parent.lock:
            # store original links
            self_prev, self_next, other_prev, other_next = (
                self.prev, self.next, other.prev, other.next
            )

            if self_prev is not None:
                self_prev.next = other
                self.prev = other_prev

            if self_next is not None:
                self_next.prev = other
                self.next = other_next

            if other_next is not None:
                other_next.prev = self
                other.next = other_next

            if other_prev is not None:
                other_prev.next = self
                other.prev = self_prev

            first_set = False
            last_set = False

            if not last_set and self is self.parent.last:
                self.parent.last = other
                last_set = True

            if not first_set and self is self.parent.first:
                self.parent.first = other
                first_set = True

            if not last_set and other is self.parent.last:
                self.parent.last = self

            if not first_set and other is self.parent.first:
                self.parent.first = self


class Item:
    __slots__ = 'node', 'key', 'value'

    node: Node
    key: Hashable
    value: Any

    def __init__(self, node: Node, key: Hashable, value: Any):
        self.node = node
        self.key = key
        self.value = value


class DLList:
    __slots__ = 'first', 'last', 'lock', 'nodes'

    NODE_CLASS: Type[Node] = Node
    ITEM_CLASS: Type[Item] = Item

    first: Optional[NODE_CLASS]
    last: Optional[NODE_CLASS]

    def __init__(self):
        self.lock = RLock()
        self.first = None
        self.last = None
        self.nodes = set()

    def __len__(self):
        return len(self.nodes)

    def __contains__(self, item: NODE_CLASS):
        return item in self.nodes

    def __iter__(self):
        with self.lock:
            first = self.first
            while first is not None:
                yield first
                first = first.next

    def _create_node(self, *args, **kwargs):
        node = self.NODE_CLASS(self, *args, **kwargs)
        self.nodes.add(node)
        return node

    def remove(self, node: NODE_CLASS):
        if node not in self.nodes:
            raise ValueError(f"Node {node!r} is not part of {self!r}")

        with self.lock:
            self.nodes.remove(node)
            if node.prev is not None:
                node.prev.next = node.next
            if node.next is not None:
                node.next.prev = node.prev

            if self.first is node:
                self.first = node.next

            if self.last is node:
                self.last = node.prev

    def create_left(self) -> NODE_CLASS:
        with self.lock:
            if self.first is None:
                self.first = self._create_node()
                self.last = self.first
                return self.first

            node = self._create_node(next=self.first)
            self.first.prev = node
            self.first = node
            return node

    def create_right(self) -> NODE_CLASS:
        with self.lock:
            if self.first is None:
                self.last = self._create_node()
                self.first = self.last
                return self.first

            node = self._create_node(prev=self.last)
            self.last.next = node
            self.last = node
            return node
