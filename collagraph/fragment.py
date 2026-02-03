from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any
from weakref import ref

from observ import computed, reactive, watch_effect
from observ.watcher import Watcher, watch

from .component import Component
from .renderers import Renderer
from .weak import weak


class Fragment:
    """
    A Fragment describes an element in the UI tree.

    Fragments form two conceptual trees:

    1. **Template Tree** (static): The structure defined in the CGX template.
       Parent-child relationships are fixed at compile time. A v-if branch
       is always a child of its ControlFlowFragment, even when hidden.
       Stored in `template_children`.

    2. **Render Tree** (dynamic): What's actually mounted to the DOM.
       Changes based on reactive state. Only includes currently visible
       fragments. Accessed via `render_children()`.

    Subclasses override `render_children()` to control which template
    children are actually rendered (e.g., ControlFlowFragment returns
    only the active branch).
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
        # Template children: static structure from compilation
        self.template_children: list[Fragment] = []
        # Dom element (if any)
        self.element: Any | None = None
        # Target dom-element to render in
        self.target: Any | None = None
        # Name of slot to be rendered into
        self.slot_name: str | None = None

        # Weak ref to parent fragment (template tree)
        self._parent: ref[Fragment] | None = ref(parent) if parent else None
        # Weak ref to render parent (for anchor lookups when mounted as slot content)
        # When set, anchor() uses this instead of _parent
        self._render_parent: ref[Fragment] | None = None
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
        # Reference name or callable for template refs
        self._ref_name: str | None = None
        self._ref_is_dynamic: bool = False

        self._mounted = False

        # Register with parent if provided
        # Note: For slot content, the compiler should NOT pass parent here
        # and instead call register_child() after setting slot_name
        if parent:
            parent.register_child(self)

    def __repr__(self):
        return f"<{type(self).__name__}({self.tag}-[{id(self)}])>"

    def debug(self, indent: int = 0):
        print(f"{'  ' * indent}<{self.tag}>")  # noqa: T201
        for child in self.render_children():
            if child._mounted:
                child.debug(indent + 1)

    @property
    def parent(self) -> Fragment | None:
        return self._parent() if self._parent else None

    @property
    def render_parent(self) -> Fragment | None:
        """
        Parent for render tree operations (anchor lookup).
        Returns _render_parent if set, otherwise falls back to parent.
        """
        if self._render_parent:
            return self._render_parent()
        return self.parent

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
        self._parent = ref(parent) if parent else None

    def register_child(self, child: Fragment) -> None:
        """Register a child fragment in the template tree."""
        self.template_children.append(child)

    def render_children(self) -> Iterable[Fragment]:
        """
        Return children that should be rendered (mounted).

        For base Fragment, all template children are rendered.
        Subclasses override to filter (e.g., ControlFlowFragment
        returns only the active branch).
        """
        return self.template_children

    def iter_all_children(self) -> Iterable[Fragment]:
        """
        Yield ALL children for tree traversal (template + runtime-generated).

        Used by hot reload and other code that needs to traverse the complete
        fragment tree. Unlike render_children(), this includes:
        - All template_children (even inactive branches)
        - Runtime-generated fragments (ListFragment, DynamicFragment)
        - ComponentFragment's rendered_fragment and slot_content

        Subclasses override to include their specific child collections.
        """
        yield from self.template_children

    def first(self) -> Any | None:
        """
        Returns the first DOM element (if any), from either itself, or its
        rendered descendants.
        """
        if self.element:
            return self.element
        for child in self.render_children():
            if element := child.first():
                return element
        return None

    def anchor(self) -> Any | None:
        """
        Returns the DOM element that serves as anchor for this fragment.
        Anchor is the first element of the next sibling in the render tree.
        """
        parent = self.render_parent
        if parent is None:
            return None

        # Find myself in parent's render children and get next sibling's element
        siblings = list(parent.render_children())
        try:
            idx = siblings.index(self)
            for sibling in siblings[idx + 1 :]:
                if element := sibling.first():
                    return element
        except ValueError:
            pass  # Not in render children

        # No sibling anchor found at this level. If the parent doesn't have
        # its own element (e.g., ComponentFragment, ControlFlowFragment), climb
        # up the tree to find an anchor from the parent's siblings.
        # However, don't climb past a fragment whose rendered elements include
        # our mount target, as anchors beyond that belong to a different subtree.
        if not parent.element and parent.render_parent:
            # Check if we would climb past our mount target
            # Skip this check for SlotFragment since its first() includes us
            if target := self.target:
                if not isinstance(parent, SlotFragment) and parent.first() is target:
                    return None
            return parent.anchor()

        return None

    def set_attribute(self, attr: str, value: Any):
        """
        Set a static attribute. Note that it is not directly applied to
        the element, that will happen in the `create` call.
        """
        # Handle ref attribute specially
        if attr == "ref":
            self._ref_name = value
            self._ref_is_dynamic = False
            return

        self._attributes[attr] = value

    def set_bind(self, attr: str, expression: Callable):
        """
        Set a bind (dynamic attribute) to the value of the expression.
        This will wait to be applied when `create` is called.
        """
        # Handle dynamic ref binding specially
        if attr == "ref":
            self._ref_name = expression
            self._ref_is_dynamic = True
            return

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

    def _register_ref(self, ref_value: Any):
        """
        Register a ref with the parent component.
        Handles both string refs and callable (function) refs.
        """
        if not ref_value:
            return

        component = self._component_parent()
        if not component:
            return

        # For ComponentFragment, register the component instance
        if isinstance(self, ComponentFragment) and self.component:
            target = self.component
        else:
            target = self.element

        if not target:
            return

        # Function ref: call it with the element/component
        if callable(ref_value):
            ref_value(target)
        # String ref: store in component.refs dict
        elif isinstance(ref_value, str):
            component._refs[ref_value] = target

    def _unregister_ref(self, ref_value: Any):
        """
        Unregister a ref from the parent component.
        """
        if not ref_value:
            return

        component = self._component_parent()
        if not component:
            return

        # Function ref: call it with None
        if callable(ref_value):
            ref_value(None)
        # String ref: remove from component.refs dict
        elif isinstance(ref_value, str) and ref_value in component._refs:
            del component._refs[ref_value]

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

        # Set up dynamic ref watcher if needed
        if self._ref_is_dynamic and self._ref_name:

            @weak(self)
            def ref_update(self, new_ref_value, old_ref_value):
                # Unregister old ref
                if old_ref_value:
                    self._unregister_ref(old_ref_value)
                # Register new ref
                if new_ref_value:
                    self._register_ref(new_ref_value)

            # Watch the ref expression
            self._watchers["ref"] = watch(
                self._ref_name,
                ref_update,
                immediate=True,
                deep=False,
            )

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

        for child in self.render_children():
            # For virtual elements, mount in target and use the
            # anchor for the correct placement
            if not self.element:
                child.mount(target, anchor)
            else:
                child.mount(self.element)

        # Register static ref after element is mounted
        # (dynamic refs are handled by the watcher created in create())
        if not self._ref_is_dynamic and self._ref_name:
            self._register_ref(self._ref_name)

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

        # Clean up ref before unmounting
        # For dynamic refs with destroy=True, we need to unregister the current value
        # For static refs, always unregister
        if self._ref_name:
            if self._ref_is_dynamic:
                # For dynamic refs, get the current value and unregister it
                # This handles function refs being called with None
                if "ref" in self._watchers:
                    current_value = self._watchers["ref"].value
                    if current_value:
                        self._unregister_ref(current_value)
            else:
                # Static refs - just unregister the name
                self._unregister_ref(self._ref_name)

        # Unmount all template children (cleanup everything, not just rendered)
        for child in self.template_children:
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
            self._ref_name = None
            self._ref_is_dynamic = False
        else:
            self.element = None
            # Disable the fn and callback of the watcher to disable
            # any 'false' triggers
            for unwatch in self._watchers.values():
                unwatch()
            self._watchers = {}


class ControlFlowFragment(Fragment):
    """
    Fragment for conditional rendering (v-if/v-else-if/v-else).

    Template children are all the branches. Only one (or zero) is rendered
    at a time based on the conditions.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The currently active (rendered) child branch
        self._active_child: Fragment | None = None

    def render_children(self) -> Iterable[Fragment]:
        """Return only the active branch (0 or 1 fragments)."""
        if self._active_child:
            yield self._active_child

    def _compute_active_child(self) -> Fragment | None:
        """Determine which branch should be active based on conditions."""
        for child in self.template_children:
            if child._condition is not None:
                # if and else-if blocks
                if child._condition():
                    return child
            else:
                # else block (no condition)
                return child
        return None

    def mount(self, target: Any, anchor: Any | None = None):
        if self._mounted:
            return
        self.target = target

        @weak(self)
        def update_fragment(self, new: Fragment | None, old: Fragment | None):
            if new is old:
                return  # No need to remount, since it is the same fragment
            if old:
                old.unmount(destroy=False)
            self._active_child = new
            if new:
                anch = anchor
                if anch is None and self.parent:
                    anch = self.anchor()
                new.mount(self.target, anch)

        @weak(self)
        def active_child(self):
            return self._compute_active_child()

        self._watchers["control_flow"] = watch(
            active_child,
            update_fragment,
            deep=True,
            immediate=True,
        )
        self._mounted = True


