from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Union


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
    children: Union[List["VNode"], Dict[str, Callable]]
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
    mounted: bool = False  # Flag for components whether it was mounted
    updated: bool = False  # Flag for components whether any DOM was updated
    unmounted: bool = False  # Flag for components whether it was unmounted
