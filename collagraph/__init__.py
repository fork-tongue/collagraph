from importlib.metadata import version

from .collagraph import Collagraph, create_element, render_slot  # noqa: F401
from .component import Component  # noqa: F401
from .renderers import *  # noqa: F403
from .types import EventLoopType, VNode  # noqa: F401
from .cgx import importer  # noqa: F401

__version__ = version("collagraph")

h = create_element
s = render_slot
