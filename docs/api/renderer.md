# Renderer API

Complete reference for the `Renderer` interface.

## Abstract Base Class

```python
from collagraph.renderers import Renderer

class MyRenderer(Renderer):
    # Implement all abstract methods
    pass
```

## Required Methods

### create_element(type: str) -> Any

Create an element of the given type.

**Parameters:**

- `type` - Element type name (e.g., "button", "mesh")

**Returns:** Platform-specific element object

**Example:**
```python
def create_element(self, type: str):
    if type == "button":
        return QPushButton()
    elif type == "label":
        return QLabel()
    # ... etc
```

### insert(el: Any, parent: Any, anchor: Any = None) -> None

Insert element into parent's children.

**Parameters:**

- `el` - Element to insert
- `parent` - Parent element
- `anchor` - Optional element to insert before (for ordering)

**Notes:**

- If `anchor` is None, append to end
- If `anchor` provided, insert before it

**Example:**
```python
def insert(self, el, parent, anchor=None):
    if anchor is None:
        parent.children.append(el)
    else:
        index = parent.children.index(anchor)
        parent.children.insert(index, el)
```

### remove(el: Any, parent: Any) -> None

Remove element from parent's children.

**Parameters:**

- `el` - Element to remove
- `parent` - Parent element

**Example:**
```python
def remove(self, el, parent):
    parent.children.remove(el)
```

### set_attribute(el: Any, attr: str, value: Any) -> None

Set an attribute/property on the element.

**Parameters:**

- `el` - Target element
- `attr` - Attribute name
- `value` - Attribute value

**Example:**
```python
def set_attribute(self, el, attr, value):
    if attr == "text":
        el.setText(str(value))
    elif attr == "enabled":
        el.setEnabled(bool(value))
    # ... etc
```

### remove_attribute(el: Any, attr: str, value: Any) -> None

Remove/reset an attribute on the element.

**Parameters:**

- `el` - Target element
- `attr` - Attribute name
- `value` - Previous value (can be used to restore default)

**Example:**
```python
def remove_attribute(self, el, attr, value):
    # Restore to default value
    if attr in self._defaults.get(el, {}):
        default = self._defaults[el][attr]
        self.set_attribute(el, attr, default)
```

### add_event_listener(el: Any, event_type: str, value: Callable) -> None

Attach an event handler to the element.

**Parameters:**

- `el` - Target element
- `event_type` - Event name (e.g., "clicked", "pointer_move")
- `value` - Handler function

**Example:**
```python
def add_event_listener(self, el, event_type, value):
    if hasattr(el, event_type):
        signal = getattr(el, event_type)
        signal.connect(value)
```

### remove_event_listener(el: Any, event_type: str, value: Callable) -> None

Detach an event handler from the element.

**Parameters:**

- `el` - Target element
- `event_type` - Event name
- `value` - Handler function to remove

**Example:**
```python
def remove_event_listener(self, el, event_type, value):
    if hasattr(el, event_type):
        signal = getattr(el, event_type)
        signal.disconnect(value)
```

### create_text_element() -> Any

Create a text node element (used for text content).

**Returns:** Platform-specific text element

**Note:** Many renderers don't support text nodes (return None or raise NotImplementedError)

### set_element_text(el: Any, value: str) -> None

Set text content of a text node.

**Parameters:**

- `el` - Text element
- `value` - Text content

## Optional Methods

### preferred_event_loop_type() -> Optional[EventLoopType]

Return the preferred event loop for this renderer.

**Returns:**

- `EventLoopType.QT` - Use Qt event loop
- `EventLoopType.ASYNCIO` - Use asyncio loop
- `EventLoopType.DEFAULT` - Use default loop
- `None` - No preference

**Example:**
```python
def preferred_event_loop_type(self):
    return EventLoopType.QT
```

### register_asyncio() -> None

Register this renderer with the asyncio event loop.

Called during initialization if using asyncio integration.

## Usage Example

```python
from collagraph import Collagraph
from collagraph.renderers import PySideRenderer

# Create renderer
renderer = PySideRenderer()

# Create Collagraph instance
gui = Collagraph(renderer=renderer)

# Render component
container = create_container()
gui.render(MyComponent, container)
```

## Custom Renderer Example

```python
class CustomRenderer(Renderer):
    def create_element(self, type: str):
        return {"type": type, "attrs": {}, "children": []}

    def insert(self, el, parent, anchor=None):
        if anchor:
            idx = parent["children"].index(anchor)
            parent["children"].insert(idx, el)
        else:
            parent["children"].append(el)

    def remove(self, el, parent):
        parent["children"].remove(el)

    def set_attribute(self, el, attr, value):
        el["attrs"][attr] = value

    def remove_attribute(self, el, attr, value):
        el["attrs"].pop(attr, None)

    def add_event_listener(self, el, event_type, value):
        el["attrs"][f"on_{event_type}"] = value

    def remove_event_listener(self, el, event_type, value):
        el["attrs"].pop(f"on_{event_type}", None)

    def create_text_element(self):
        return {"type": "text", "value": ""}

    def set_element_text(self, el, value):
        el["value"] = value
```

## Performance Considerations

**Batching:** Renderers should batch updates when possible. Use the scheduler to coordinate with reactive updates.

**Caching:** Cache defaults and type information to avoid repeated lookups.

**Weak References:** Use weak references to avoid circular dependencies between elements and handlers.

**Efficient Moves:** In `insert()`, check if element is already in correct position before moving.

## Next Steps

- See [PySideRenderer implementation](../renderers/pyside.md)
- See [PygfxRenderer implementation](../renderers/pygfx.md)
- Check source code in `collagraph/renderers/`
