# Renderer API

The `Renderer` abstract base class defines the interface for all renderers. Implement this to render collagraph components to any UI framework.

## Abstract Methods

All abstract methods must be implemented:

### `create_element(type: str) -> Any`

Create a platform element for the given type string (from template tags).

```python
def create_element(self, type: str):
    # Map "button" -> QPushButton, "mesh" -> gfx.Mesh, etc.
    ...
```

### `create_text_element() -> Any`

Create a text node element.

### `insert(el, parent, anchor=None)`

Add `el` as a child of `parent`. If `anchor` is provided, insert before it.

### `remove(el, parent)`

Remove `el` from `parent`'s children.

### `set_element_text(el, value: str)`

Set the text content of a text element.

### `set_attribute(el, attr: str, value)`

Set attribute `attr` on element `el` to `value`.

### `remove_attribute(el, attr: str, value)`

Remove/reset attribute `attr` on element `el`.

### `add_event_listener(el, event_type: str, handler: Callable)`

Register an event handler on an element.

### `remove_event_listener(el, event_type: str, handler: Callable)`

Remove an event handler from an element.

## Optional Methods

These have default no-op implementations:

### `preferred_event_loop_type() -> EventLoopType | None`

Return the preferred event loop type for this renderer, or `None` for the default.

### `register_asyncio()`

Called when the collagraph instance sets up the asyncio event loop. Override for renderers that need custom event loop integration (e.g., Qt's asyncio policy).

### `save_element_state(el) -> dict | None`

Save renderer-specific element state for hot reload (e.g., window geometry). Return `None` if nothing to save.

### `restore_element_state(el, state: dict)`

Restore state saved by `save_element_state` after hot reload.

## Example: Minimal Custom Renderer

```python
from collagraph.renderers import Renderer

class MyRenderer(Renderer):
    def create_element(self, type):
        return {"type": type, "children": [], "attrs": {}}

    def create_text_element(self):
        return {"type": "text", "content": "", "attrs": {}}

    def insert(self, el, parent, anchor=None):
        if anchor:
            idx = parent["children"].index(anchor)
            parent["children"].insert(idx, el)
        else:
            parent["children"].append(el)

    def remove(self, el, parent):
        parent["children"].remove(el)

    def set_element_text(self, el, value):
        el["content"] = value

    def set_attribute(self, el, attr, value):
        el["attrs"][attr] = value

    def remove_attribute(self, el, attr, value):
        el["attrs"].pop(attr, None)

    def add_event_listener(self, el, event_type, handler):
        el["attrs"].setdefault("_listeners", {})[event_type] = handler

    def remove_event_listener(self, el, event_type, handler):
        el["attrs"].get("_listeners", {}).pop(event_type, None)
```

Usage:

```python
gui = cg.Collagraph(renderer=MyRenderer(), event_loop_type=cg.EventLoopType.SYNC)
container = {"type": "root", "children": [], "attrs": {}}
gui.render(MyComponent, container)
```
