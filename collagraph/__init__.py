from functools import partial
from importlib.metadata import version
from itertools import zip_longest
import logging
from queue import SimpleQueue
import time
from typing import Any, Callable, Dict, Iterable, List, Optional

from observ import reactive, scheduler, watch

from .renderers import DictRenderer, Renderer
from .types import EffectTag, EventLoopType, Fiber, OpType, VNode


__all__ = ["create_element", "Collagraph", "EventLoopType"]
__version__ = version("collagraph")


logger = logging.getLogger(__name__)


def create_element(type, props=None, *children) -> VNode:
    """Create an element description, based on type, props and (optionally) children"""
    key = props.pop("key") if props and "key" in props else None
    return VNode(type, reactive(props or {}), children or tuple(), key)


class Collagraph:
    def __init__(
        self,
        renderer: Renderer = None,
        *,
        event_loop_type: EventLoopType = EventLoopType.DEFAULT,
    ):
        if renderer is None:
            renderer = DictRenderer()
        assert isinstance(renderer, Renderer)
        self.renderer = renderer
        self.event_loop_type = event_loop_type
        if self.event_loop_type is EventLoopType.QT:
            scheduler.register_qt()  # pragma: no cover
        elif self.event_loop_type is EventLoopType.DEFAULT:
            import asyncio

            def request_flush():
                loop = asyncio.get_event_loop_policy().get_event_loop()
                loop.call_soon(scheduler.flush)

            scheduler.register_request_flush(request_flush)
        else:
            scheduler.register_request_flush(scheduler.flush)

        # The current fiber tree that is committed to the DOM
        self._current_root: Fiber = None
        # The WIP root that holds the WIP fiber tree
        self._wip_root: Fiber = None
        self._next_unit_of_work: Fiber = None
        self._deletions: List[Fiber] = None
        self._render_callback: Callable = None
        self._request = None
        self._qt_timer = None
        self._work = SimpleQueue()

    def render(self, element: VNode, container, callback=None):
        self._wip_root = Fiber(
            dom=container,
            props={},
            children=(element,),
            alternate=self._current_root,
        )

        self._deletions = []
        self._next_unit_of_work = self._wip_root
        self._render_callback = callback

        self.request_idle_work()

    def request_idle_work(self, deadline: int = None):
        """
        Schedules work to be done when all other Qt events have been handled.

        Args:
            deadline: targetted deadline for until when work can be done. If
                no deadline is given, then it will be set to 16ms from now.
        """
        logger.info("Request work")

        # current in ns
        if not deadline:
            deadline = time.perf_counter_ns() + 16 * 1000000

        if self.event_loop_type is EventLoopType.SYNC:
            self.work_loop(deadline=None)
            return

        if not self._request:
            if self.event_loop_type is EventLoopType.DEFAULT:
                import asyncio

                def start(deadline):
                    loop = asyncio.get_event_loop_policy().get_event_loop()
                    loop.call_soon(self.work_loop, deadline)

                self._request = start
            if self.event_loop_type is EventLoopType.QT:  # pragma: no cover
                from PySide6 import QtCore

                self._qt_timer = QtCore.QTimer()
                self._qt_timer.setSingleShot(True)
                self._qt_timer.setInterval(0)

                self._qt_first_run = True

                def start(deadline):
                    if not self._qt_first_run:
                        self._qt_timer.timeout.disconnect()
                        self._qt_first_run = False
                    self._qt_timer.timeout.connect(
                        lambda: self.work_loop(deadline=deadline)
                    )
                    self._qt_timer.start()

                self._request = start

        self._request(deadline)

    def work_loop(self, deadline: int):
        """
        Performs work until right before the deadline or when the work runs out.
        Will at least perform one unit of work (if `_next_unit_of_work` is not None).
        NOTE: when sync is True, the deadline is not taken into account and all
        work will be done in sync until there is no more work.
        """
        should_yield = False
        while self._next_unit_of_work and not should_yield:
            self._next_unit_of_work = self.perform_unit_of_work(self._next_unit_of_work)
            # yield if time is up
            now = time.perf_counter_ns()
            should_yield = (
                self.event_loop_type is not EventLoopType.SYNC
                and (deadline - now) < 1 * 1000000
            )

        if not self._next_unit_of_work and self._wip_root:
            # All the preparations to build the new WIP root have been performed,
            # so it's time to walk through the new WIP root fiber tree and update
            # the actual DOM
            self.commit_root()

        if self._next_unit_of_work:
            self.request_idle_work()
        else:
            if self._render_callback:
                self._render_callback()

    def perform_unit_of_work(self, fiber: Fiber) -> Optional[Fiber]:
        is_function_component = callable(fiber.type)
        if is_function_component:
            self.update_function_component(fiber)
        else:
            self.update_host_component(fiber)

        # Return next unit of work
        if child := fiber.child:
            return child

        next_fiber = fiber
        while next_fiber:
            if sibling := next_fiber.sibling:
                return sibling
            next_fiber = next_fiber.parent

    def update_function_component(self, fiber: Fiber):
        children = [fiber.type(fiber.props)]
        self.reconcile_children(fiber, children)

    def update_host_component(self, fiber: Fiber):
        # Add dom node
        if not fiber.dom:
            fiber.dom = self.create_dom(fiber)

        # Create new fibers
        self.reconcile_children(fiber, fiber.children)

    def create_dom(self, fiber: Fiber) -> Any:
        dom = self.renderer.create_element(fiber.type)
        self.update_dom(dom, prev_props={}, next_props=fiber.props)
        return dom

    def state_updated(self, fiber: Fiber):
        logger.info(f"state update: {fiber.type}")
        # Clear the watcher that triggered the update
        fiber.watcher = None

        # Request an update to start building/update the wip fiber tree
        self._wip_root = (
            self._current_root and self._current_root.alternate
        ) or Fiber()
        self._wip_root.dom = self._current_root.dom
        self._wip_root.props = self._current_root.props
        self._wip_root.children = self._current_root.children
        self._wip_root.alternate = self._current_root
        self._next_unit_of_work = self._wip_root
        self._deletions = []
        self.request_idle_work()

    def reconcile_children(self, wip_fiber: Fiber, elements: List[VNode]):
        # The old fiber, which holds the state as it was rendered to DOM
        old_fiber = wip_fiber.alternate and wip_fiber.alternate.child

        # Create list of old_fibers, from the sibling of the old_fiber
        old_fibers = []
        if old_fiber:
            old_fibers = [old_fiber]
            sibling = old_fiber.sibling
            while sibling:
                old_fibers.append(sibling)
                sibling = sibling.sibling

        # Create watcher for the wip_fiber if not already there
        if wip_fiber.props:
            if wip_fiber.dom and not wip_fiber.watcher:
                wip_fiber.watcher = watch(
                    lambda: wip_fiber.props,
                    lambda: self.state_updated(wip_fiber),
                    deep=True,
                    sync=self.event_loop_type is EventLoopType.SYNC,
                )

        # Clear the watcher from the old fiber
        if old_fiber and old_fiber.props:
            old_fiber.watcher = None

        def matcher(x, y):
            return x.key == y.key

        ordered_old_fibers, removals = compare(elements, old_fibers, match=matcher)

        operations = {}
        if len(elements) > 1:
            new_keys = [el.key for el in elements if el and el.key]
            old_keys = [fib.key for fib in old_fibers if fib and fib.key]

            ops = create_ops(old_keys, new_keys)

            for op in ops:
                if op["op"] is not OpType.DEL:
                    if "anchor" in op:

                        def match(el, key):
                            return el.key == key

                        anchor = first(old_fibers, match, op["anchor"])
                        operations[op["value"]] = anchor.dom

        # In here, all the 'new' elements are compared to the old/current fiber/state
        prev_sibling = None
        for idx, (element, old_fiber) in enumerate(
            zip_longest(elements, ordered_old_fibers + removals)
        ):
            # Clear the watcher from the old fiber
            if old_fiber and old_fiber.props:
                old_fiber.watcher = None

            new_fiber = None
            same_type = old_fiber and element and element.type == old_fiber.type

            if same_type:
                # Configure a fiber for updating a DOM element
                new_fiber = old_fiber.alternate or Fiber()
                new_fiber.type = element.type
                new_fiber.props = element.props
                new_fiber.props_snapshot = element.props.copy()
                new_fiber.children = element.children
                new_fiber.key = element.key
                new_fiber.dom = old_fiber.dom
                new_fiber.parent = wip_fiber
                new_fiber.alternate = old_fiber
                new_fiber.child = None
                new_fiber.sibling = None
                new_fiber.effect_tag = EffectTag.UPDATE
                new_fiber.watcher = None
                new_fiber.move = new_fiber.key in operations
                new_fiber.anchor = operations.get(new_fiber.key)
            if element and not same_type:
                # Configure a fiber for creating a new DOM element
                new_fiber = (old_fiber and old_fiber.alternate) or Fiber()
                new_fiber.type = element.type
                new_fiber.props = element.props
                new_fiber.props_snapshot = element.props.copy()
                new_fiber.children = element.children
                new_fiber.key = element.key
                new_fiber.dom = None
                new_fiber.parent = wip_fiber
                new_fiber.alternate = None
                new_fiber.child = None
                new_fiber.sibling = None
                new_fiber.effect_tag = EffectTag.PLACEMENT
                new_fiber.watcher = None
                new_fiber.move = False
                new_fiber.anchor = operations.get(new_fiber.key)
                # NOTE: If there is an old_fiber, then it will be
                # marked for deletion in the next if statement
            if old_fiber and not same_type:
                # Mark the old fiber for deletion so that DOM element will be removed
                old_fiber.effect_tag = EffectTag.DELETION
                self._deletions.append(old_fiber)

            # And we add it to the fiber tree setting it either as a child or as a
            # sibling, depending on whether it’s the first child or not.
            if not wip_fiber.child:
                wip_fiber.child = new_fiber
            if prev_sibling:
                # NOTE: `new_fiber` can still be None here!
                prev_sibling.sibling = new_fiber

            prev_sibling = new_fiber

    def commit_root(self):
        """
        Start updating the UI from the root of the fiber tree
        NOTE: `_wip_root` represents the container in which is rendered, so hence
        the work starts with the `child` attribute of the `_wip_root` (once all fibers
        that have been marked for deletion have been removed.
        """
        for deletion in self._deletions:
            self._work.put(deletion)
        self._deletions = []
        self._work.put(self._wip_root.child)

        while not self._work.empty():
            work = self._work.get()
            self.commit_work(work)

        self._current_root = self._wip_root
        self._wip_root = None

    def commit_deletion(self, fiber: Fiber, dom_parent: Any):
        """
        Remove an item from the dom. If the given fiber does not reference
        a dom element, then it will try its child (recursively) until it finds
        a fiber with a dom element that can be removed.
        Clears the child and dom attributes of the fiber.
        """
        if dom := fiber.dom:
            self.renderer.remove(dom, dom_parent)
            fiber.dom = None
        else:
            self.commit_deletion(fiber.child, dom_parent)
        fiber.child = None
        fiber.sibling = None

    def commit_work(self, fiber: Fiber):
        if not fiber:
            return

        dom_parent_fiber = fiber.parent
        while not dom_parent_fiber.dom:
            dom_parent_fiber = dom_parent_fiber.parent
        dom_parent = dom_parent_fiber.dom

        if fiber.effect_tag == EffectTag.PLACEMENT and fiber.dom:
            self.renderer.insert(fiber.dom, dom_parent, anchor=fiber.anchor)
        elif fiber.effect_tag == EffectTag.UPDATE and fiber.dom:
            if fiber.move:
                self.renderer.remove(fiber.dom, dom_parent)
                self.renderer.insert(
                    fiber.dom,
                    dom_parent,
                    anchor=fiber.anchor,
                )
            self.update_dom(
                fiber.dom,
                prev_props=fiber.alternate.props_snapshot,
                next_props=fiber.props_snapshot,
            )
        elif fiber.effect_tag == EffectTag.DELETION:
            self.commit_deletion(fiber, dom_parent)

        self._work.put(fiber.child)
        self._work.put(fiber.sibling)

    def update_dom(self, dom: Any, prev_props: Dict, next_props: Dict):
        def is_event(key):
            return key.startswith("on")

        def is_property(key):
            return not is_event(key)

        def is_new(val, other, key):
            return val != other.get(key)

        def is_equivalent_event_handler(val, other, key):
            alt = other.get(key)
            return equivalent_functions(val, alt)

        # Remove old event listeners
        for name, val in prev_props.items():
            if not is_event(name):
                continue
            if name in next_props and is_equivalent_event_handler(
                val, next_props, name
            ):
                continue

            event_type = name.lower()[2:]
            self.renderer.remove_event_listener(dom, event_type, val)

        # Remove old properties
        for key in prev_props:
            # Is key an actual property?
            if not is_property(key):
                continue
            # Is key gone?
            if key in next_props:
                continue

            self.renderer.remove_attribute(dom, key, prev_props[key])

        # Set new or changed properties
        for key, val in next_props.items():
            if not is_property(key):
                continue
            # Is key new or changed?
            if not is_new(val, prev_props, key):
                continue

            self.renderer.set_attribute(dom, key, val)

        # Add new event listeners
        for name in next_props:
            if not is_event(name):
                continue
            if is_equivalent_event_handler(prev_props.get(name), next_props, name):
                continue

            event_type = name.lower()[2:]
            self.renderer.add_event_listener(dom, event_type, next_props[name])


