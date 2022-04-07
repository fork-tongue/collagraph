from abc import ABCMeta, abstractmethod

from observ import reactive, readonly


class Component(metaclass=ABCMeta):
    """Abstract base class for components"""

    def __init__(self, props=None):
        self.props = readonly(props)
        self.state = reactive({})
        self._mounted = False

    def before_mount(self):
        """Called right before the component is to be mounted."""
        pass

    def mounted(self):
        """Called after the component has been mounted.

        A component is considered mounted after:

        * All of its child components have been mounted.
        * Its own DOM tree has been created and inserted into the parent container.
        """
        pass

    def before_update(self):
        """Called right before the component is about to update its DOM tree."""
        pass

    def updated(self):
        """Called after the component has updated its DOM tree.

        A parent component's updated method is called after that of its child
        components.
        """
        pass

    def before_unmount(self):
        """Called right before a component instance is to be unmounted."""
        pass

    def unmounted(self):
        """Called after the component has been unmounted.

        A component is considered unmounted after all of its child components have
        been unmounted.
        """
        pass

    @abstractmethod
    def render():
        return NotImplementedError
