# Python Views

Besides `.cgx` templates, components can describe their UI in **plain Python**, using the element builder `h` in a `view` method:

```python title="counter.py"
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
```

Both styles are fully supported and can be mixed freely in one application: a `.cgx` component can use a Python-view component as a child and vice versa. Python views are just regular Python, so type checkers, linters, formatters, debuggers and IDEs work out of the box — no plugins needed.

## How it works

The `view` method runs **once**, when the component is created — just like the render function that is compiled from a `.cgx` template. It builds a tree of elements; afterwards, fine-grained reactivity keeps the UI up to date without ever re-running `view`.

That works through one rule:

!!! tip "The one rule"
    **A plain value is static, a zero-argument callable is live.**

    ```python
    h.label(text="never changes")                           # static
    h.label(text=lambda: f"Count: {self.state['count']}")   # updates reactively
    ```

Everything dynamic — attribute values, text, conditions, list expressions — is passed as a callable (usually a `lambda`). Collagraph watches each callable and updates exactly the thing it is bound to when its value changes, comparable to how [Solid](https://www.solidjs.com) works in the JavaScript world.

Unlike in templates, there is no name resolution magic: expressions are ordinary closures, so state is accessed as `self.state["count"]` (not `count`).

## Elements

`h` creates elements. Use attribute access for regular elements and pass component classes directly:

```python
h.label(text="plain element")     # equivalent to h("label", ...)
h("flow-layout")                  # tags that aren't valid identifiers
h(TodoList, items=lambda: ...)    # child component
```

Nest elements with `with`:

```python
def view(self):
    with h.widget():
        h.label(text="one")
        with h.widget(layout={"type": "Box", "direction": "LeftToRight"}):
            h.label(text="two")
```

Just like templates, a view can have multiple root elements.

## Attributes

Keyword arguments become attributes, following the one rule:

```python
h.button(
    text="Add",                                # static (like text="Add")
    enabled=lambda: len(self.state["items"]),  # bound (like :enabled="...")
)
```

Attribute names with dashes are written with underscores (`maximum_size` instead of `maximum-size`); the PySide renderer treats them the same.

To bind a whole dict of attributes at once (`v-bind="attrs"`), use the `bind` keyword:

```python
h.label(bind=lambda: self.props["attrs"])
```

To pass an actual function object as a static attribute value (which would otherwise be interpreted as a live binding), wrap it in `cg.static`:

```python
h.item(sort_function=cg.static(natural_sort))
```

## Events

Keyword arguments starting with `on_` register event handlers (`@clicked` in templates):

```python
h.button(text="Add", on_clicked=self.handle_submit)
h.lineedit(on_text_edited=self.handle_change)
```

Handlers are regular callables and receive whatever arguments the event emits.

## Text content

Positional arguments become text content — the equivalent of `{{ interpolation }}`:

```python
h.label("static text")
h.label(lambda: f"Count: {self.state['count']}")
h.button("bump", on_clicked=self.bump)
```

!!! note "Renderer support"
    Like text in templates, this requires the renderer to support text elements. For other elements, set text through an attribute such as `text=`.

## Conditional rendering

`when`, `elif_` and `otherwise` are the equivalents of `v-if`, `v-else-if` and `v-else`. Content built inside the block is only rendered while the condition holds:

```python
with cg.when(lambda: self.props["status"] == "loading"):
    h.label(text="Loading…")
with cg.elif_(lambda: self.props["status"] == "error"):
    h.label(text="Error!")
with cg.otherwise():
    h.label(text="Ready")
```

Like `v-else-if`/`v-else` in templates, `elif_` and `otherwise` must directly follow the block they belong to. A branch may contain any number of elements.

!!! warning "Don't use a plain `if`"
    A regular Python `if` statement in `view` runs only once, when the view is built — the UI would never react to changes. Any condition that depends on state or props belongs in a `when`.

## List rendering

`each` is the equivalent of `v-for`. It decorates a function that builds the content for a single item:

```python
with h.widget():

    @cg.each(lambda: self.state["items"], key=lambda item: item["id"])
    def _(item):
        h.label(text=lambda: item()["text"])
```

The function receives the loop variable as a **getter**: a zero-argument callable returning the current value. Call it *inside* your lambdas (`item()`), so that the read happens whenever the binding updates — this is what allows collagraph to update items in place instead of rebuilding the list.

Multiple loop variables work through the function signature, like tuple unpacking in a `for` statement:

```python
@cg.each(lambda: enumerate(self.state["items"]))
def _(index, item):
    h.label(text=lambda: f"{index()}: {item()}")
```

The `key` function is the equivalent of `:key`: it receives the item value and should return a unique, stable identifier. Providing it enables keyed reconciliation, so that reordering moves elements instead of recreating them.

## Components

Pass a component class to `h`, with props and event handlers as keyword arguments:

```python
h(
    TodoList,
    items=lambda: self.state["items"],   # bound prop (:items="items")
    title="To do",                       # static prop
    on_clicked=self.handle_complete,     # event handler (@clicked="...")
)
```

The child component subscribes to `emit`-ed events through the `on_*` handlers, exactly like with templates.

## Slots

Declare a slot in a component's view with `cg.slot`; fallback content goes inside the block:

```python
class Card(cg.Component):
    def view(self):
        with h.widget():
            with cg.slot("header"):
                h.label(text="fallback header")
            cg.slot()  # the "default" slot
```

Provide content from the parent with `cg.fill` (the equivalent of `<template v-slot:name>`). Content placed directly inside a component element goes to the default slot:

```python
with h(Card):
    with cg.fill("header"):
        h.label(text="header content")
    h.label(text="this goes into the default slot")
```

## Template refs

The `ref` attribute works the same as in templates:

```python
h.lineedit(ref="input")
```

After mounting, the element (or component instance) is available as `self.refs["input"]`.

## Dynamic components

`cg.dynamic` is the equivalent of `<component :is="...">`. The callable returns a component class (or tag string) and the element is swapped out reactively when the value changes:

```python
cg.dynamic(lambda: self.state["active_view"], items=lambda: self.state["items"])
```

## A common pitfall: eager reads

Reading state or props *directly* in view code — instead of inside a lambda — bakes the value in statically:

```python
def view(self):
    h.label(text=f"Count: {self.state['count']}")  # ⚠ never updates!
```

Collagraph detects this and emits a warning pointing out the fix:

```
UserWarning: Reactive value read during view build: ...
Reads of state/props directly in view code are evaluated only once and
will not update. Wrap the expression in a lambda to make it reactive.
```

The same applies inside `each` item functions: `h.label(text=item())` is an eager read, `h.label(text=lambda: item())` (or simply `h.label(text=item)`) is a live binding.

## Template to Python cheat sheet

| Template | Python view |
|---|---|
| `<label text="x" />` | `h.label(text="x")` |
| `<label :text="expr" />` | `h.label(text=lambda: expr)` |
| `v-bind="attrs"` | `h.label(bind=lambda: attrs)` |
| `@clicked="handler"` | `h.button(on_clicked=handler)` |
| `<label>{{ expr }}</label>` | `h.label(lambda: expr)` |
| `v-if` / `v-else-if` / `v-else` | `with cg.when(...)` / `cg.elif_(...)` / `cg.otherwise()` |
| `v-for="item in items"` + `:key` | `@cg.each(lambda: items, key=...)` |
| `<MyComponent :prop="expr" />` | `h(MyComponent, prop=lambda: expr)` |
| `<slot name="x">fallback</slot>` | `with cg.slot("x"): ...` |
| `<template v-slot:x>` | `with cg.fill("x"): ...` |
| `ref="name"` | `h.label(ref="name")` |
| `<component :is="expr" />` | `cg.dynamic(lambda: expr)` |

## Examples

Runnable examples using Python views can be found in the repository:

```sh
uv run python examples/pyside/counter_view.py
uv run python examples/pyside/todo_view.py
```
