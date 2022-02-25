from dataclasses import dataclass
import enum
from importlib.metadata import version
import logging
import queue
import time
from typing import Any, Callable, Dict, List, Optional, Union

from observ import reactive, scheduler, watch
from PySide6 import QtCore


from .renderers import PygfxRenderer, Renderer


__all__ = ["create_element", "PyGui"]
__version__ = version("pygui")


logger = logging.getLogger(__name__)


class EffectTag(enum.Enum):
    UPDATE = "UPDATE"
    PLACEMENT = "PLACEMENT"
    DELETION = "DELETION"


@dataclass
class VNode:
    type: Union[str, Callable]
    props: Dict
    children: List["VNode"]
    key: Optional[str] = None


@dataclass
class Fiber:
    dom: Optional[Any]
    props: Dict
    children: List["VNode"]
    alternate: Optional["Fiber"]
    type: Optional[Union[str, Callable]] = None
    child: Optional["Fiber"] = None
    sibling: Optional["Fiber"] = None
    parent: Optional["Fiber"] = None
    effect_tag: Optional[EffectTag] = None
    watcher: Optional[Any] = None


def create_element(type, props=None, *children) -> VNode:
    """Create an element description, based on type, props and (optionally) children"""
    key = props.pop("key") if props and "key" in props else None
    return VNode(type, reactive(props or {}), children or tuple(), key)


