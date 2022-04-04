from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Union

from observ import reactive


class EventLoopType(Enum):
    DEFAULT = "asyncio"
    QT = "Qt"
    SYNC = "sync"


class EffectTag(Enum):
    """Possible effect tags for Fibers"""

    UPDATE = "UPDATE"
    PLACEMENT = "PLACEMENT"
    DELETION = "DELETION"


class OpType(Enum):
    MOVE = "MOVE"
    DEL = "DEL"
    ADD = "ADD"


@dataclass
class VNode:
    """Virtual Node that serves as a basic description of the node to be rendered."""

    type: Union[str, Callable]
    props: Dict
    children: List["VNode"]
    key: str = None


@dataclass
class Fiber:
    """Fibers hold information/work about a VNode and a 'dom' element."""

    alternate: "Fiber" = None
    child: "Fiber" = None
    children: List["VNode"] = None
    dom: Any = None
    effect_tag: EffectTag = None
    key: str = None
    anchor: Any = None  # Dom element
    move: bool = False
    parent: "Fiber" = None
    props: Dict = None
    sibling: "Fiber" = None
    snapshot: Dict = None
    type: Union[str, Callable] = None
    watcher: Any = None
    component: Any = None
    component_watcher: Any = None


class Component(metaclass=ABCMeta):
    """Abstract base class for components"""

    def __init__(self, props=None):
        self._incoming_props = reactive(props)
        self._local_props = reactive({})
        self._mounted = False

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self._local_props[name] = value

    def __getattribute__(self, name):
        if name.startswith("_"):
            return super().__getattribute__(name)
        if name in self._local_props:
            return self._local_props[name]
        return super().__getattribute__(name)

    def on_mounted(self):
        pass

    def before_mount(self):
        """Called right before the component is to be mounted.

        When this method is called, the component has finished setting up its reactive
        state, but no DOM nodes have been created yet. It is about to execute its DOM
        render effect for the first time.
        """
        pass

    def mounted(self):
        """Called after the component has been mounted.

        A component is considered mounted after:

        * All of its child components have been mounted.
        * Its own DOM tree has been created and inserted into the parent container.

        This method is typically used for performing side effects that need access to
        the component's rendered DOM.
        """
        pass

    def before_update(self):
        """Called right before the component is about to update its DOM tree due to a
        reactive state change.

        This metho can be used to access the DOM state before Vue updates the DOM. It is
        also safe to modify component state inside this method.
        FIXME: is it really safe though?
        """
        pass

    def updated(self):
        """Called after the component has updated its DOM
        tree due to a reactive state change.

        A parent component's updated method is called after that of its child
        components.

        This method is called after any DOM update of the component, which can be caused
        by different state changes. If you need to access the updated DOM after a
        specific state change, use [a timer] instead.
        """
        pass

    def before_unmount(self):
        """Called right before a component instance is to be unmounted.

        When this hook is called, the component instance is still fully functional.
        """
        pass

    def unmounted(self):
        """Called after the component has been unmounted.

        A component is considered unmounted after:

        * All of its child components have been unmounted.
        * All of its associated reactive effects (render effect and computed / watchers
          created during setup()) have been stopped.

        Use this method to clean up manually created side effects such as timers, DOM
        event listeners or server connections.
        """
        pass

    @abstractmethod
    def render():
        return NotImplementedError
