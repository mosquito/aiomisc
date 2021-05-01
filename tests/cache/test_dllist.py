from typing import List

import pytest

from aiomisc.cache.dllist import DLList, Node


def test_simple(subtests):
    dllist = DLList()
    node_class = DLList.NODE_CLASS

    with subtests.test("blank object"):
        assert len(dllist) == 0
        assert dllist.first is None
        assert dllist.last is None

    with subtests.test("one node"):
        node1 = dllist.create_right()
        assert isinstance(node1, node_class)
        assert len(dllist) == 1
        assert dllist.first is node1
        assert dllist.last is node1
        assert node1.next is None
        assert node1.prev is None

    with subtests.test("two nodes"):
        node2 = dllist.create_right()
        assert isinstance(node2, node_class)
        assert dllist.first is node1
        assert dllist.last is node2
        assert node1.next is node2
        assert dllist.first.next is node2

    with subtests.test("three nodes"):
        node3 = dllist.create_left()
        assert isinstance(node3, node_class)
        assert dllist.first is node3
        assert dllist.first.next is node1

        assert dllist.last is node2
        assert node3.next is node1
        assert node1.next is node2
        assert node2.prev is node1
        assert node1.prev is node3
        assert dllist.last is node2

    with subtests.test("remove node"):
        first = dllist.first
        while first:
            with subtests.test("remove first"):
                dllist.remove(dllist.first)
                assert dllist.first is not first
                assert first not in dllist
                first = dllist.first


@pytest.fixture
def nodes() -> list:
    return []


@pytest.fixture
def dllist(nodes):
    dllist = DLList()
    for i in range(10):
        nodes.append(dllist.create_right())

    return dllist


ITERATIONS = 10


@pytest.mark.parametrize("node_idx", list(range(ITERATIONS)))
def test_remove(node_idx: int, nodes: List[Node], dllist: DLList):
    node = nodes.pop(node_idx)
    assert node in dllist
    dllist.remove(node)
    assert node not in dllist

    for idx, item in enumerate(dllist):
        assert nodes[idx] is item


def test_remove_first(subtests, nodes: List[Node], dllist: DLList):
    first = dllist.first
    counter = 0
    while first is not None:
        with subtests.test(f"iteration={counter}"):
            counter += 1
            dllist.remove(dllist.first)
            assert dllist.first is not first
            assert first not in dllist
            first = dllist.first

            assert len(dllist) == (ITERATIONS - counter)
            for idx, item in enumerate(dllist):
                assert nodes[counter:][idx] is item


def test_remove_last(subtests, nodes: List[Node], dllist: DLList):
    last = dllist.last
    counter = 0
    while last is not None:
        with subtests.test(f"iteration={counter}"):
            counter += 1
            dllist.remove(dllist.last)
            assert dllist.last is not last
            assert last not in dllist
            last = dllist.last

            assert len(dllist) == (ITERATIONS - counter)

            for idx, item in enumerate(dllist):
                assert nodes[idx] is item


def test_node_repr_recursion(nodes: List[Node]):
    for node in nodes:
        assert str(id(node)) in repr(node)
        assert str(id(node.next)) in repr(node)
        assert str(id(node.prev)) in repr(node)


def test_node_swap(dllist):
    a, b = dllist.first, dllist.last
    a_next = a.next
    a_prev = a.prev
    b_next = b.next
    b_prev = b.prev

    assert dllist.first is a
    assert dllist.last is b

    dllist.first.swap(dllist.last)

    assert dllist.first is not a
    assert dllist.last is not b

    assert b_next is not b.next
    assert a_next is not a.next
    assert a_prev is not a.prev
    assert b_prev is not b.prev

