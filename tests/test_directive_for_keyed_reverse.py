"""Test v-for directive with keys - reversing a keyed list."""

from weakref import ref

import pytest
from observ import reactive

from collagraph import Collagraph, EventLoopType
from tests.conftest import CustomElement, CustomElementRenderer, TrackingRenderer


def test_reverse_list_reordering(parse_source):
    """
    Test that reversing a keyed list [A, B, C] -> [C, B, A] correctly
    reorders the DOM elements, not just their attributes.

    This test verifies that:
    1. Element instances are preserved (moved, not recreated)
    2. Elements appear in the correct DOM order after reversal
    """
    Items, _ = parse_source(
        """
        <items>
          <item v-for="item in items" :key="item" :content="item" />
        </items>

        <script>
        import collagraph as cg

        class Items(cg.Component):
            pass
        </script>
        """
    )

    renderer = CustomElementRenderer()
    container = CustomElement(type="root")
    state = reactive({"items": ["A", "B", "C"]})

    gui = Collagraph(
        renderer=renderer,
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(Items, container, state=state)

    items_container = container.children[0]

    # Verify initial order
    assert len(items_container.children) == 3
    assert items_container.children[0].content == "A"
    assert items_container.children[1].content == "B"
    assert items_container.children[2].content == "C"

    # Store references to the original elements
    element_a = items_container.children[0]
    element_b = items_container.children[1]
    element_c = items_container.children[2]

    # Keep weak references to verify they're reused
    ref_a = ref(element_a)
    ref_b = ref(element_b)
    ref_c = ref(element_c)

    # Reverse the list
    state["items"] = ["C", "B", "A"]

    # CRITICAL CHECKS: Verify DOM order is actually reversed
    assert len(items_container.children) == 3, "Should still have 3 children"

    # Check position 0: should now have element C
    assert items_container.children[0].content == "C", (
        "Position 0 should have content 'C' after reversal"
    )
    assert items_container.children[0] is element_c, (
        "Position 0 should be the original element C (moved, not recreated)"
    )

    # Check position 1: should still have element B
    assert items_container.children[1].content == "B", (
        "Position 1 should have content 'B' after reversal"
    )
    assert items_container.children[1] is element_b, (
        "Position 1 should be the original element B"
    )

    # Check position 2: should now have element A
    assert items_container.children[2].content == "A", (
        "Position 2 should have content 'A' after reversal"
    )
    assert items_container.children[2] is element_a, (
        "Position 2 should be the original element A (moved, not recreated)"
    )

    # Verify all elements are still alive (not garbage collected)
    assert ref_a() is not None
    assert ref_b() is not None
    assert ref_c() is not None


def test_partial_reordering(parse_source):
    """
    Test a more complex reordering scenario: [A, B, C] -> [C, A, B]

    This is the specific scenario mentioned in the review where:
    - C moves from position 2 to position 0
    - A moves from position 0 to position 1
    - B moves from position 1 to position 2
    """
    Items, _ = parse_source(
        """
        <items>
          <item v-for="item in items" :key="item" :content="item" />
        </items>

        <script>
        import collagraph as cg

        class Items(cg.Component):
            pass
        </script>
        """
    )

    renderer = CustomElementRenderer()
    container = CustomElement(type="root")
    state = reactive({"items": ["A", "B", "C"]})

    gui = Collagraph(
        renderer=renderer,
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(Items, container, state=state)

    items_container = container.children[0]

    # Store references to original elements
    element_a = items_container.children[0]
    element_b = items_container.children[1]
    element_c = items_container.children[2]

    # Reorder: [A, B, C] -> [C, A, B]
    state["items"] = ["C", "A", "B"]

    # Verify correct DOM order
    assert len(items_container.children) == 3

    # Position 0: should have C
    assert items_container.children[0].content == "C"
    assert items_container.children[0] is element_c

    # Position 1: should have A
    assert items_container.children[1].content == "A"
    assert items_container.children[1] is element_a

    # Position 2: should have B
    assert items_container.children[2].content == "B"
    assert items_container.children[2] is element_b


@pytest.mark.parametrize(
    "before,after,expected_creates,expected_removes,expected_inserts,description",
    [
        # Simple reorderings (optimized with LIS)
        (
            ["A", "B", "C"],
            ["C", "B", "A"],
            0,
            2,
            2,
            "full reversal",
        ),
        (
            ["A", "B", "C"],
            ["C", "A", "B"],
            0,
            1,
            1,
            "rotate right (LIS: A,B stay)",
        ),
        (
            ["A", "B", "C"],
            ["B", "C", "A"],
            0,
            1,
            1,
            "rotate left (LIS: B,C stay)",
        ),
        (
            ["A", "B", "C"],
            ["B", "A", "C"],
            0,
            1,
            1,
            "swap first two (LIS: A or B stays)",
        ),
        (
            ["A", "B", "C"],
            ["A", "C", "B"],
            0,
            1,
            1,
            "swap last two (LIS: A or C stays)",
        ),
        (
            ["A", "B", "C"],
            ["A", "B", "C"],
            0,
            0,
            0,
            "no change",
        ),
        # Simple additions
        (
            ["A", "B", "C"],
            ["A", "B", "C", "D"],
            1,
            0,
            1,
            "add at end",
        ),
        (
            ["A", "B", "C"],
            ["D", "A", "B", "C"],
            1,
            0,
            1,
            "add at start",
        ),
        (
            ["A", "B", "C"],
            ["A", "D", "B", "C"],
            1,
            0,
            1,
            "add in middle",
        ),
        # Simple removals
        (
            ["A", "B", "C"],
            ["B", "C"],
            0,
            1,
            0,
            "remove first",
        ),
        (
            ["A", "B", "C"],
            ["A", "C"],
            0,
            1,
            0,
            "remove middle",
        ),
        (
            ["A", "B", "C"],
            ["A", "B"],
            0,
            1,
            0,
            "remove last",
        ),
        # Mixed operations
        (
            ["A", "B", "C"],
            ["C", "B", "A", "D"],
            1,
            2,
            3,
            "reverse and add at end",
        ),
        (
            ["A", "B", "C", "D"],
            ["D", "B"],
            0,
            3,
            1,
            "remove two and reorder (LIS: B stays)",
        ),
        (
            ["A", "B", "C"],
            ["D", "C", "B"],
            1,
            2,
            2,
            "add D and reverse (LIS: C,B stay)",
        ),
        (
            ["A", "B", "C"],
            ["C", "D", "A"],
            1,
            2,
            2,
            "remove B, add D, reorder (LIS: A stays)",
        ),
        (
            ["A", "B", "C", "D"],
            ["E", "D", "F", "B"],
            2,
            3,
            3,
            "complex: remove A,C add E,F, reorder",
        ),
    ],
)
def test_list_operations_efficiency(
    parse_source,
    before,
    after,
    expected_creates,
    expected_removes,
    expected_inserts,
    description,
):
    """
    Test that list reconciliation performs the expected number of
    DOM operations for various reordering scenarios.

    Tracks creates, removes, and inserts separately.
    Inserts include both new elements and moved existing elements.
    """
    Items, _ = parse_source(
        """
        <items>
          <item v-for="item in items" :key="item" :content="item" />
        </items>

        <script>
        import collagraph as cg

        class Items(cg.Component):
            pass
        </script>
        """
    )

    renderer = TrackingRenderer()
    container = CustomElement(type="root")
    state = reactive({"items": before})

    gui = Collagraph(
        renderer=renderer,
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(Items, container, state=state)

    items_container = container.children[0]

    # Reset counters after initial render
    renderer.reset_counters()

    # Apply the transformation
    state["items"] = after

    # Verify final DOM order matches expected order
    assert len(items_container.children) == len(after), description
    for i, expected_item in enumerate(after):
        assert items_container.children[i].content == expected_item, (
            f"{description}: position {i} should have {expected_item}"
        )

    # Verify expected number of creates
    assert renderer.create_count == expected_creates, (
        f"{description}: expected {expected_creates} creates, "
        f"got {renderer.create_count}"
    )

    # Verify expected number of inserts
    assert renderer.insert_count == expected_inserts, (
        f"{description}: expected {expected_inserts} inserts, "
        f"got {renderer.insert_count}"
    )

    # Verify expected number of removes
    assert renderer.remove_count == expected_removes, (
        f"{description}: expected {expected_removes} removes, "
        f"got {renderer.remove_count}"
    )
