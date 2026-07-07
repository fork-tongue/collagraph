# Collagraph

Reactive user interfaces in Python.

Collagraph lets you build declarative UIs using class-based components with a Vue-like single-file component syntax (`.cgx` files). It supports desktop applications via PySide6 and 3D graphics via Pygfx.

## Quick Example

```html title="counter.cgx"
<widget>
  <label>Count: {{ count }}</label>
  <button @clicked="bump">bump</button>
</widget>

<script>
import collagraph as cg

class Counter(cg.Component):
    def init(self):
        self.state["count"] = 0

    def bump(self):
        self.state["count"] += 1
</script>
```

Run it:

```sh
uv run collagraph counter.cgx
```

## Key Features

- **Reactive state** -- powered by [observ](https://github.com/fork-tongue/observ), changes to state automatically update the UI
- **Single-file components** -- Vue-like `.cgx` files with template + script
- **Multiple renderers** -- PySide6 for desktop, Pygfx for 3D scenes
- **Hot reload** -- edit components and see changes without restarting
- **Familiar syntax** -- if you know Vue, you already know most of the template syntax

## Template Syntax

Collagraph's template syntax is modelled after [Vue's template syntax](https://vuejs.org/guide/essentials/template-syntax.html). If you're familiar with Vue, the directives (`v-if`, `v-for`), bindings (`:attr`), and event handlers (`@event`) work the same way.

The key difference: collagraph templates use **Python expressions** instead of JavaScript.
