from dataclasses import dataclass
import enum
import time
from typing import Callable, Dict, List, Optional, Union

import pygfx as gfx
from PySide6 import QtCore

from . import pygfx_renderer

__all__ = [
    "create_element",
    "render",
    "use_state",
]


class EffectTag(enum.Enum):
    UPDATE = "UPDATE"
    PLACEMENT = "PLACEMENT"
    DELETION = "DELETION"


next_unit_of_work = None
current_root = None
wip_root = None
deletions = None
wip_fiber = None
hook_index = None
qt_timer = None
render_callback = None


@dataclass
class VNode:
    type: Union[str, Callable]
    props: Dict
    children: List["VNode"]
    key: Optional[str] = None


def create_element(type, props=None, *children) -> VNode:
    """Create an element description, based on type, props and (optionally) children"""
    key = props.pop("key") if props and "key" in props else None
    return VNode(type, props or {}, children or tuple(), key)


def request_idle_work(deadline: int = None):
    """
    Schedules work to be done when all other Qt events have been handled.

    Args:
        deadline: targetted deadline for until when work can be done. If
            no deadline is given, then it will be set to 16ms from now.
    """
    global qt_timer
    if not qt_timer:
        qt_timer = QtCore.QTimer()
        qt_timer.setSingleShot(True)
        qt_timer.setInterval(0)
    else:
        qt_timer.timeout.disconnect()

    # current in ns
    if not deadline:
        deadline = time.perf_counter_ns() + 1000000 * 16

    qt_timer.timeout.connect(lambda: work_loop(deadline=deadline))
    qt_timer.start()


def render(element, container, callback=None):
    global current_root
    global wip_root
    global next_unit_of_work
    global deletions
    global render_callback

    wip_root = {
        "dom": container,
        "props": {},
        "children": [element],
        "alternate": current_root,
    }
    deletions = []
    next_unit_of_work = wip_root
    render_callback = callback

    request_idle_work()


def work_loop(deadline: int):
    global next_unit_of_work
    should_yield = False
    while next_unit_of_work and not should_yield:
        next_unit_of_work = perform_unit_of_work(next_unit_of_work)
        # yield if time is up
        now = time.perf_counter_ns()
        should_yield = (deadline - now) < 1 * 1000000

    if not next_unit_of_work and wip_root:
        commit_root()

    if next_unit_of_work:
        request_idle_work()
    else:
        if render_callback:
            render_callback()


def create_dom(fiber) -> gfx.WorldObject:
    dom = pygfx_renderer.create_element(fiber["type"])
    update_dom(dom, {}, fiber["props"])
    return dom


def perform_unit_of_work(fiber):
    is_function_component = "type" in fiber and callable(fiber["type"])
    if is_function_component:
        update_function_component(fiber)
    else:
        update_host_component(fiber)

    # return next unit of work
    if child := fiber.get("child"):
        return child

    next_fiber = fiber
    while next_fiber:
        if sibling := next_fiber.get("sibling"):
            return sibling
        next_fiber = next_fiber.get("parent")


def update_function_component(fiber):
    global wip_fiber
    global hook_index
    wip_fiber = fiber
    hook_index = 0
    wip_fiber["hooks"] = []

    children = [fiber["type"](fiber["props"])]
    reconcile_children(fiber, children)


def use_state(initial):
    global hook_index
    old_hook = (
        wip_fiber.get("alternate")
        and wip_fiber["alternate"].get("hooks")
        and wip_fiber["alternate"]["hooks"][hook_index]
    )
    hook = {
        "state": old_hook["state"] if old_hook else initial,
        "queue": [],
    }

    actions = old_hook["queue"] if old_hook else []
    for action in actions:
        hook["state"] = action(hook["state"])

    def set_state(action):
        global wip_root
        global next_unit_of_work
        global deletions
        hook["queue"].append(action)
        # TODO: maybe check that the wip_root is None?
        # assert wip_root is None
        wip_root = {
            "dom": current_root.get("dom"),
            "props": current_root.get("props"),
            "children": current_root["children"],
            "alternate": current_root,
        }
        next_unit_of_work = wip_root
        deletions = []
        request_idle_work()

    wip_fiber["hooks"].append(hook)
    hook_index += 1
    return hook["state"], set_state