def first(items: Iterable, match: Callable, *args):
    idx = indexOf(items, match, *args)
    return items[idx] if idx is not None else None


def indexOf(items: Iterable, match: Callable, *args):
    for idx, item in enumerate(items):
        if match(item, *args):
            return idx


def compare(a: Iterable, b: Iterable, match: Callable):
    b = b.copy()
    matches = []
    for item in a:
        match_idx = indexOf(b, match, item)
        if match_idx is not None:
            matches.append(b.pop(match_idx))
        else:
            # Add an 'insertion' point
            matches.append(None)

    removals = b.copy()
    return matches, removals


def apply_op(op: Dict, it: Iterable):
    if op["op"] is OpType.MOVE:
        idx = it.index(op["value"])
        val = it.pop(idx)
        new_idx = it.index(op["anchor"])
        it.insert(new_idx, val)
    elif op["op"] is OpType.DEL:
        it.remove(op["value"])
    elif op["op"] is OpType.ADD:
        idx = it.index(op["anchor"]) if "anchor" in op else len(it)
        it.insert(idx, op["value"])


def create_operation(type, value, anchor: Any = None):
    """
    Returns:
        Operation as a simple dict with the following keys:
        - op: type of operation: DEL, ADD or MOVE
        - value: value of the item
        - anchor (required when type is MOVE): the element before
            which this element should be inserted
    """
    result = {"op": type, "value": value}
    if anchor is not None:
        result["anchor"] = anchor
    assert type is not OpType.MOVE or "anchor" in result
    return result


