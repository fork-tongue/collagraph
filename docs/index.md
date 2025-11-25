# Collagraph Documentation

Collagraph is a reactive UI framework for Python with Vue-like syntax and fine-grained reactivity inspired by Svelte and Solid.

## What is Collagraph?

Collagraph enables building declarative user interfaces with fine-grained reactivity. Unlike web frameworks, Collagraph targets:

- **Desktop applications** (PySide6/Qt)
- **2D/3D graphics** (Pygfx)

## Key Features

- Single-file components (`.cgx` files) with Vue-like syntax
- **Fine-grained reactivity** - Direct updates, no virtual DOM or diffing
- Reactive state management powered by the `observ` library
- Component-based architecture with lifecycle hooks
- Multiple renderers for different output targets
- Key-based list reconciliation for efficient list updates

## Reactivity Model

Collagraph uses **fine-grained reactivity** inspired by Svelte and Solid:

- **No virtual DOM** - Updates happen directly on elements
- **Dependency tracking** - Reactive values track their dependents
- **Surgical updates** - Only affected elements update when state changes
- **Computed values** - Automatically derive and cache computed state
- **Watchers** - React to specific state changes with side effects

This is fundamentally different from React's VDOM reconciliation or Vue 2's watcher system.

## Quick Example

```python
# counter.cgx
<widget>
  <label :text="'Count: ' + str(state['count'])" />
  <button text="Increment" @clicked="increment" />
</widget>

<script>
import collagraph as cg

class Counter(cg.Component):
    def init(self):
        self.state["count"] = 0

    def increment(self):
        self.state["count"] += 1
</script>
```

Run it:
```bash
uv run collagraph counter.cgx
```

## Architecture Overview

Collagraph uses a **renderer abstraction** that allows the same component code to target different platforms:

```
Component (.cgx file)
    ↓ (compiled to)
Python Component Class
    ↓ (renders via)
Renderer (PySide/Pygfx/etc)
    ↓ (creates)
Native Elements (Qt Widgets/3D Objects)
```

This means you write your UI logic once, and the renderer handles platform-specific details.

## No Web, No CSS

Important: Collagraph is **not** a web framework. There is:

- No HTML rendering
- No CSS styling
- No DOM in the browser sense

Instead, you work with:

- Qt widgets and their properties
- 3D objects and their transforms
- Native platform capabilities

## Next Steps

- Learn about [Renderers](renderers/overview.md)
- Explore [PySide6 rendering](renderers/pyside.md)
- Check out [Pygfx rendering](renderers/pygfx.md)
