from importlib.metadata import version

from .collagraph import Collagraph, create_element  # noqa: F401
from .components import Component  # noqa: F401
from .renderers import *  # noqa: F401, F403
from .types import EventLoopType, VNode  # noqa: F401
from .cgx import importer  # noqa: F401, I100

__version__ = version("collagraph")

h = create_element