def create_ops(current, future):
    """
    Args:
        current: list of keys as they are currently rendered in the dom
        future: list of keys as they should be rendered in the dom

    Returns:
        list of operations to apply (in order) to convert `current` to
        `future`. See `create_operation` for more details.
    """
    ops = []
    # Bookkeep the state of the array for intermediate states
    wip = current.copy()

    # First figure out all the deletions that need to take place
    for idx, old in enumerate(current):
        if old not in future:
            ops.append(create_operation(OpType.DEL, value=old))
            apply_op(ops[-1], wip)

    # Then figure out all the movements and deletions
    for idx, (old, new) in enumerate(zip_longest(current, future)):
        if new is not None and new not in current:
            anchor = wip[idx] if idx < len(wip) else None
            ops.append(create_operation(OpType.ADD, value=new, anchor=anchor))
            apply_op(ops[-1], wip)

        if old is not None and new is None:
            # The deletion ops have already been recorded
            continue

        idx_before = wip.index(new)

        if idx_before != idx:
            # If an item is moved back, then the offset will be increased
            anchor = wip[idx] if idx < len(wip) else None
            ops.append(create_operation(OpType.MOVE, value=new, anchor=anchor))
            apply_op(ops[-1], wip)

    return ops


def equivalent_functions(a: Callable, b: Callable):
    """Returns whether function a is equivalent to function b.

    ``functools.partial`` functions are also supported (but only when both
    argument a and b are partial).
    """
    if not hasattr(a, "__code__") or not hasattr(b, "__code__"):
        if isinstance(a, partial) and isinstance(b, partial):
            return (
                a.args == b.args
                and a.keywords == b.keywords
                and equivalent_functions(a.func, b.func)
            )

        return a == b

    return equivalent_code(a.__code__, b.__code__) and equivalent_closure_values(a, b)


