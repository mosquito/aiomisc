from aiomisc.cache.lfu import LFUCachePolicy


def test_simple():
    test_data = [(chr(i), i) for i in range(97, 127)]

    lfu = LFUCachePolicy(max_size=10)

    for key, value in test_data[:10]:
        lfu.set(key, value)

        lfu.get(key)

        assert key in lfu

    assert len(lfu) == 10

    lfu.set("foo", "bar")

    assert len(lfu) == 10

    lfu.remove("foo")

    for key, value in test_data[:10]:
        lfu.remove(key)
        assert key not in lfu

    assert len(lfu) == 0
    assert len(lfu.cache) == 0

    node = lfu.usages
    while node is not None:
        assert len(node.items) == 0
        node = node.next
