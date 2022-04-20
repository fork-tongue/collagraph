from abc import ABCMeta, abstractmethod
from weakref import ref

from observ import reactive, readonly


class Component(metaclass=ABCMeta):
    """Abstract base class for components"""

    def __init__(self, props=None):
        self.props = readonly({} if props is None else props)
        self.state = reactive({})
        self._element = None

    @property
    def element(self):
        """The root DOM element of this component."""
        return self._element and self._element()

    @element.setter
    def element(self, value):
        """Setter that is used by the internals of Collagraph. Please don't use this."""
        try:
            self._element = ref(value)
        except TypeError:
            # It is not possible to create weak refs to dicts and lists
            # so instead wrap the element in a lambda.
            self._element = lambda: value

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

    def __del__(self):
        # Make sure to clean-up _element. Normally this shouldn't be needed as it is
        # a weak ref, but if a type of element was set for which no weak ref can be
        # made, we still need to do the clean-up.
        self._element = None