def equivalent_code(a, b):
    """Returns True if a and b are equivalent code.

    In order to determine this, a number of properties are compared that
    should be equal between similar functions.
    It checks all co_* props of __code__ (as seen in Python 3.9), except for:
      * co_varnames
      * co_firstlineno
      * co_lnotab
      * co_name
    because those vars can differ without having any impact on the equivalency
    of the functions themselves.
    """
    for attr in [
        "co_argcount",
        "co_cellvars",
        "co_code",
        "co_consts",
        "co_filename",
        "co_flags",
        "co_freevars",
        "co_kwonlyargcount",
        "co_names",
        "co_nlocals",
        "co_posonlyargcount",
        "co_stacksize",
    ]:
        attr_a = getattr(a, attr, None)
        attr_b = getattr(b, attr, None)
        if attr_a != attr_b:
            return False

    return True


def equivalent_closure_values(a, b):
    """Compare the cell contents of the __closure__ attribute for the given
    functions. This method assumes that the code for a and be is already
    equivalent."""
    if (closure_a := getattr(a, "__closure__", None)) and (
        closure_b := getattr(b, "__closure__", None)
    ):
        values_a = [cell.cell_contents for cell in closure_a]
        values_b = [cell.cell_contents for cell in closure_b]
        return values_a == values_b

    return True
