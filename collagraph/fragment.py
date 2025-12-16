from __future__ import annotations

from collections.abc import Callable
from typing import Any
from weakref import ref

from observ import computed, reactive, watch_effect
from observ.watcher import Watcher, watch  # type: ignore

from .component import Component
from .renderers import Renderer
from .weak import weak


class Fragment:
    """
    A fragment is something that describes an element as a kind of function.
    In the cgx template, elements are functions that describe what an element
    should be like based on certain input. Directives such as v-if and v-for serve
    as functions that govern a dynamic list of elements.
    """

    def __init__(
        self,
        renderer: Renderer,
        # tag = None for 'transient' Fragments, like a virtual root
        tag: str | Callable[[], Component] | None = None,
        parent: Fragment | None = None,
    ):
        super().__init__()

        # The tag for the fragment
        self.tag: str | Callable[[], Component] | None = tag
        # Reference to the renderer
        # TODO: don't pass the renderer to the fragments...
        self.renderer = renderer
        # List of child fragments
        self.children: list[Fragment] = []
        # Dom element (if any)
        self.element: Any | None = None
        # Target dom-element to render in
        self.target: Any | None = None
        # Name of slot to be rendered into
        self.slot_name: str | None = None

        # Weak ref to parent fragment
        self._parent: ref[Fragment] | None = ref(parent) if parent else None
        # Static attributes for the DOM element
        self._attributes: dict[str, str] = {}
        # Events for the DOM element
        self._events: dict[str, Callable] = {}
        # Registered binds
        self._binds: list[tuple] = []
        # Watchers associated with the DOM element
        # TODO: add extra dict prop just for attributes:
        # that saves on lookups like: 'bind:' in key
        self._watchers: dict[str, Watcher] = {}
        # Conditional expression for whether the DOM element should be rendered
        self._condition: Callable | None = None

        self._mounted = False

        # Make sure that the relationship between this
        # item and its parent is set correctly
        if parent:
            parent.register_child(self)

        # FIXME: should fragments also be able to be 'anchored'???

    def __repr__(self):
        return f"<{type(self).__name__}({self.tag}-[{id(self)}])>"

    def debug(self, indent: int = 0):
        print(f"{'  ' * indent}<{self.tag}>")  # noqa: T201
        for child in self.children:
            if child._mounted:
                child.debug(indent + 1)

    @property
    def parent(self) -> Fragment | None:
        return self._parent() if self._parent else None

    def _component_parent(self) -> Component | None:
        """
        Returns the component of the first parent ComponentFragment that
        has a component property. Or None, if not there.

        """
        # TODO: would be nice if we could cache the _component_parent in a clever way
        parent = self.parent
        while parent and (
            not isinstance(parent, ComponentFragment) or not parent.component
        ):
            parent = parent.parent

        if parent:
            return parent.component

    @parent.setter
    def parent(self, parent: Fragment | None):
        # TODO: should this also check that this item is
        # now in the list of the parent's children?
        self._parent = ref(parent) if parent else None

    def register_child(self, child: Fragment) -> None:
        self.children.append(child)

    def first(self) -> Any | None:
        """
        Returns the first DOM element (if any), from either itself, or its direct
        decendants, in case of virtual fragments. Should not be deeper since an
        anchor lives in the same depth in the tree.
        """
        if self.element:
            return self.element
        for child in self.children:
            if child.element:
                return child.element

    def anchor(self) -> Any | None:
        """
        Returns the fragment that serves as anchor for this fragment.
        Anchor is the first mounted item *after* the current item.
        """
        parent = self.parent
        assert parent is not None
        idx = parent.children.index(self)
        length = len(parent.children) - 1
        while 0 <= idx < length:
            idx += 1
            if element := parent.children[idx].first():
                return element

    def set_attribute(self, attr: str, value: Any):
        """
        Set a static attribute. Note that it is not directly applied to
        the element, that will happen in the `create` call.
        """
        self._attributes[attr] = value

    def set_bind(self, attr: str, expression: Callable):
        """
        Set a bind (dynamic attribute) to the value of the expression.
        This will wait to be applied when `create` is called.
        """
        self._binds.append((attr, expression, True))

    def set_bind_dict(self, name: str, expression: Callable[[], dict[str, Any]]):
        """
        Set dynamic attributes for all of the keys in the value of the expression.
        Since there might be more than one dict bound, the name is used to discern
        between them.

        The dict of the expression will be watched for the keys. For each new key,
        `set_bind` is called to create a dynamic attribute for the value of that
        key. When a key is removed, then the specific watcher is removed and some
        cleanup performed.

        This will wait to be applied when `create` is called.
        """
        self._binds.append((name, expression, False))

    def set_condition(self, expression: Callable[[], bool]):
        """
        Set a expression that determines whether this fragment
        should show up or not.
        Only during the 'mount' cycle will this condition be 'installed'
        and monitored for its effects.
        """
        self._condition = expression

    def set_event(self, event: str, handler: Callable[[], Any]):
        """
        Set a handler for an event.
        """
        self._events[event] = handler

    def _watch_bind(self, attr, expression):
        """
        Install a watcher for a bound attribute with the given expression
        """

        @weak(self)
        def update(self, new):
            self._set_attr(attr, new)

        self._watchers[f"bind:{attr}"] = watch(
            expression,
            update,
            immediate=True,
            deep=True,
        )

    def _watch_bind_dict(self, name, expression):
        @weak(self)
        def update(self, new: set[str], old: set[str] | None):
            if old is None:
                old = set()
            if additional_attrs := new - old:
                for attr in additional_attrs:
                    self._watch_bind(
                        attr,
                        lambda attr=attr: expression()[attr],
                    )

            if removed_attrs := old - new:
                for attr in removed_attrs:
                    if f"bind:{attr}" in self._watchers:
                        unwatch = self._watchers.pop(f"bind:{attr}")
                        unwatch()
                        # Perform cleanup
                        self._rem_attr(attr)

        self._watchers[f"bind_dict:{name}"] = watch(
            lambda: set(expression().keys()),
            update,
            immediate=True,
            deep=True,
        )

    def create(self):
        """
        Creates instance, depending on whether there is
        an expression
        """
        if self.tag == "template" or self.tag is None:
            return

        # Create the element
        self.element = self.renderer.create_element(self.tag)
        # Set all static attributes
        for attr, value in self._attributes.items():
            self.renderer.set_attribute(self.element, attr, value)

        # Add all event handlers
        # TODO: check what happens within v-for constructs?
        for event, handler in self._events.items():
            self.renderer.add_event_listener(self.element, event, handler)

        # Set all dynamic attributes
        for name, expression, singular in self._binds:
            if singular:
                self._watch_bind(name, expression)
            else:
                self._watch_bind_dict(name, expression)

        # IDEA/TODO: for v-for, don't create instances direct, but
        # instead, create child fragments first, then call
        # create on those instead. Might involve some reparenting
        # of the current child fragments???

    def mount(self, target: Any, anchor: Any | None = None):
        if self._mounted:
            return

        self.target = target
        self.create()

        if self.element:
            self.renderer.insert(self.element, parent=target, anchor=anchor)
        for child in self.children:
            child.mount(self.element or target)

        self._mounted = True

    def _set_attr(self, attr, value):
        if self.element:
            self.renderer.set_attribute(self.element, attr, value)
            if self._mounted:
                if component := self._component_parent():
                    component.updated()

    def _rem_attr(self, attr):
        if self.element:
            self.renderer.remove_attribute(self.element, attr, None)
            if self._mounted:
                if component := self._component_parent():
                    component.updated()

    def _remove(self):
        if self.element:
            self.renderer.remove(self.element, self.target)
            self.element = None

    def unmount(self, destroy=True):
        self._mounted = False

        for child in self.children:
            child.unmount(destroy=destroy)

        self._remove()

        if destroy:
            self.element = None
            self.target = None
            self._attributes = {}
            self._events = {}
            # Disable the fn and callback of the watcher to disable
            # any 'false' triggers
            for unwatch in self._watchers.values():
                unwatch()
            self._watchers = {}
            self._condition = None
            self.tag = None
        else:
            self.element = None
            # Disable the fn and callback of the watcher to disable
            # any 'false' triggers
            for unwatch in self._watchers.values():
                unwatch()
            self._watchers = {}

        # TODO: maybe control flow fragments needs another custom 'parenting'
        # solution where the control flow fragment keeps references to the
        # 'child' elements
        # if self.parent and not isinstance(self.parent, ControlFlowFragment):
        #     if self in self.parent.children:
        #         self.parent.children.remove(self)


