# Component API

## `collagraph.Component`

Base class for all components.

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `props` | `readonly(dict)` | Read-only incoming props from parent |
| `state` | `reactive(dict)` | Reactive local state |
| `refs` | `reactive(dict)` | Template refs (elements/components) |
| `element` | varies | The root platform element |
| `parent` | `Component \| None` | Parent component (None for root) |

### Lifecycle Hooks

#### `init()`

Called after `__init__` completes. Use this to initialize state:

```python
def init(self):
    self.state["count"] = 0
    self.state["items"] = []
```

#### `mounted()`

Called after the component and all its children are mounted in the element tree:

```python
def mounted(self):
    # Safe to access self.element and self.refs here
    self.refs["input"].setFocus()
```

#### `updated()`

Called after the component's DOM tree has been updated due to a reactive state change:

```python
def updated(self):
    # Called after children's updated() hooks
    pass
```

#### `before_unmount()`

Called right before the component is removed. Clean up side effects here:

```python
def before_unmount(self):
    self.timer.stop()
```

### Methods

#### `emit(event, *args, **kwargs)`

Emit a custom event to the parent component:

```python
self.emit("submit", form_data)
self.emit("resize", width, height)
```

#### `provide(key, value)`

Make a value available to all descendant components:

```python
self.provide("theme", "dark")
self.provide("api_client", client)
```

#### `inject(key, default=None)`

Retrieve a value provided by an ancestor component:

```python
theme = self.inject("theme", "light")
```

#### `render(renderer) -> ComponentFragment`

Abstract method. Normally generated automatically from the `.cgx` template. Only override this for pure-Python components (no template):

```python
def render(self, renderer):
    from collagraph.fragment import Fragment, ComponentFragment

    component = ComponentFragment(renderer)
    el = Fragment(renderer, tag="label", parent=component)
    el.set_attribute("text", "Hello")
    return component
```
