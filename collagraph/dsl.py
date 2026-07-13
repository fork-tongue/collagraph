"""
Pure-Python view API for collagraph components.

Instead of writing a .cgx template, components can describe their UI in a
`view` method using the element builder `h` together with the control flow
helpers from this module. The view method runs *once* when the component is
created (like a compiled .cgx render function); fine-grained reactivity is
achieved by passing zero-argument callables for anything dynamic.

The one rule to remember: **a plain value is static, a callable is live**.

    import collagraph as cg
    from collagraph import h


    class Counter(cg.Component):
        def init(self):
            self.state["count"] = 0

        def bump(self):
            self.state["count"] += 1

        def view(self):
            with h.widget():
                h.label(text=lambda: f"Count: {self.state['count']}")
                h.button("bump", on_clicked=self.bump)

Keyword arguments to an element map onto the fragment API as follows:

* plain value: static attribute (``set_attribute``)
* callable: reactive bind (``set_bind``)
* ``on_<event>``: event handler (``set_event``)
* ``bind``: callable returning a dict of attributes (``set_bind_dict``),
  the pure-Python equivalent of ``v-bind="dict"``
* ``ref``: template ref (string or callable)

Positional arguments to an element become text children: plain strings are
static text, callables are live text (the equivalent of ``{{ expression }}``).

Control flow (``v-if``/``v-else-if``/``v-else``) is expressed with ``when``,
``or_when`` and ``otherwise``; list rendering (``v-for``) with the ``each``
decorator. Slots are declared with ``slot`` and filled with ``fill``. Dynamic
components (``<component :is="...">``) are created with ``dynamic``.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from inspect import signature
from typing import Any
from warnings import warn
from weakref import ref

from .component import Component
from .fragment import (
    ComponentFragment,
    ControlFlowFragment,
    DynamicFragment,
    Fragment,
    ListFragment,
    SlotFragment,
)
from .renderers import Renderer

# Adjust this setting to disable some runtime checks
# Defaults to True, except when it is part of an installed application
DSL_RUNTIME_WARNINGS = not getattr(sys, "frozen", False)

EVENT_PREFIX = "on_"
BIND_DICT_KEY = "bind"


class _Frame:
    """One level of nesting in the view being built."""

    __slots__ = ("control_flow", "fragment")

    def __init__(self, fragment: Fragment):
        self.fragment = fragment
        # The 'open' ControlFlowFragment that a subsequent or_when/otherwise
        # at this nesting level would attach to. Reset whenever a regular
        # sibling element is added (mirrors how adjacency of v-if/v-else-if/
        # v-else works in templates).
        self.control_flow: ControlFlowFragment | None = None


class _Builder:
    """Tracks the fragment tree under construction for one view (or one
    generated list item)."""

    __slots__ = ("frames", "renderer")

    def __init__(self, renderer: Renderer):
        self.renderer = renderer
        self.frames: list[_Frame] = []

    @property
    def frame(self) -> _Frame:
        return self.frames[-1]


# Stack of active builders. A plain list suffices: views are built
# synchronously, and list item factories (which run later, during mount
# and updates) push their own builder.
_builders: list[_Builder] = []


def _current_builder() -> _Builder:
    if not _builders:
        raise RuntimeError(
            "No view is being built: h() and the other view functions can "
            "only be called (directly or indirectly) from a component's "
            "`view` method"
        )
    return _builders[-1]


def _is_component_usage(fragment: Fragment) -> bool:
    """Whether the fragment is a component usage site (children of which
    become slot content)."""
    return isinstance(fragment, ComponentFragment) and fragment.tag is not None


def _attach(builder: _Builder, fragment: Fragment, slot_name: str | None = None):
    """Attach a newly built fragment to the current parent.

    Children of a component usage site become slot content: their slot name
    has to be set *before* registering with the parent.
    """
    parent = builder.frame.fragment
    if _is_component_usage(parent):
        fragment.slot_name = slot_name or fragment.slot_name or "default"
    fragment._parent = ref(parent)
    parent.register_child(fragment)


class _Node:
    """Handle to a built fragment. Can be used as context manager to nest
    child elements."""

    __slots__ = ("_builder", "fragment")

    def __init__(self, fragment: Fragment, builder: _Builder):
        self.fragment = fragment
        self._builder = builder

    def __enter__(self) -> _Node:
        self._builder.frames.append(_Frame(self.fragment))
        return self

    def __exit__(self, *exc) -> bool:
        frame = self._builder.frames.pop()
        assert frame.fragment is self.fragment
        return False


class _Static:
    """Marks a callable that should be treated as a static attribute value
    instead of a reactive bind. See `static`."""

    __slots__ = ("value",)

    def __init__(self, value):
        self.value = value


def static(value) -> _Static:
    """Wrap a callable to pass it as a static attribute value.

    By default a callable attribute value creates a reactive bind. Use this
    to pass an actual function object as a (non-event) attribute instead:

        h.item(sort_function=cg.static(natural_sort))
    """
    return _Static(value)


def _apply_props(fragment: Fragment, props: dict[str, Any]):
    for key, value in props.items():
        if key.startswith(EVENT_PREFIX) and len(key) > len(EVENT_PREFIX):
            fragment.set_event(key[len(EVENT_PREFIX) :], value)
        elif key == BIND_DICT_KEY and callable(value):
            fragment.set_bind_dict(BIND_DICT_KEY, value)
        elif isinstance(value, _Static):
            fragment.set_attribute(key, value.value)
        elif callable(value):
            fragment.set_bind(key, value)
        else:
            fragment.set_attribute(key, value)


def _add_text_children(
    builder: _Builder, fragment: Fragment, children: tuple[Any, ...]
):
    for child in children:
        text = Fragment(builder.renderer, tag="TEXT_ELEMENT")
        if callable(child):
            text.set_bind("content", child)
        else:
            text.set_attribute("content", child)
        text._parent = ref(fragment)
        fragment.register_child(text)


def _element(
    tag: str | type[Component], children: tuple[Any, ...], props: dict[str, Any]
) -> _Node:
    builder = _current_builder()
    is_component = isinstance(tag, type) and issubclass(tag, Component)
    if is_component:
        fragment: Fragment = ComponentFragment(builder.renderer, tag=tag)
    else:
        fragment = Fragment(builder.renderer, tag=tag)
    _apply_props(fragment, props)
    _attach(builder, fragment)
    # A regular sibling breaks any open when/or_when chain
    builder.frame.control_flow = None
    _add_text_children(builder, fragment, children)
    return _Node(fragment, builder)


class _TagBuilder:
    """Bound element builder for a specific tag: `h.widget` etc."""

    __slots__ = ("tag",)

    def __init__(self, tag: str):
        self.tag = tag

    def __call__(self, *children, **props) -> _Node:
        return _element(self.tag, children, props)


class _H:
    """Element builder.

    * ``h("widget", ...)`` or ``h.widget(...)``: element with a string tag
    * ``h(MyComponent, ...)``: child component
    """

    def __call__(self, tag: str | type[Component], *children, **props) -> _Node:
        return _element(tag, children, props)

    def __getattr__(self, tag: str) -> _TagBuilder:
        if tag.startswith("_"):
            raise AttributeError(tag)
        return _TagBuilder(tag)


h = _H()


def _branch(
    builder: _Builder,
    control_flow: ControlFlowFragment,
    condition: Callable[[], Any] | None,
) -> _Node:
    # Branches can hold multiple children, so each branch is wrapped in a
    # virtual (tag-less) fragment which carries the condition.
    branch = Fragment(builder.renderer, tag=None, parent=control_flow)
    if condition is not None:
        branch.set_condition(lambda: bool(condition()))
    return _Node(branch, builder)


def when(condition: Callable[[], Any]) -> _Node:
    """Start a conditional block (``v-if``).

    Content built inside the returned context manager is only rendered while
    the condition evaluates to a truthy value:

        with cg.when(lambda: self.state["ready"]):
            h.label(text="Ready!")
    """
    assert callable(condition), "when() takes a callable, e.g. lambda: state['x']"
    builder = _current_builder()
    frame = builder.frame
    control_flow = ControlFlowFragment(builder.renderer)
    _attach(builder, control_flow)
    frame.control_flow = control_flow
    return _branch(builder, control_flow, condition)


def or_when(condition: Callable[[], Any]) -> _Node:
    """Add an else-if branch (``v-else-if``) to the directly preceding
    `when` block."""
    assert callable(condition), "or_when() takes a callable, e.g. lambda: state['x']"
    builder = _current_builder()
    control_flow = builder.frame.control_flow
    if control_flow is None:
        raise RuntimeError("or_when() must directly follow a when() or or_when() block")
    return _branch(builder, control_flow, condition)


def otherwise() -> _Node:
    """Add an else branch (``v-else``) to the directly preceding `when`
    block."""
    builder = _current_builder()
    control_flow = builder.frame.control_flow
    if control_flow is None:
        raise RuntimeError(
            "otherwise() must directly follow a when() or or_when() block"
        )
    # The chain is complete: nothing can attach to it anymore
    builder.frame.control_flow = None
    return _branch(builder, control_flow, None)


def each(expression: Callable[[], Any], key: Callable[[Any], Any] | None = None):
    """Render an item of content for each value of a reactive collection
    (``v-for``).

    Used as a decorator on a function that builds the content for a single
    item. The function receives one *getter* per loop variable: a
    zero-argument callable returning the current value (call it inside your
    lambdas, so that the read happens when the binding updates):

        @cg.each(lambda: self.state["items"], key=lambda item: item["id"])
        def _(item):
            h.label(text=lambda: item()["text"])

    Multiple loop variables work through the function signature, like tuple
    unpacking in a for statement:

        @cg.each(lambda: enumerate(self.state["items"]))
        def _(i, item):
            h.label(text=lambda: f"{i()}: {item()}")

    The `key` function (``:key``) receives the whole item value and must
    return a unique, stable identifier; providing it enables keyed
    reconciliation (efficient reordering).
    """
    assert callable(expression), "each() takes a callable, e.g. lambda: state['items']"
    builder = _current_builder()
    renderer = builder.renderer
    list_fragment = ListFragment(renderer)
    _attach(builder, list_fragment)
    builder.frame.control_flow = None

    def decorator(fn: Callable) -> Callable:
        arity = len(
            [
                param
                for param in signature(fn).parameters.values()
                if param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD)
            ]
        )
        if arity == 0:
            raise TypeError(
                "each() requires a function with at least one parameter "
                "(the loop variable getter)"
            )

        def create_fragment(context: Callable[[], Any]) -> Fragment:
            wrapper = Fragment(renderer, tag=None)
            if arity == 1:
                getters: tuple[Callable[[], Any], ...] = (context,)
            else:
                getters = tuple((lambda i=i: context()[i]) for i in range(arity))
            nested = _Builder(renderer)
            nested.frames.append(_Frame(wrapper))
            _builders.append(nested)
            try:
                _call_view_code(lambda: fn(*getters), fn)
            finally:
                _builders.pop()
            return wrapper

        key_extractor = None
        if key is not None:

            def key_extractor(context, _key=key):
                # ListFragment passes a getter for the item
                return _key(context())

        list_fragment.set_create_fragment(
            create_fragment, is_keyed=key is not None, key_extractor=key_extractor
        )
        list_fragment.set_expression(expression)
        return fn

    return decorator


def slot(name: str = "default") -> _Node:
    """Declare a slot (``<slot>``) at this location in the view.

    Content that the parent component provides for this slot name is
    rendered here. Fallback content can be nested inside:

        with cg.slot("header"):
            h.label(text="default header")
    """
    builder = _current_builder()
    parent = builder.frame.fragment
    fragment = SlotFragment(builder.renderer, name=name, parent=parent)
    builder.frame.control_flow = None
    return _Node(fragment, builder)


def fill(name: str = "default") -> _Node:
    """Provide content for a named slot of the surrounding component
    (``<template v-slot:name>``):

        with h(Layout):
            with cg.fill("header"):
                h.label(text="header content")

    Content built directly inside a component element (without `fill`) goes
    to the "default" slot.
    """
    builder = _current_builder()
    parent = builder.frame.fragment
    if not _is_component_usage(parent):
        raise RuntimeError(
            "fill() can only be used directly inside a component element"
        )
    fragment = Fragment(builder.renderer, tag="template")
    _attach(builder, fragment, slot_name=name)
    builder.frame.control_flow = None
    return _Node(fragment, builder)


def dynamic(is_: Callable[[], Any], *children, **props) -> _Node:
    """Create a dynamic element/component (``<component :is="...">``).

    The callable determines the tag: it can return a component class or a
    string tag, and the element is swapped out reactively when the value
    changes."""
    assert callable(is_), "dynamic() takes a callable, e.g. lambda: state['view']"
    builder = _current_builder()
    fragment = DynamicFragment(builder.renderer, expression=is_)
    _apply_props(fragment, props)
    _attach(builder, fragment)
    builder.frame.control_flow = None
    _add_text_children(builder, fragment, children)
    return _Node(fragment, builder)


def _call_view_code(fn: Callable[[], Any], source: Any):
    """Call view-building code, guarding against eager reactive reads.

    Correct view code performs *no* reactive reads while it runs: all reads
    of state/props belong inside the lambdas passed to elements. An eager
    read is almost always a bug (the value would be baked in statically), so
    detect it by running the code as a (temporary) watcher and checking
    whether any dependencies were recorded.

    Wrapping in a watcher also shields any surrounding watcher (e.g. the one
    that re-mounts a conditional block) from accidentally picking up those
    reads as dependencies.
    """
    if not DSL_RUNTIME_WARNINGS:
        fn()
        return

    from observ.watcher import Watcher

    watcher = Watcher(fn)
    try:
        watcher.get()
        if watcher._deps:
            warn(
                f"Reactive value read during view build: {source}.\n"
                "Reads of state/props directly in view code are evaluated "
                "only once and will not update. Wrap the expression in a "
                "lambda to make it reactive, e.g.:\n"
                "  h.label(text=lambda: self.state['count'])"
            )
    finally:
        watcher.stop()


def build_view(component: Component, renderer: Renderer) -> ComponentFragment:
    """Build the fragment tree for a component that defines a `view` method.

    Called by the default `Component.render` implementation."""
    root = ComponentFragment(renderer)
    builder = _Builder(renderer)
    builder.frames.append(_Frame(root))
    _builders.append(builder)
    try:
        _call_view_code(component.view, component)
    finally:
        _builders.pop()
    return root
