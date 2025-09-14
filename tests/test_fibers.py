import pytest
from observ import reactive

from collagraph import Collagraph, EventLoopType
from collagraph import create_element as h
from collagraph.renderers import DictRenderer


def test_fiber_reuse_update():
    renderer = DictRenderer()
    gui = Collagraph(renderer=renderer, event_loop_type=EventLoopType.SYNC)
    container = {"type": "root"}
    state = reactive({"counter": 0})
    element = h("counter", state)

    gui.render(element, container)

    assert container["children"][0]["attrs"]["counter"] == 0

    assert gui._wip_root is None
    assert gui._current_root
    assert gui._current_root.child
    assert gui._current_root.child.type == "counter"
    assert gui._current_root.child.child is None
    assert gui._current_root.child.sibling is None
    assert gui._current_root.child.parent == gui._current_root
    assert gui._current_root.alternate is None
    assert gui._current_root.child.alternate is None

    first_root_fiber = gui._current_root
    first_counter_fiber = gui._current_root.child

    # Update state, which triggers a re-render
    state["counter"] += 1

    assert container["children"][0]["attrs"]["counter"] == 1

    assert gui._wip_root is None
    assert gui._current_root
    assert gui._current_root.child
    assert gui._current_root.child.type == "counter"
    assert gui._current_root.child.child is None
    assert gui._current_root.child.sibling is None
    assert gui._current_root.child.parent == gui._current_root
    assert gui._current_root.alternate is first_root_fiber
    assert gui._current_root.child.alternate is first_counter_fiber

    alt_root_fiber = gui._current_root
    alt_counter_fiber = gui._current_root.child
    assert alt_root_fiber is not first_root_fiber
    assert alt_counter_fiber is not first_counter_fiber

    # Trigger another re-render, now the first root should be re-used
    state["counter"] += 1

    assert container["children"][0]["attrs"]["counter"] == 2

    assert gui._wip_root is None
    assert gui._current_root is first_root_fiber
    assert gui._current_root.child is first_counter_fiber
    assert gui._current_root.child.type == "counter"
    assert gui._current_root.child.child is None
    assert gui._current_root.child.sibling is None
    assert gui._current_root.child.parent == first_root_fiber
    assert gui._current_root.alternate is alt_root_fiber
    assert gui._current_root.child.alternate is alt_counter_fiber


def walk_tree(fiber, callback):
    if not fiber:
        return

    callback(fiber)

    if fiber.child:
        walk_tree(fiber.child, callback)
        return

    while fiber:
        if fiber.sibling:
            walk_tree(fiber.sibling, callback)
            return
        fiber = fiber.parent


def test_fiber_element_deletion():
    def List(props):
        return h(
            "list",
            {},
            *[
                h("item", {"index": index + props["start_index"]})
                for index in range(props["count"])
            ],
        )

    renderer = DictRenderer()
    gui = Collagraph(renderer=renderer, event_loop_type=EventLoopType.SYNC)
    container = {"type": "root"}
    state = reactive({"count": 2, "start_index": 0})
    element = h(List, state)

    gui.render(element, container)

    list_element = container["children"][0]
    assert len(list_element["children"]) == 2
    assert list_element["children"][0]["attrs"]["index"] == 0

    first_root_fiber = gui._current_root
    first_list_fiber = gui._current_root.child

    # Trigger another update to build up the alternate tree as well
    state["start_index"] = 3

    assert len(list_element["children"]) == 2
    assert list_element["children"][0]["attrs"]["index"] == 3
    assert list_element["children"][1]["attrs"]["index"] == 4

    alt_root_fiber = gui._current_root
    alt_list_fiber = gui._current_root.child
    assert first_root_fiber is not alt_root_fiber
    assert first_list_fiber is not alt_list_fiber

    # First child of alt_list_fiber is the fiber that actually represents
    # the 'list' DOM element
    fiber_to_be_deleted = alt_list_fiber.child.child.sibling
    assert fiber_to_be_deleted.props["index"] == 4

    # Trigger a deletion
    state["count"] = 1

    assert len(list_element["children"]) == 1

    def assert_is_not_deleted_fiber(fiber):
        assert fiber is not fiber_to_be_deleted
        assert fiber.alternate is not fiber_to_be_deleted
        assert fiber.child is not fiber_to_be_deleted
        assert fiber.sibling is not fiber_to_be_deleted
        assert fiber.parent is not fiber_to_be_deleted

    # The current tree should not have any references anymore to the fiber
    # that is to be deleted. The alternate tree still does
    walk_tree(gui._current_root, assert_is_not_deleted_fiber)
    with pytest.raises(AssertionError):
        walk_tree(gui._current_root.alternate, assert_is_not_deleted_fiber)

    # Trigger another update
    state["start_index"] = 2

    # Now both the current and the alternate tree should not have any references
    # anymore to the object that is about to be deleted
    walk_tree(gui._current_root, assert_is_not_deleted_fiber)
    walk_tree(gui._current_root.alternate, assert_is_not_deleted_fiber)


def test_fiber_element_type_change():
    # check number of fibers stays the same
    def List(props):
        return h(
            "foo" if props["foo"] else "bar",
            {},
        )

    renderer = DictRenderer()
    gui = Collagraph(renderer=renderer, event_loop_type=EventLoopType.SYNC)
    container = {"type": "root"}
    state = reactive({"foo": True})
    element = h(List, state)
    gui.render(element, container)

    assert container["children"][0]["type"] == "foo"
    fiber_to_be_deleted = gui._current_root.child.child

    def assert_is_not_deleted_fiber(fiber):
        assert fiber is not fiber_to_be_deleted
        assert fiber.alternate is not fiber_to_be_deleted
        assert fiber.child is not fiber_to_be_deleted
        assert fiber.sibling is not fiber_to_be_deleted
        assert fiber.parent is not fiber_to_be_deleted

    state["foo"] = False

    assert container["children"][0]["type"] == "bar"
    walk_tree(gui._current_root, assert_is_not_deleted_fiber)
    with pytest.raises(AssertionError):
        walk_tree(gui._current_root.alternate, assert_is_not_deleted_fiber)

    state["foo"] = True

    assert container["children"][0]["type"] == "foo"
    walk_tree(gui._current_root, assert_is_not_deleted_fiber)
    walk_tree(gui._current_root.alternate, assert_is_not_deleted_fiber)
