from abc import ABCMeta, abstractmethod

from observ import reactive, readonly


class Component(metaclass=ABCMeta):
    """Abstract base class for components"""

    def __init__(self, props=None):
        self._props = readonly(props)
        self._state = reactive({})
        self._mounted = False

    @property
    def state(self):
        """Readonly view on local component state."""
        return readonly(self._state)

    @property
    def props(self):
        """Readonly view on incoming component props."""
        return self._props

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self._state[name] = value

    def __getattribute__(self, name):
        if name.startswith("_") or name in ["state", "props"]:
            return super().__getattribute__(name)
        if name in self._state:
            return self._state[name]
        if name in self._props:
            return self._props[name]
        return super().__getattribute__(name)

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