def update_host_component(fiber):
    # add dom node
    if not fiber["dom"]:
        fiber["dom"] = create_dom(fiber)

    # create new fibers
    reconcile_children(fiber, fiber["children"])


def reconcile_children(wip_fiber, elements):
    index = 0
    old_fiber = wip_fiber.get("alternate") and wip_fiber.get("alternate").get("child")
    prev_sibling = None

    while index < len(elements) or old_fiber is not None:
        element = elements[index] if index < len(elements) else None
        new_fiber = None

        same_type = old_fiber and element and element.type == old_fiber["type"]

        if same_type:
            # update the node
            new_fiber = {
                "type": old_fiber["type"],
                "props": element.props,
                "children": element.children,
                "dom": old_fiber["dom"],
                "parent": wip_fiber,
                "alternate": old_fiber,
                "effect_tag": EffectTag.UPDATE,
            }
        if element and not same_type:
            # add this node
            new_fiber = {
                "type": element.type,
                "props": element.props,
                "children": element.children,
                "dom": None,
                "parent": wip_fiber,
                "alternate": None,
                "effect_tag": EffectTag.PLACEMENT,
            }
        if old_fiber and not same_type:
            # delete the old_fiber's node
            old_fiber["effect_tag"] = EffectTag.DELETION
            deletions.append(old_fiber)
        # TODO: we could use 'key's here for better reconciliation

        if old_fiber:
            old_fiber = old_fiber.get("sibling")

        if index == 0:
            wip_fiber["child"] = new_fiber
        elif element:
            prev_sibling["sibling"] = new_fiber

        prev_sibling = new_fiber
        index += 1


def commit_root():
    global wip_root
    global current_root
    global deletions
    for deletion in deletions:
        commit_work(deletion)
    commit_work(wip_root.get("child"))
    current_root = wip_root
    wip_root = None


def commit_deletion(fiber, dom_parent):
    if dom := fiber.get("dom"):
        dom_parent.remove(dom)
    else:
        commit_deletion(fiber["child"], dom_parent)


def commit_work(fiber):
    if not fiber:
        return

    dom_parent_fiber = fiber.get("parent")
    while not dom_parent_fiber.get("dom"):
        dom_parent_fiber = dom_parent_fiber.get("parent")
    # pygfx object here (hence 'dom')
    dom_parent = dom_parent_fiber["dom"]

    if fiber.get("effect_tag") == EffectTag.PLACEMENT and fiber.get("dom"):
        # Add a 'renderer' and call the renderer with insert(element, parent)
        dom_parent.add(fiber["dom"])
    elif fiber.get("effect_tag") == EffectTag.UPDATE and fiber.get("dom"):
        update_dom(fiber["dom"], fiber["alternate"]["props"], fiber["props"])
    elif fiber.get("effect_tag") == EffectTag.DELETION:
        commit_deletion(fiber, dom_parent)

    commit_work(fiber.get("child"))
    commit_work(fiber.get("sibling"))


def update_dom(dom, prev_props, next_props):
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

        event_type = name.lower()[2:]  # noqa: F841
        dom.remove_event_handler(event_type, val)

    # Remove old properties
    for key, val in prev_props.items():
        # is key an actual property?
        if not is_property(key):
            continue
        # is key gone?
        if key in next_props:
            continue

        # Supports resetting Vector3...
        pygfx_renderer.clear_attribute(dom, key, val)

    # Set new or changed properties
    for key, val in next_props.items():
        if not is_property(key):
            continue
        # is key new or changed?
        if not is_new(val, prev_props, key):
            continue

        # Only supports Vector3...
        pygfx_renderer.set_attribute(dom, key, val)

    # Add new event listeners
    for name, val in next_props.items():
        if not is_event(name):
            continue
        if not is_new(prev_props.get(name), next_props, name):
            continue

        event_type = name.lower()[2:]  # noqa: F841
        dom.add_event_handler(event_type, val)
