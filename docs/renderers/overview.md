# Renderer Overview

Renderers are the bridge between Collagraph components and the target platform.

## What is a Renderer?

A renderer implements the `Renderer` interface and handles:

1. **Creating elements** (widgets, graphics objects, etc.)
2. **Building hierarchies** (parent-child relationships)
3. **Setting attributes** (properties, styles, transforms)
4. **Handling events** (clicks, key presses, etc.)

## Available Renderers

| Renderer | Target | Use Case |
|----------|--------|----------|
| **PySideRenderer** | Qt/PySide6 | Desktop applications with native UI |
| **PygfxRenderer** | Pygfx | 2D/3D graphics and visualizations |
| **DictRenderer** | Python dicts | Testing and debugging |

## Renderer Interface

All renderers implement these core methods:

```python
class Renderer(ABC):
    # Element lifecycle
    def create_element(self, type: str) -> Any
    def insert(self, el: Any, parent: Any, anchor: Any = None)
    def remove(self, el: Any, parent: Any)

    # Attributes
    def set_attribute(self, el: Any, attr: str, value: Any)
    def remove_attribute(self, el: Any, attr: str, value: Any)

    # Events
    def add_event_listener(self, el: Any, event_type: str, value: Callable)
    def remove_event_listener(self, el: Any, event_type: str, value: Callable)
```

## How Renderers Work

When you write a component:

```xml
<button text="Click me" @clicked="handler" />
```

The renderer:

1. **Creates** a button element (`create_element("button")`)
2. **Sets** the text attribute (`set_attribute(button, "text", "Click me")`)
3. **Attaches** the event handler (`add_event_listener(button, "clicked", handler)`)
4. **Inserts** it into the parent (`insert(button, parent)`)

## Choosing a Renderer

**Use PySideRenderer when:**

- Building desktop applications
- Need native look and feel
- Want standard UI widgets (buttons, menus, dialogs)
- Need file dialogs, system integration

**Use PygfxRenderer when:**

- Creating visualizations
- Building 3D scenes
- Need custom graphics rendering
- Working with meshes, cameras, lights

**Use DictRenderer when:**

- Writing unit tests
- Debugging component logic
- Don't need actual rendering

## Specifying a Renderer

When running a component:

```bash
# PySide (default)
uv run collagraph myapp.cgx

# Pygfx
uv run collagraph --renderer=pygfx myapp.cgx
```

In code:

```python
from collagraph import Collagraph
from collagraph.renderers import PySideRenderer

gui = Collagraph(renderer=PySideRenderer())
gui.render(MyComponent, container)
```

## Next Steps

- [PySide6 Renderer Details](pyside.md)
- [Pygfx Renderer Details](pygfx.md)
- [Renderer API Reference](../api/renderer.md)
