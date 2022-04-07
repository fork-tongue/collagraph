from abc import ABCMeta, abstractmethod

from observ import reactive, readonly


class Component(metaclass=ABCMeta):
    """Abstract base class for components"""

    def __init__(self, props=None):
        self.props = readonly(props or {})
        self.state = reactive({})

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

        There are no specific guarantees about the order of when this method is called.
        A parent component's method might be called before that of its child components.
        """
        pass

    @abstractmethod
    def render():  # pragma: no cover
        pass