class ListFragment(Fragment):
    """
    Fragment for list rendering (v-for).

    The template_children contains the template for one item (used as a factory).
    Generated fragments for each list item are stored in _generated_fragments.

    For keyed lists, fragments are tracked by key for efficient reordering.
    For unkeyed lists, fragments are reused by index.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.create_fragment: Callable[[], Fragment] | None = None
        self.expression: Callable[[], list[Any]] | None = None
        self.is_keyed: bool = False
        self.key_extractor: Callable[[Any], Any] | None = None
        # Generated fragments for current list items
        self._generated_fragments: list[Fragment] = []

    def render_children(self) -> Iterable[Fragment]:
        """Return generated fragments for current list items."""
        return self._generated_fragments

    def iter_all_children(self) -> Iterable[Fragment]:
        """Yield template children (factory) and all generated fragments."""
        yield from self.template_children
        yield from self._generated_fragments

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
                    # Remove from generated fragments list
                    self._generated_fragments.remove(fragment)
                    fragment.unmount()

                # Build new fragments array in the correct order
                new_fragments = []
                for i, key in enumerate(new_keys):
                    item = new_key_to_item[key]

                    if key in self.key_to_fragment:
                        # Reuse existing fragment
                        fragment = self.key_to_fragment[key]
                        # Update the context with new item value
                        new_fragments.append(fragment)
                    else:
                        # Create new fragment for new key
                        context = reactive({"context": item})
                        fragment = self.create_fragment(lambda c=context: c["context"])
                        fragment.parent = self
                        self.key_to_fragment[key] = fragment
                        new_fragments.append(fragment)

                # Now we need to reorder/mount the DOM elements to match new_fragments
                # We process from the end to the beginning to avoid interference
                # from previous moves
                for i in range(len(new_fragments) - 1, -1, -1):
                    fragment = new_fragments[i]

                    # Determine the correct anchor for this position
                    # The anchor is the element after this position
                    if i + 1 < len(new_fragments):
                        # Anchor is the next fragment's first element
                        next_fragment = new_fragments[i + 1]
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

                # Update generated fragments list
                self._generated_fragments = new_fragments

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
                num_generated = len(self._generated_fragments)
                for index in reversed(range(len(items), num_generated)):
                    # Remove extra items and context
                    fragment = self._generated_fragments.pop(index)
                    fragment.unmount()
                    self.values.pop(index)

                for i, item in enumerate(items):
                    if i < len(self._generated_fragments):
                        # Update the content for existing values
                        self.values[i]["context"] = item
                    else:
                        # Create a new fragment + context
                        context = reactive({"context": item})
                        self.values.append(context)
                        fragment = self.create_fragment(
                            lambda i=i: self.values[i]["context"]
                        )
                        self._generated_fragments.append(fragment)
                        fragment.parent = self
                        fragment.mount(target, anchor=self.anchor())

            # Then we add a watch_effect for the children
            # which adds/removes/updates all the child fragments
            self._watchers["list"] = watch_effect(update_children)

        for child in self._generated_fragments:
            if not child.element:
                child.mount(target, anchor=self.anchor())

        self._mounted = True

    def unmount(self, destroy=True):
        # First unmount all generated fragments
        for child in self._generated_fragments:
            child.unmount(destroy=destroy)
        # Clear the generated fragments, so that they get recreated on remount
        self._generated_fragments = []
        # Then call parent unmount for cleanup
        super().unmount(destroy=destroy)


class ComponentFragment(Fragment):
    """
    Fragment for component instances.

    ComponentFragment has two modes based on whether `tag` is set:

    1. When `tag` is set (component usage site, e.g., <MyComponent>):
       - `slot_content` dict maps slot names to fragment lists
       - `rendered_fragment` holds the component's render output
       - `render_children()` yields `rendered_fragment`

    2. When `tag` is None (render wrapper inside component):
       - `template_children` contains the component's template output
       - `render_children()` returns `template_children`
    """

    def __init__(self, *args, props=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.component: Component | None = None
        # The fragment returned by component.render()
        self.rendered_fragment: Fragment | None = None
        self.props: dict[Any, Any] | None = props
        self.slots: dict = {}
        # Slot content: maps slot name to list of fragments
        # Content with no explicit slot goes to "default"
        self.slot_content: dict[str, list[Fragment]] = {}
        assert "tag" not in kwargs or callable(kwargs["tag"])

    def register_child(self, child: Fragment) -> None:
        """
        Register a child fragment.

        When tag is set (component usage), children are slot content.
        When tag is None (render wrapper), children are template children.
        """
        if self.tag:
            # This is a component usage - children are slot content
            slot_name = child.slot_name or "default"
            if slot_name not in self.slot_content:
                self.slot_content[slot_name] = []
            self.slot_content[slot_name].append(child)
        else:
            # This is a render wrapper - children are template children
            self.template_children.append(child)

    def render_children(self) -> Iterable[Fragment]:
        """Return the rendered fragment (component's output)."""
        if self.rendered_fragment:
            yield self.rendered_fragment
        else:
            yield from self.template_children

    def iter_all_children(self) -> Iterable[Fragment]:
        """Yield all children: template, rendered, and slot content."""
        yield from self.template_children
        if self.rendered_fragment:
            yield self.rendered_fragment
        for slot_fragments in self.slot_content.values():
            yield from slot_fragments

    def first(self) -> Any | None:
        """Return the first element from the rendered component fragment."""
        if self.rendered_fragment:
            return self.rendered_fragment.first()
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
        self.rendered_fragment = self.component.render(self.renderer)
        self.rendered_fragment.parent = self

        # Add all event handlers
        for event, handler in self._events.items():
            self.component.add_event_handler(event, handler)

        # Set up dynamic ref watcher if needed (for component refs)
        if self._ref_is_dynamic and self._ref_name:

            @weak(self)
            def ref_update(self, new_ref_value, old_ref_value):
                # Unregister old ref
                if old_ref_value:
                    self._unregister_ref(old_ref_value)
                # Register new ref
                if new_ref_value:
                    self._register_ref(new_ref_value)

            # Watch the ref expression
            self._watchers["ref"] = watch(
                self._ref_name,
                ref_update,
                immediate=True,
                deep=False,
            )

    def mount(self, target: Any, anchor: Any | None = None):
        if self._mounted:
            return

        self.target = target
        self.create()

        if self.rendered_fragment:
            self.rendered_fragment.mount(target, anchor)
        else:
            for child in self.render_children():
                child.mount(target, anchor)

        if self.component:
            from collections import deque

            # Find the first element in the render tree
            lookup = deque(self.render_children())
            try:
                while True:
                    child = lookup.popleft()
                    if element := child.element:
                        self.component._element = element
                        lookup.clear()
                        break
                    lookup.extend(child.render_children())
            except IndexError:
                pass

            # Register static component ref after component is mounted
            # (dynamic refs are handled by the watcher created in create())
            # Override base class behavior to register component instance
            if not self._ref_is_dynamic and self._ref_name:
                self._register_ref(self._ref_name)

            self.component.mounted()

        self._mounted = True

    def register_slot(self, name, fragment: SlotFragment):
        self.slots[name] = fragment

    def get_slot_content(self, name: str) -> list[Fragment]:
        """Get slot content for a given slot name."""
        return self.slot_content.get(name, [])

    def _set_attr(self, attr, value):
        self.props[attr] = value

    def _rem_attr(self, attr):
        del self.props[attr]

    def _remove(self):
        self.props = None

    def unmount(self, destroy=True):
        # Clean up component ref before unmounting
        # Handle both static and dynamic refs
        if self._ref_name and self.component:
            if self._ref_is_dynamic:
                # For dynamic refs, get the current value and unregister it
                if "ref" in self._watchers:
                    current_value = self._watchers["ref"].value
                    if current_value:
                        self._unregister_ref(current_value)
            else:
                # Static refs - just unregister the name
                self._unregister_ref(self._ref_name)

        if self.component:
            self.component.before_unmount()

        # Unmount the rendered fragment (component's output) - for component usage site
        if self.rendered_fragment:
            self.rendered_fragment.unmount(destroy=destroy)

        # Unmount slot content
        for slot_fragments in self.slot_content.values():
            for fragment in slot_fragments:
                fragment.unmount(destroy=destroy)

        # Unmount template children (for render wrapper with tag=None)
        for child in self.template_children:
            child.unmount(destroy=destroy)

        # Set _ref_name to None before cleanup
        temp_ref_name = self._ref_name
        temp_ref_is_dynamic = self._ref_is_dynamic
        self._ref_name = None
        self._ref_is_dynamic = False

        self._mounted = False
        self._remove()

        if destroy:
            self.element = None
            self.target = None
            self._attributes = {}
            self._events = {}
            for unwatch in self._watchers.values():
                unwatch()
            self._watchers = {}
            self._condition = None
            self.tag = None
            # Clear ComponentFragment-specific state
            self.rendered_fragment = None
            self.template_children.clear()
            self.slot_content.clear()
            self.slots.clear()
            self.component = None
            self.props = None
        else:
            self.element = None
            for unwatch in self._watchers.values():
                unwatch()
            self._watchers = {}
            self._ref_name = temp_ref_name
            self._ref_is_dynamic = temp_ref_is_dynamic


class SlotFragment(Fragment):
    """
    Fragment that renders slot content from a component's usage site.

    SlotFragment looks up slot content from the parent ComponentFragment
    and renders it at the slot's location inside the component's template.

    Note: For dynamic slot content (v-if on slot content), use a template
    tag wrapper. See: tests/data/slots/dynamic_if_template.cgx
    """

    def __init__(self, *args, name, tag=None, props=None, **kwargs):
        super().__init__(*args, tag=None, **kwargs)
        self.name = name

        # Walk up to find the root ComponentFragment (render wrapper)
        parent = self.parent
        while parent.parent:
            parent = parent.parent

        assert isinstance(parent, ComponentFragment)
        assert parent.tag is None
        self._root_component = parent
        self._root_component.register_slot(name, self)

    def set_attribute(self, attr: str, value: Any):
        # name is a reserved attribute for slots
        if attr != "name":
            super().set_attribute(attr, value)

    def render_children(self) -> Iterable[Fragment]:
        """
        Return slot content from the component usage site.

        If there's slot content for this slot name, return it.
        Otherwise, return template_children (default slot content).
        """
        # Get the ComponentFragment that represents the component usage
        component_usage = self._root_component.parent
        if isinstance(component_usage, ComponentFragment):
            slot_content = component_usage.get_slot_content(self.name)
            if slot_content:
                return slot_content
        # Fall back to default slot content (template children)
        return self.template_children

    def mount(self, target: Any, anchor: Any | None = None):
        if self._mounted:
            return

        self.target = target

        # Mount slot content (or default content)
        # Set render_parent so that slot content looks for anchors within the slot
        for child in self.render_children():
            child._render_parent = ref(self)
            child.mount(target, anchor)

        self._mounted = True


class DynamicFragment(Fragment):
    """
    Fragment for dynamic component tags: <component :is="expression" />

    Template children are the slot content to pass to the dynamic component.
    The active fragment (ComponentFragment or Fragment) is created based
    on the reactive expression value.
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

    def render_children(self) -> Iterable[Fragment]:
        """Return the active fragment."""
        if self._active_fragment:
            yield self._active_fragment

    def iter_all_children(self) -> Iterable[Fragment]:
        """Yield template children and active fragment."""
        yield from self.template_children
        if self._active_fragment:
            yield self._active_fragment

    def create(self):
        """Create the initial fragment based on expression value."""
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
        """Create appropriate fragment for the given tag."""
        # Get existing children to transfer
        # If we had a ComponentFragment, get its slot content
        if (
            self._active_fragment
            and isinstance(self._active_fragment, ComponentFragment)
            and self._active_fragment.tag is not None
        ):
            # Collect all slot content from the ComponentFragment
            existing_children = []
            for fragments in self._active_fragment.slot_content.values():
                existing_children.extend(fragments)
        else:
            # Get children from DynamicFragment's template_children
            existing_children = self.template_children.copy()

        if callable(tag):
            # Component class - create ComponentFragment
            # Don't pass parent to skip register_child
            self._active_fragment = ComponentFragment(
                self.renderer,
                tag=tag,
                props=reactive({}),
            )
            # Manually set the parent
            self._active_fragment._parent = ref(self)

            # Transfer existing children as slot content
            for child in existing_children:
                child._parent = ref(self._active_fragment)
                # Set slot_name to "default" if not already set
                if child.slot_name is None:
                    child.slot_name = "default"
                self._active_fragment.register_child(child)
        else:
            # String tag - create regular Fragment
            # Don't pass parent to skip register_child
            self._active_fragment = Fragment(
                self.renderer,
                tag=tag,
            )
            # Manually set the parent
            self._active_fragment._parent = ref(self)

            # Transfer existing children to the active fragment
            for child in existing_children:
                child._parent = ref(self._active_fragment)
                self._active_fragment.template_children.append(child)

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

        # Standard cleanup for template children
        for child in self.template_children:
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
