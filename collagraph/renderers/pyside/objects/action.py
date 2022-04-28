import logging

from ..utils import attr_name_to_method_name, call_method


logger = logging.getLogger(__name__)


def set_attribute(self, attr, value):
    method_name = attr_name_to_method_name(attr, setter=True)
    method = getattr(self, method_name, None)
    if not method:
        logger.debug(f"Setting custom attr: {attr}")
        setattr(self, attr, value)
        return

    call_method(method, value)
