from itertools import zip_longest
import logging
from queue import SimpleQueue
import time
from typing import Any, Callable, Dict, Iterable, List, Optional
from weakref import ref

from observ import reactive, scheduler, to_raw
from observ.watcher import Watcher

from .compare import equivalent_functions
from .renderers import Renderer
from .types import (
    EffectTag,
    EventLoopType,
    Fiber,
    OpType,
    VNode,
)


logger = logging.getLogger(__name__)

# Node types for which no DOM elements are made
VIRTUAL_NODE_TYPES = {"template", "slot"}


class NotifyChangeWatcher(Watcher):
    """
    Custom watcher that simply calls callback function without evaluating
    the new value of the watched expression.
    This makes it possible to just signal to Collagraph that a dependency
    has changed and then Collagraph can decide when to actually evaluate
    the new value.
    """

    def update(self):
        """On update, simply run the callback."""
        self.callback()


def watch(fn, cb, lazy=False, deep=False, **kwargs):
    """Create custom watcher for the given expression: fn.

    Defaults lazy to False, so that value is evaluated immediately. And deep
    defaults to True for convenience."""
    return NotifyChangeWatcher(fn, lazy=lazy, deep=deep, callback=cb)


def create_element(type, props=None, *children) -> VNode:
    """Create an element description, based on type, props and (optionally) children"""
    key = props.get("key", None) if props is not None else None
    children = [
        child if not isinstance(child, str) else create_text_element(child)
        for child in children
    ]
    if len(children) == 1:
        # If children is 1 dictionary, then that is the slots definition
        if isinstance(children[0], dict):
            children = children[0]
        # If children is 1 callable item, then it becomes the default slot
        elif callable(children[0]):
            children = {"default": children[0]}
    return VNode(type, reactive(props or {}), children or tuple(), key)


def create_text_element(text):
    return VNode("TEXT_ELEMENT", {"content": text}, [])


def render_slot(name, props, slots):
    if name in slots:
        result = slots[name](props)
        if isinstance(result, VNode):
            return [result]
        return result
    return ()


