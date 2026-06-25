# Renderers Overview

Collagraph uses a pluggable renderer system. The renderer is responsible for creating platform-specific elements, managing the element tree, and handling attributes and events.

## Available Renderers

| Renderer | Use Case | Install |
|----------|----------|---------|
| `PySideRenderer` | Desktop applications with Qt widgets | `collagraph[pyside]` |
| `PygfxRenderer` | 3D graphics scenes | `collagraph[pygfx]` |
| `DictRenderer` | Testing (renders to Python dicts) | included |

## Choosing a Renderer

```python
import collagraph as cg

# Desktop apps
gui = cg.Collagraph(renderer=cg.PySideRenderer())

# 3D scenes
gui = cg.Collagraph(renderer=cg.PygfxRenderer())

# Testing
gui = cg.Collagraph(renderer=cg.DictRenderer(), event_loop_type=cg.EventLoopType.SYNC)
```

## How Renderers Work

A renderer implements the `Renderer` interface:

1. **`create_element(type)`** -- maps a tag name from your template to a platform object
2. **`insert(el, parent, anchor)`** -- adds elements to the tree
3. **`remove(el, parent)`** -- removes elements
4. **`set_attribute(el, attr, value)`** -- sets properties on elements
5. **`add_event_listener(el, event, handler)`** -- connects events

The template tags you write (e.g., `<button>`, `<mesh>`) are resolved by the renderer to platform-specific objects.

## Custom Renderers

You can create a renderer for any UI framework by implementing the `Renderer` abstract base class. See the [Renderer API reference](../reference/renderer-api.md).