class ControlFlowFragment(Fragment):
    def mount(self, target: Any, anchor: Any | None = None):
        if self._mounted:
            return
        self.target = target

        @weak(self)
        def update_fragment(self, new: Fragment | None, old: Fragment | None):
            if old:
                old.unmount(destroy=False)
            if new:
                anch = anchor
                if anch is None and self.parent:
                    anch = self.anchor()
                new.mount(self.target, anch)

        @weak(self)
        def active_child(self):
            for child in self.children:
                if child._condition is not None:
                    # if and else-if blocks
                    if child._condition():
                        return child
                else:
                    # else block
                    return child

        self._watchers["control_flow"] = watch(
            active_child,
            update_fragment,
            deep=True,
            immediate=True,
        )
        self._mounted = True


class ListFragment(Fragment):
    """
    1. Handle expression (for 'X' in 'Y') in multiple parts (by analyzing the
       AST):
        A. Create a watcher for collection 'Y'
        B. Callback will create (or update existing) Fragments
            - When unkeyed:
                idx = 0
                for 'X' in 'Y':
                    if idx < len(fragments):
                        fragment = fragments[idx]
                    else:
                        fragment = Fragment(...)
                    ...
                    idx += 1
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.create_fragment: Callable[[], Fragment] | None = None
        self.expression: Callable[[], list[Any]] | None = None
        self.is_keyed: bool = False
        self.key_extractor: Callable[[Any], Any] | None = None

    def set_create_fragment(
        self,
        create_fragment: Callable[[], Fragment],
        is_keyed: bool,
        key_extractor: Callable[[Any], Any] | None = None,
    ):
        self.create_fragment = create_fragment
        self.is_keyed = is_keyed
        self.key_extractor = key_extractor

    def set_expression(self, expression: Callable[[], list[Any]] | None):
        self.expression = expression

    def mount(self, target: Any, anchor: Any | None = None):
        if self._mounted:
            return

        self.target = target

        # First create a computed value that captures the expression
        # as a list. We use a computed value so that the list is
        # evaluated lazy and is only re-evaluated when needed.
        @computed(deep=False)
        @weak(self)
        def expression(self):
            value = self.expression()
            return value if hasattr(value, "__len__") else list(value)

        # Keep a list with all the rendered values
        self.values = []

        if self.is_keyed and self.key_extractor:
            # Key-based reconciliation
            # Track fragments by their keys
            self.key_to_fragment: dict[str, Fragment] = {}

            @weak(self)
            def update_children_keyed(self):
                items = expression()

                # Build new keys list
                new_keys = []
                new_key_to_item = {}
                for item in items:
                    # Extract key for this item
                    # Pass a function that returns the item directly
                    key = self.key_extractor(lambda i=item: i)
                    new_keys.append(key)
                    new_key_to_item[key] = item

                # Check for duplicate keys, raise when found
                if len(new_keys) != len(new_key_to_item):
                    duplicates = []
                    for key in new_key_to_item:
                        if new_keys.count(key) > 1:
                            duplicates.append(str(key))
                    raise RuntimeError(f"Duplicate keys found: {', '.join(duplicates)}")

                # Determine which keys are removed, added, or moved
                old_key_set = set(self.key_to_fragment)
                new_key_set = set(new_keys)

                # Keys that are no longer present - unmount them
                removed_keys = old_key_set - new_key_set
                for key in removed_keys:
                    fragment = self.key_to_fragment.pop(key)
                    # Remove from children list
                    self.children.remove(fragment)
                    fragment.unmount()

                # Build new children array in the correct order
                new_children = []
                for i, key in enumerate(new_keys):
                    item = new_key_to_item[key]

                    if key in self.key_to_fragment:
                        # Reuse existing fragment
                        fragment = self.key_to_fragment[key]
                        # Update the context with new item value
                        new_children.append(fragment)
                    else:
                        # Create new fragment for new key
                        context = reactive({"context": item})
                        fragment = self.create_fragment(lambda c=context: c["context"])
                        fragment.parent = self
                        self.key_to_fragment[key] = fragment
                        new_children.append(fragment)

                # Now we need to reorder/mount the DOM elements to match new_children
                # We process from the end to the beginning to avoid interference
                # from previous moves
                for i in range(len(new_children) - 1, -1, -1):
                    fragment = new_children[i]

                    # Determine the correct anchor for this position
                    # The anchor is the element after this position
                    if i + 1 < len(new_children):
                        # Anchor is the next fragment's first element
                        next_fragment = new_children[i + 1]
                        anchor = next_fragment.first()
                    else:
                        # This is the last item, use the list's anchor
                        anchor = self.anchor()

                    # Check if fragment needs to be mounted or moved
                    if not fragment._mounted:
                        # Mount new fragment at the correct position
                        fragment.mount(target, anchor=anchor)
                    else:
                        # Fragment is already mounted, move it in the DOM if needed
                        if fragment.element:
                            # Check if it's already in the correct position
                            # Get the actual next sibling in the current DOM
                            current_next = self._get_next_sibling(
                                fragment.element, target
                            )

                            # Only move if not already in correct position
                            if current_next != anchor:
                                # Remove from current position
                                # (but keep element reference)
                                # and insert at new position
                                self.renderer.remove(fragment.element, target)
                                self.renderer.insert(
                                    fragment.element, parent=target, anchor=anchor
                                )

                # Update children list
                self.children = new_children

            def _get_next_sibling(element, parent):
                """Get the next sibling element in the parent's children list"""
                try:
                    idx = parent.children.index(element)
                    if idx + 1 < len(parent.children):
                        return parent.children[idx + 1]
                    return None
                except (ValueError, AttributeError):
                    return None

            # Bind the helper function to self
            self._get_next_sibling = _get_next_sibling

            # Watch for changes
            self._watchers["list"] = watch_effect(update_children_keyed)
        else:
            # Index-based reconciliation (original logic)
            @weak(self)
            def update_children(self):
                items = expression()
                for index in reversed(range(len(items), len(self.children))):
                    # Remove extra items and context
                    fragment = self.children.pop(index)
                    fragment.unmount()
                    self.values.pop(index)

                for i, item in enumerate(items):
                    if i < len(self.children):
                        # Update the content for existing values
                        self.values[i]["context"] = item
                    else:
                        # Create a new fragment + context
                        context = reactive({"context": item})
                        self.values.append(context)
                        fragment = self.create_fragment(
                            lambda i=i: self.values[i]["context"]
                        )
                        self.children.append(fragment)
                        fragment.parent = self
                        fragment.mount(target, anchor=self.anchor())

            # Then we add a watch_effect for the children
            # which adds/removes/updates all the child fragments
            self._watchers["list"] = watch_effect(update_children)

        for child in self.children:
            if not child.element:
                child.mount(target, anchor=self.anchor())

        self._mounted = True

    def unmount(self, destroy=True):
        super().unmount(destroy=destroy)
        # Clear the children array, so that they get recreated on remount
        self.children = []


