from importlib.metadata import version

from .collagraph import Collagraph  # noqa: F401
from .component import Component  # noqa: F401
from .constants import EventLoopType  # noqa: F401
from .dsl import (  # noqa: F401
    dynamic,
    each,
    fill,
    h,
    or_when,
    otherwise,
    slot,
    static,
    when,
)
from .renderers import *  # noqa: F403
from .sfc import importer  # noqa: F401

__version__ = version("collagraph")
