from abc import abstractmethod
from collections import defaultdict

from observ import reactive, readonly

from collagraph import render_slot


class Component:
    """Abstract base class for components"""

    __slots__ = ["state", "props"]

    def __init__(self, props=None):
        self.props = readonly({} if props is None else props)
        self.state = reactive({})
        self._element = None
        self._slots = {}
        self._event_handlers = defaultdict(set)

    @property
    def element(self):
        """The root DOM element of this component."""
        return self._element

    @element.setter
    def element(self, value):
        """Setter that is used by the internals of Collagraph. Please don't use this."""
        self._element = value

    def render_slot(self, name, props=None):
        return render_slot(name, props, self._slots)

    # Provide shortcut to render_slot method
    s = render_slot

    def mounted(self):
        """Called after the component has been mounted.

        A component is considered mounted after:

        * All of its child components have been mounted.
        * Its own DOM tree has been created and inserted into the parent container.
        """
        pass

    def updated(self):
        """Called after the component has updated its DOM tree.

        A parent component's updated method is called after that of its child
        components.
        """
        pass

    def before_unmount(self):
        """Called right before a component instance is to be unmounted.

        Use this method to clean up manually created side effects such as timers, DOM
        event listeners or server connections.

        Note that there are no specific guarantees about the order of when this method
        is called. A parent component's method might be called before that of its child
        components.
        """
        pass

    @abstractmethod
    def render():  # pragma: no cover
        pass

    def emit(self, event, *args, **kwargs):
        """Call event handlers for the given event. Any args and kwargs will be passed
        on to the registered handlers."""
        for handler in self._event_handlers[event].copy():
            handler(*args, **kwargs)

    def add_event_handler(self, event, handler):
        """Adds an event handler for the given event."""
        self._event_handlers[event].add(handler)

    def remove_event_handler(self, event, handler):
        """Removes an event handler for the given event."""
        self._event_handlers[event].remove(handler)