class ComponentFragment(Fragment):
    def __init__(self, *args, props=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.component: Component | None = None
        self.fragment: Fragment | None = None
        self.props: dict[Any, Any] | None = props
        self.slots: dict = {}
        self.slot_contents = []
        assert "tag" not in kwargs or callable(kwargs["tag"])

    def register_child(self, child: Fragment) -> None:
        if self.tag:
            self.slot_contents.append(child)
        else:
            self.children.append(child)

    def first(self) -> Any | None:
        """Return the first element from the rendered component fragment"""
        if self.fragment:
            return self.fragment.first()
        return super().first()

    def create(self):
        if self.tag is None:
            return

        if self.props is None:
            self.props = reactive({})
        # Set static attributes
        self.props.update(self._attributes)

        # Apply all dynamic attributes
        for name, expression, singular in self._binds:
            if singular:
                self._watch_bind(name, expression)
            else:
                self._watch_bind_dict(name, expression)

        # Set dynamic attributes
        for key, watcher in self._watchers.items():
            if key.startswith("bind:"):
                _, attr = key.split(":")
                self.props[attr] = watcher.value

        parent = self._component_parent()
        assert not isinstance(self.tag, str)
        self.component = self.tag(props=self.props, parent=parent)
        self.fragment = self.component.render(self.renderer)
        self.fragment.parent = self
        self.children.append(self.fragment)

        # Add all event handlers
        for event, handler in self._events.items():
            self.component.add_event_handler(event, handler)

    def mount(self, target: Any, anchor: Any | None = None):
        if self._mounted:
            return

        self.target = target
        self.create()

        if self.fragment:
            self.fragment.mount(target, anchor)
        else:
            for child in self.children:
                child.mount(target, anchor)

        if self.component:
            from collections import deque

            # Use fifo data structure (double-ended queue)
            lookup = deque(self.children)
            try:
                while True:
                    child = lookup.popleft()
                    if element := child.element:
                        self.component._element = element
                        lookup.clear()
                        break
                    lookup.extend(child.children)
            except IndexError:
                pass

            self.component.mounted()

        self._mounted = True

    def register_slot(self, name, fragment: SlotFragment):
        self.slots[name] = fragment

    def _set_attr(self, attr, value):
        self.props[attr] = value

    def _rem_attr(self, attr):
        del self.props[attr]

    def _remove(self):
        self.props = None

    def unmount(self, destroy=True):
        if self.component:
            self.component.before_unmount()

        # Unmount slot contents before calling super
        for slot_content in self.slot_contents:
            slot_content.unmount(destroy=destroy)

        super().unmount(destroy=destroy)


class SlotFragment(Fragment):
    """
    Fragment that describes a 'slot' element

    Problem with this: mounting works on 'this' item, which means that
    it only controls this instance, and not its children...
    So if we need another layer of abstraction to (conditionally) mount
    a subtree, we'll need a different mechanism. Probably.

    Instead of 'mounting' an element, we could for instance 'attach' an
    element to its parent. So basically we ask the parent to mount/unmount
    the current element. The parent can then redirect the actual mounting
    to wherever it is actually needed?

    Workaround: use a template tag if dynamic slot content is needed.
    See: tests/data/slots/dynamic_if_template.cgx
    """

    def __init__(self, *args, name, tag=None, props=None, **kwargs):
        super().__init__(*args, tag=None, **kwargs)
        self.name = name

        parent = self.parent
        while parent.parent:
            parent = parent.parent

        assert isinstance(parent, ComponentFragment)
        assert parent.tag is None
        self.parent_component = parent
        self.parent_component.register_slot(name, self)

    def set_attribute(self, attr: str, value: Any):
        # name is a reserved attribute for slots
        if attr != "name":
            super().set_attribute(attr, value)

    def mount(self, target: Any, anchor: Any | None = None):
        component_parent = self.parent_component.parent
        if component_parent.slot_contents:
            for item in component_parent.slot_contents:
                if item.slot_name == self.name:
                    item.mount(target, anchor)
        else:
            super().mount(target, anchor)


class DynamicFragment(Fragment):
    """
    Fragment for dynamic component tags: <component :is="expression" />

    Handles switching between different tag types (components or elements)
    based on a reactive expression.
    """

    def __init__(
        self, renderer: Renderer, expression: Callable, parent: Fragment | None = None
    ):
        # Don't pass tag to parent - it will be dynamic
        super().__init__(renderer, tag=None, parent=parent)

        # Store the expression that determines the tag
        self._expression = expression

        # Current active fragment (ComponentFragment or regular Fragment)
        self._active_fragment: Fragment | None = None

        # Watcher for the expression
        self._type_watcher: Watcher | None = None

    def create(self):
        """Create the initial fragment based on expression value"""
        # Evaluate expression to get initial tag
        tag = self._expression()

        # Create fragment for this tag
        self._create_fragment_for_tag(tag)

        # Set up watcher for tag changes
        @weak(self)
        def update_type(self, new_tag):
            # Calculate anchor before unmounting
            anchor = self.anchor()

            # Unmount current fragment
            if self._active_fragment:
                # Note: _active_fragment is no longer in self.children
                # (it's removed in _create_fragment_for_tag)
                self._active_fragment.unmount(destroy=False)

            # Create new fragment
            self._create_fragment_for_tag(new_tag)

            # Mount it
            if self._active_fragment:
                self._active_fragment.mount(self.target, anchor)

        self._type_watcher = watch(
            self._expression,
            update_type,
            immediate=False,
        )

    def _create_fragment_for_tag(self, tag):
        """Create appropriate fragment for the given tag"""
        # Save existing children before creating active fragment
        # If we had a ComponentFragment, children are in its slot_contents
        if (
            self._active_fragment
            and isinstance(self._active_fragment, ComponentFragment)
            and self._active_fragment.tag is not None
        ):
            # Get children from previous ComponentFragment's slot_contents
            existing_children = self._active_fragment.slot_contents.copy()
        else:
            # Get children from DynamicFragment's children
            existing_children = self.children.copy()

        if callable(tag):
            # Component class - create ComponentFragment
            # Don't pass parent, so that the register_child method is skipped
            # so that the _active_fragment won't be part of the children
            # which are whatever is specified in the template
            self._active_fragment = ComponentFragment(
                self.renderer,
                tag=tag,
                props=reactive({}),
            )
            # Manually set the parent
            self._active_fragment._parent = ref(self)

            # Transfer existing children as slot content
            # ComponentFragment.register_child() adds them to slot_contents
            # when tag is set
            for child in existing_children:
                child._parent = ref(self._active_fragment)
                # Set slot_name to "default" if not already set (e.g., by v-slot:name)
                if not hasattr(child, "slot_name") or child.slot_name is None:
                    child.slot_name = "default"
                self._active_fragment.register_child(child)
        else:
            # String tag - create regular Fragment
            # Also don't pass parent here
            self._active_fragment = Fragment(
                self.renderer,
                tag=tag,
            )
            # Manually set the parent
            self._active_fragment._parent = ref(self)

            # Transfer existing children to the active fragment
            for child in existing_children:
                child._parent = ref(self._active_fragment)
                self._active_fragment.children.append(child)

        # Transfer attributes, bindings, events from self to active fragment
        self._active_fragment._attributes.update(self._attributes)
        self._active_fragment._binds.extend(self._binds)
        self._active_fragment._events.update(self._events)

        # Create the fragment
        self._active_fragment.create()

    def mount(self, target: Any, anchor: Any | None = None):
        if self._mounted:
            return

        self.target = target
        self.create()

        # Mount the active fragment
        if self._active_fragment:
            self._active_fragment.mount(target, anchor)

        self._mounted = True

    def unmount(self, destroy=True):
        self._mounted = False

        # Unmount active fragment
        if self._active_fragment:
            self._active_fragment.unmount(destroy=destroy)
            if destroy:
                self._active_fragment = None

        # Standard cleanup
        for child in self.children:
            child.unmount(destroy=destroy)

        self._remove()

        if destroy:
            self.element = None
            self.target = None
            self._attributes = {}
            self._events = {}
            if self._type_watcher:
                self._type_watcher()
                self._type_watcher = None
            self._condition = None
            self._expression = None
        else:
            self.element = None
            # Keep _type_watcher alive for dynamic tag switching

    def first(self) -> Any | None:
        if self._active_fragment:
            return self._active_fragment.first()
        return None

    def _set_attr(self, attr, value):
        # Update our attributes (for transfer to next fragment)
        self._attributes[attr] = value
        # Apply to active fragment
        if self._active_fragment:
            self._active_fragment._set_attr(attr, value)

    def _rem_attr(self, attr):
        if attr in self._attributes:
            del self._attributes[attr]
        if self._active_fragment:
            self._active_fragment._rem_attr(attr)

    def _remove(self):
        if self._active_fragment:
            self._active_fragment._remove()