class PyGui:
    def __init__(self, renderer: Renderer = None, *args, sync=False, **kwargs):
        if renderer is None:
            renderer = PygfxRenderer()
        assert isinstance(renderer, Renderer)
        self.renderer = renderer
        self.sync = sync
        if not sync:
            scheduler.register_qt()

        self._next_unit_of_work: Fiber = None
        self._current_root: Fiber = None
        self._wip_root: Fiber = None
        self._deletions: List[Fiber] = None
        self._wip_fiber: Fiber = None
        self._render_callback: Callable = None
        self._timer = None
        self._work = queue.SimpleQueue()

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
            deadline = time.perf_counter_ns() + 1000000 * 16

        if self.sync:
            self.work_loop(deadline=deadline)
            return

        if not self._timer:
            self._timer = QtCore.QTimer()
            self._timer.setSingleShot(True)
            self._timer.setInterval(0)
        else:
            self._timer.timeout.disconnect()

        self._timer.timeout.connect(lambda: self.work_loop(deadline=deadline))
        self._timer.start()

    def render(self, element: VNode, container, callback=None):
        self._wip_root = Fiber(
            dom=container,
            props={},
            children=[element],
            alternate=self._current_root,
        )

        self._deletions = []
        self._next_unit_of_work = self._wip_root
        self._render_callback = callback

        self.request_idle_work()

    def work_loop(self, deadline: int):
        should_yield = False
        while self._next_unit_of_work and not should_yield:
            self._next_unit_of_work = self.perform_unit_of_work(self._next_unit_of_work)
            # yield if time is up
            now = time.perf_counter_ns()
            should_yield = (deadline - now) < 1 * 1000000

        if not self._next_unit_of_work and self._wip_root:
            self.commit_root()

        if self._next_unit_of_work:
            self.request_idle_work()
        else:
            logger.info("Work done")
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

    def update_host_component(self, fiber: Fiber):
        # Add dom node
        if not fiber.dom:
            fiber.dom = self.create_dom(fiber)

        # Create new fibers
        self.reconcile_children(fiber, fiber.children)

    def update_function_component(self, fiber: Fiber):
        children = [fiber.type(fiber.props)]
        self.reconcile_children(fiber, children)

    def state_updated(self, fiber: Fiber):
        logger.info(f"state update: {fiber.dom}")
        # Clear the watcher that triggered the update
        fiber.watcher = None
        # TODO: maybe check that the wip_root is None?
        # TODO: just queue the work instead?
        # assert wip_root is None
        self._wip_root = Fiber(
            dom=self._current_root.dom,
            props=self._current_root.props,
            children=self._current_root.children,
            alternate=self._current_root,
        )
        self._next_unit_of_work = self._wip_root
        self._deletions = []
        self.request_idle_work()

    def create_dom(self, fiber: Fiber) -> Any:
        dom = self.renderer.create_element(fiber.type)
        self.update_dom(dom, prev_props={}, next_props=fiber.props)
        return dom

    def reconcile_children(self, wip_fiber: Fiber, elements: List[VNode]):
        index = 0
        old_fiber = wip_fiber.alternate and wip_fiber.alternate.child
        prev_sibling = None

        if wip_fiber.props is not None:
            if wip_fiber.dom and not wip_fiber.watcher:
                wip_fiber.watcher = watch(
                    lambda: wip_fiber.props,
                    lambda: self.state_updated(wip_fiber),
                    deep=True,
                    sync=self.sync,
                )
        # Clear the watcher from the old fiber
        if old_fiber and old_fiber.props is not None:
            old_fiber.watcher = None

        while index < len(elements) or old_fiber is not None:
            element = elements[index] if index < len(elements) else None
            new_fiber = None

            same_type = old_fiber and element and element.type == old_fiber.type

            if same_type:
                # update the node
                new_fiber = Fiber(
                    type=old_fiber.type,
                    props=element.props,
                    children=element.children,
                    dom=old_fiber.dom,
                    parent=wip_fiber,
                    alternate=old_fiber,
                    effect_tag=EffectTag.UPDATE,
                )
            if element and not same_type:
                # add this node
                new_fiber = Fiber(
                    type=element.type,
                    props=element.props,
                    children=element.children,
                    dom=None,
                    parent=wip_fiber,
                    alternate=None,
                    effect_tag=EffectTag.PLACEMENT,
                )
            if old_fiber and not same_type:
                # delete the old_fiber's node
                old_fiber.effect_tag = EffectTag.DELETION
                self._deletions.append(old_fiber)
            # TODO: we could use 'key's here for better reconciliation

            if old_fiber:
                old_fiber = old_fiber.sibling

            if index == 0:
                wip_fiber.child = new_fiber
            elif element:
                prev_sibling.sibling = new_fiber

            prev_sibling = new_fiber
            index += 1

    def commit_root(self):
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
        if dom := fiber.dom:
            self.renderer.remove(dom, dom_parent)
        else:
            self.commit_deletion(fiber.child, dom_parent)

    def commit_work(self, fiber: Fiber):
        if not fiber:
            return

        dom_parent_fiber = fiber.parent
        while not dom_parent_fiber.dom:
            dom_parent_fiber = dom_parent_fiber.parent
        dom_parent = dom_parent_fiber.dom

        if fiber.effect_tag == EffectTag.PLACEMENT and fiber.dom:
            self.renderer.insert(fiber.dom, dom_parent)
        elif fiber.effect_tag == EffectTag.UPDATE and fiber.dom:
            self.update_dom(
                fiber.dom, prev_props=fiber.alternate.props, next_props=fiber.props
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

        # Remove old event listeners
        for name, val in prev_props.items():
            if not is_event(name):
                continue
            if name not in next_props or not is_new(val, next_props, name):
                continue

            event_type = name.lower()[2:]
            dom.remove_event_handler(event_type, val)

        # Remove old properties
        for key, val in prev_props.items():
            # Is key an actual property?
            if not is_property(key):
                continue
            # Is key gone?
            if key in next_props:
                continue

            self.renderer.clear_attribute(dom, key, val)

        # Set new or changed properties
        for key, val in next_props.items():
            if not is_property(key):
                continue
            # Is key new or changed?
            if not is_new(val, prev_props, key):
                continue

            self.renderer.set_attribute(dom, key, val)

        # Add new event listeners
        for name, val in next_props.items():
            if not is_event(name):
                continue
            if not is_new(prev_props.get(name), next_props, name):
                continue

            event_type = name.lower()[2:]
            dom.add_event_handler(event_type, val)
