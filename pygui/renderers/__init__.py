from abc import ABCMeta, abstractmethod


class Renderer(metaclass=ABCMeta):
    @abstractmethod
    def create_element(self, type: str) -> object:
        pass

    @abstractmethod
    def insert(self, el, parent):
        pass

    @abstractmethod
    def remove(self, el, parent):
        pass

    @abstractmethod
    def set_attribute(self, el, attr: str, value):
        pass

    @abstractmethod
    def clear_attribute(self, el, attr: str, value):
        pass

    @abstractmethod
    def add_event_listener(self, el, event_type, value):
        pass

    @abstractmethod
    def remove_event_listener(self, el, event_type, value):
        pass


from .dict_renderer import DictRenderer
from .pygfx_renderer import PygfxRenderer
