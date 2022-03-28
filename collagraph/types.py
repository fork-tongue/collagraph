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

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            # TODO: maybe keypath support for name for deep structures?
            self._local_props[name] = value

    def __getattribute__(self, name):
        if name.startswith("_"):
            return super().__getattribute__(name)
        if name in self._local_props:
            return self._local_props[name]
        return super().__getattribute__(name)

    def on_mounted(self):
        pass

    def on_unmounted(self):
        pass

    @abstractmethod
    def render():
        return NotImplementedError
