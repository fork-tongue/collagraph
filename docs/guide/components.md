# Components

Components are the building blocks of a collagraph application. Each component is a Python class that extends `cg.Component`.

## Structure

A component has:

- **Props** -- read-only data passed from a parent component
- **State** -- reactive local data
- **Lifecycle hooks** -- methods called at specific points in the component's life
- **Methods** -- callable from templates or other methods

## Defining a Component

In a `.cgx` file:

```html
<label :text="f'Hello, {name}!'" />

<script>
import collagraph as cg

class Greeting(cg.Component):
    pass
</script>
```

The class name becomes the component's name. Props are received automatically from the parent.

## Props

Props are passed from parent components via attributes:

```html
<!-- Parent template -->
<Greeting name="World" :count="items" />
```

Access them in the component via `self.props`:

```python
class Greeting(cg.Component):
    def init(self):
        print(self.props["name"])  # "World"
```

Props are **read-only**. Attempting to modify them raises an error.

In templates, props are available directly by name (no `self.props` prefix needed):

```html
<label :text="name" />
```

## State

State is a reactive dictionary. Changes trigger template re-evaluation:

```python
class Counter(cg.Component):
    def init(self):
        self.state["count"] = 0

    def increment(self):
        self.state["count"] += 1  # UI updates automatically
```

In templates, state values are available directly by name:

```html
<label :text="f'Count: {count}'" />
```

## Lifecycle Hooks

| Hook | When Called |
|------|------------|
| `init()` | After component creation, before mount |
| `mounted()` | After the component and all children are mounted |
| `updated()` | After the component's DOM tree has been updated |
| `before_unmount()` | Right before the component is removed |

```python
class MyComponent(cg.Component):
    def init(self):
        self.state["data"] = []

    def mounted(self):
        # Component is now in the DOM
        pass

    def updated(self):
        # DOM was just updated
        pass

    def before_unmount(self):
        # Clean up timers, connections, etc.
        pass
```

## Template Refs

Use `ref` to get a reference to an element or child component:

```html
<lineedit ref="input" />
<button text="Focus" @clicked="focus_input" />
```

```python
class MyComponent(cg.Component):
    def focus_input(self):
        self.refs["input"].setFocus()
```

## Lookup Resolution

In templates, names are resolved in this order:

1. `self.props`
2. `self.state`
3. `self.refs`
4. Attributes/methods on `self`
5. Global/module scope

This means you can reference props, state, refs, and methods without any prefix.
