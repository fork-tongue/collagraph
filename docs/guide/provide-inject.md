# Provide / Inject

Provide/inject allows ancestor components to share data with all descendants without passing props through every level. See [Vue Provide / Inject](https://vuejs.org/guide/components/provide-inject.html).

## Provide

Call `self.provide()` in a parent component (typically in `init()`):

```python
class App(cg.Component):
    def init(self):
        self.state["theme"] = "dark"
        self.provide("theme", self.state["theme"])
```

## Inject

Any descendant (not just direct child) can inject the value:

```python
class DeepChild(cg.Component):
    def init(self):
        theme = self.inject("theme")
        # Use theme value
```

## Default Values

`inject()` accepts a default if the key isn't provided by any ancestor:

```python
theme = self.inject("theme", "light")
```

## Use Cases

- Theme configuration
- Shared services (API clients, stores)
- Locale/i18n settings
- Anything that would be cumbersome to pass as props through many levels