class Collagraph:
    def __init__(
        self,
        renderer,
        *,
        event_loop_type: EventLoopType = None,
    ):
        if not isinstance(renderer, Renderer):
            raise TypeError(f"Expected a Renderer but got a {type(renderer)}")
        self.renderer = renderer
        if not event_loop_type:
            event_loop_type = (
                renderer.preferred_event_loop_type() or EventLoopType.DEFAULT
            )
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
        self._dirty = False

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
            if self.event_loop_type is EventLoopType.QT:
                from PySide6 import QtCore

                self._qt_timer = QtCore.QTimer()
                self._qt_timer.setSingleShot(True)
                self._qt_timer.setInterval(0)

                self._qt_first_run = True

                def start(deadline):
                    if not self._qt_first_run:
                        self._qt_timer.timeout.disconnect()
                    else:
                        self._qt_first_run = False

                    weak_self = ref(self)
                    self._qt_timer.timeout.connect(
                        lambda: weak_self() and weak_self().work_loop(deadline=deadline)
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
            self._dirty = False
            self.commit_root()
            # A state change happened during updating of the DOM
            if self._dirty:
                self.prepare_next_iteration_of_work()

        if self._next_unit_of_work:
            self.request_idle_work()
        else:
            if self._render_callback:
                self._render_callback()

    def perform_unit_of_work(self, fiber: Fiber) -> Optional[Fiber]:
        is_function_or_class_component = callable(fiber.type)
        if is_function_or_class_component:
            is_class_component = isinstance(fiber.type, type)
            if is_class_component:
                self.update_class_component(fiber)
            else:
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

    def update_class_component(self, fiber: Fiber):
        component = fiber.component or fiber.alternate and fiber.alternate.component
        if not component:
            component = fiber.type(fiber.props)

        # Attach the component instance to the fiber
        fiber.component = component

        component._slots = fiber.children if isinstance(fiber.children, dict) else {}

        if fiber.alternate:
            fiber.alternate.component = None
            fiber.watcher = fiber.alternate.watcher
            fiber.alternate.watcher = None

        if fiber.watcher:
            # Re-evaluate the watcher to get the new value
            fiber.watcher.evaluate()
        else:
            fiber.watcher = watch(
                component.render,
                lambda: self.state_updated(fiber),
            )

        self.reconcile_children(fiber, [fiber.watcher.value])

    def update_function_component(self, fiber: Fiber):
        if fiber.alternate:
            fiber.alternate.watcher = None

        def render():
            if isinstance(fiber.children, dict):
                return [fiber.type(fiber.props, fiber.children)]
            return [fiber.type(fiber.props)]

        fiber.watcher = watch(
            render,
            lambda: self.state_updated(fiber),
        )

        self.reconcile_children(fiber, fiber.watcher.value)

    def update_host_component(self, fiber: Fiber):
        # Add dom node, but not for template/slot tags (which are virtual tags)
        if not fiber.dom and fiber.type not in VIRTUAL_NODE_TYPES:
            fiber.dom = self.create_dom(fiber)

        if fiber.alternate:
            fiber.alternate.watcher = None

        fiber.watcher = watch(
            lambda: fiber.props.keys(),
            lambda: self.state_updated(fiber),
        )

        # Create new fibers
        self.reconcile_children(fiber, fiber.children)

    def create_dom(self, fiber: Fiber) -> Any:
        dom = (
            self.renderer.create_text_element()
            if fiber.type == "TEXT_ELEMENT"
            else self.renderer.create_element(fiber.type)
        )
        self.update_dom_or_component(fiber, dom, prev_props={}, next_props=fiber.props)
        return dom

    def prepare_next_iteration_of_work(self):
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

    def state_updated(self, fiber: Fiber):
        self._dirty = True

        if not self._wip_root:
            self.prepare_next_iteration_of_work()

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
        for element, old_fiber in zip_longest(elements, ordered_old_fibers + removals):
            new_fiber = None
            same_type = old_fiber and element and element.type == old_fiber.type

            if same_type:
                # Configure a fiber for updating a DOM element
                new_fiber = old_fiber.alternate or Fiber()
                new_fiber.type = element.type
                new_fiber.props = element.props
                new_fiber.props_snapshot = to_raw(element.props)
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
                new_fiber.props_snapshot = to_raw(element.props)
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

        # Use a queue to walk through the whole tree of fibers in order to
        # call component hooks (e.g: mounted, updated). The walk starts with
        # the root down to the leaves.
        # Here we use a tuple consisting of a fiber and boolean that indicates
        # whether we are traversing down to the leaves, or going back up to
        # a parent node. Only at the end of a collection of siblings we move
        # back up at which point we know for certain that all children for
        # the parent node have been processed, hence we can call the component
        # hooks on the way up.
        component_hooks = SimpleQueue()
        component_hooks.put((self._wip_root, True))

        # parent_component = None
        while not component_hooks.empty():
            # `down` is whether the tree is walked down toward the leaves
            # or up, back towards the root. On the way back, all the children
            # for the current fiber have been processed
            fiber, down = component_hooks.get()
            if not fiber:
                continue

            # Process children first
            if down and fiber.child:
                component_hooks.put((fiber.child, True))
                continue

            if fiber.mounted:
                if fiber.component:
                    fiber.component.element = fiber.child.dom
                    fiber.component.mounted()
                fiber.mounted = False
                fiber.updated = False
            elif fiber.updated:
                if fiber.component:
                    fiber.component.updated()
                fiber.updated = False

            if fiber.sibling:
                component_hooks.put((fiber.sibling, True))
            else:
                # The last of the siblings signals the
                # parent that we're walking back
                component_hooks.put((fiber.parent, False))

        self._current_root = self._wip_root
        self._wip_root = None

    def commit_deletion(self, fiber: Fiber, dom_parent: Any):
        """
        Remove an item from the dom. If the given fiber does not reference
        a dom element, then it will try its child (recursively) until it finds
        a fiber with a dom element that can be removed.
        Clears the child and dom attributes of the fiber.
        """
        if fiber.component:
            if not fiber.unmounted:
                fiber.component.before_unmount()
                fiber.unmounted = True

        def traverse_before_unmount(fiber):
            if fiber is None:
                return
            if fiber.component:
                if not fiber.unmounted:
                    fiber.component.before_unmount()
                    fiber.unmounted = True
            traverse_before_unmount(fiber.child)
            traverse_before_unmount(fiber.sibling)

        traverse_before_unmount(fiber.child)

        if fiber.dom is not None:
            self.renderer.remove(fiber.dom, dom_parent)
            fiber.dom = None
        else:
            self.commit_deletion(fiber.child, dom_parent)

        fiber.child = None
        fiber.sibling = None

    def commit_work(self, fiber: Fiber):
        if not fiber:
            return

        dom_parent_fiber = fiber.parent
        while dom_parent_fiber.dom is None:
            dom_parent_fiber = dom_parent_fiber.parent
        dom_parent = dom_parent_fiber.dom

        if fiber.effect_tag == EffectTag.PLACEMENT:
            if fiber.component:
                self.update_dom_or_component(
                    fiber, None, prev_props={}, next_props=fiber.props
                )
                fiber.mounted = True
            if fiber.dom is not None:
                self.renderer.insert(fiber.dom, dom_parent, anchor=fiber.anchor)
        elif fiber.effect_tag == EffectTag.UPDATE:
            if fiber.dom is not None:
                if fiber.move:
                    self.renderer.remove(fiber.dom, dom_parent)
                    self.renderer.insert(
                        fiber.dom,
                        dom_parent,
                        anchor=fiber.anchor,
                    )
            self.update_dom_or_component(
                fiber,
                fiber.dom,
                prev_props=fiber.alternate.props_snapshot,
                next_props=fiber.props_snapshot,
            )
        elif fiber.effect_tag == EffectTag.DELETION:
            self.commit_deletion(fiber, dom_parent)

        self._work.put(fiber.child)
        self._work.put(fiber.sibling)

    def update_dom_or_component(
        self, fiber: Fiber, dom: Any, prev_props: Dict, next_props: Dict
    ):
        if not dom and not fiber.component:
            return

        if fiber.type == "TEXT_ELEMENT":
            if (new_content := next_props["content"]) != prev_props.get("content"):
                self.renderer.set_element_text(dom, new_content)
                return

        events_to_remove = {}
        attrs_to_remove = {}
        attrs_to_update = {}
        events_to_add = {}
        equivalent_event_handlers = set()

        for key, val in prev_props.items():
            if is_event(key):
                if key in next_props and is_equivalent_event_handler(
                    val, next_props, key
                ):
                    equivalent_event_handlers.add(key)
                    continue

                event_type = key_to_event(key)
                events_to_remove[event_type] = val
            elif dom:  # Don't track prop changes for non-dom fibers
                # Is key gone?
                if key not in next_props:
                    attrs_to_remove[key] = prev_props[key]

        for key, val in next_props.items():
            if is_event(key):
                if key in equivalent_event_handlers:
                    continue

                event_type = key_to_event(key)
                events_to_add[event_type] = next_props[key]
            elif dom:  # Don't track prop changes for non-dom fibers
                # Is key new or changed?
                if is_new(val, prev_props, key):
                    attrs_to_update[key] = val

        if dom:
            for event_type, val in events_to_remove.items():
                self.renderer.remove_event_listener(dom, event_type, val)

            for key, val in attrs_to_remove.items():
                self.renderer.remove_attribute(dom, key, val)

            for key, val in attrs_to_update.items():
                self.renderer.set_attribute(dom, key, val)

            for event_type, val in events_to_add.items():
                self.renderer.add_event_listener(dom, event_type, val)

            # Climb up the tree to find first component to mark as updated
            if events_to_remove or events_to_add or attrs_to_remove or attrs_to_update:
                parent = fiber.parent
                component = None
                while parent:
                    component = parent.component
                    if component:
                        # Mark the fiber as updated
                        parent.updated = True
                        break
                    parent = parent.parent

        if fiber.component:
            for event_type, val in events_to_remove.items():
                fiber.component.remove_event_handler(event_type, val)

            for event_type, val in events_to_add.items():
                fiber.component.add_event_handler(event_type, val)


def is_event(key):
    return key.startswith("on_")


def key_to_event(key):
    # Events start with `on_`
    return key[3:].lower()


def is_new(val, other, key):
    return val != other.get(key)


def is_equivalent_event_handler(val, other, key):
    alt = other.get(key)
    return equivalent_functions(val, alt)


def indexOf(items: Iterable, match: Callable, *args):
    """Returns the index of the first item for which the `match` function returns
    True."""
    for idx, item in enumerate(items):
        if match(item, *args):
            return idx


def first(items: Iterable, match: Callable, *args):
    """Returns the first item for which the `match` function returns True."""
    idx = indexOf(items, match, *args)
    return items[idx] if idx is not None else None


def compare(a: Iterable, b: Iterable, match: Callable):
    """Returns a list of `matches` between a and b and `removals` which contain
    items that are in b but not in a.

    The list of matches has the same length as a and contains 'None' values at
    positions for which no match was found in b.
    """
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
    """Apply a single operation 'op' on a list 'it'."""
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
    for old in current:
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
