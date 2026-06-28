from gcounter import GCounter


def test_basic_increment():
    c = GCounter("node_a")
    c.increment()
    c.increment()
    assert c.total() == 2, f"Expected 2, got {c.total()}"
    print("✓ basic increment")


def test_merge_two_nodes():
    a = GCounter("node_a")
    b = GCounter("node_b")

    for _ in range(30): a.increment()
    for _ in range(25): b.increment()

    # Gossip: both share snapshots
    a.merge(b.snapshot())
    b.merge(a.snapshot())

    assert a.total() == 55, f"Expected 55, got {a.total()}"
    assert b.total() == 55, f"Expected 55, got {b.total()}"
    print("✓ merge two nodes converges to correct total")


def test_idempotent_merge():
    """Merging the same snapshot twice should not change the total."""
    a = GCounter("node_a")
    b = GCounter("node_b")

    for _ in range(10): a.increment()
    for _ in range(10): b.increment()

    snap = b.snapshot()
    a.merge(snap)
    a.merge(snap)   # second merge — should be a no-op
    a.merge(snap)   # third merge — should be a no-op

    assert a.total() == 20
    print("✓ merge is idempotent")


def test_no_double_counting():
    """
    If node_a sends its snapshot to node_b and node_b sends back
    a merged snapshot that includes node_a's counts,
    node_a should not double-count its own slot.
    """
    a = GCounter("node_a")
    b = GCounter("node_b")

    for _ in range(5): a.increment()
    b.merge(a.snapshot())       # b now knows about a's 5
    a.merge(b.snapshot())       # a merges back, should still be 5, not 10

    assert a.total() == 5, f"Expected 5, got {a.total()}"
    print("✓ no double counting on round-trip merge")


def test_reset():
    a = GCounter("node_a")
    for _ in range(50): a.increment()
    assert a.total() == 50
    a.reset()
    assert a.total() == 0
    print("✓ reset clears counts")


def test_four_nodes():
    nodes = [GCounter(f"node_{c}") for c in "abcd"]

    # Each node processes some requests
    for i, node in enumerate(nodes):
        for _ in range((i + 1) * 10):
            node.increment()
    # Expected: 10 + 20 + 30 + 40 = 100

    # Fully gossip — every node shares with every other
    for a in nodes:
        for b in nodes:
            if a is not b:
                a.merge(b.snapshot())

    for node in nodes:
        assert node.total() == 100, f"{node.node_id}: expected 100, got {node.total()}"
    print("✓ four-node full gossip converges correctly")


if __name__ == "__main__":
    test_basic_increment()
    test_merge_two_nodes()
    test_idempotent_merge()
    test_no_double_counting()
    test_reset()
    test_four_nodes()
    print("\nAll tests passed. G-Counter is correct.")