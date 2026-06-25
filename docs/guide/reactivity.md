# Reactivity

Collagraph uses fine-grained reactivity powered by [observ](https://github.com/fork-tongue/observ). This is different from Vue's virtual DOM approach -- instead of diffing entire trees, reactive watchers track dependencies and directly update only what changed.

## How It Works

1. `self.state` is a **reactive dictionary** (from `observ`)
2. When a template expression reads from state, a dependency is recorded
3. When state changes, only the expressions that depend on it are re-evaluated
4. The renderer updates only the affected elements

```python
class Counter(cg.Component):
    def init(self):
        self.state["count"] = 0

    def increment(self):
        # This triggers re-evaluation of any binding that reads "count"
        self.state["count"] += 1
```

## Reactive Collections

State supports reactive lists and nested dicts:

```python
class TodoApp(cg.Component):
    def init(self):
        self.state["items"] = ["Buy milk", "Write docs"]

    def add(self, item):
        # Appending to a reactive list triggers updates
        self.state["items"].append(item)

    def remove(self, index):
        del self.state["items"][index]
```

## Props Are Read-Only

Props use `readonly()` from observ. They can be observed for changes but cannot be mutated by the child component:

```python
# This will raise an error:
self.props["name"] = "new value"
```

## What Triggers Updates

- Assigning to `self.state[key]`
- Mutating reactive collections (`.append()`, `.remove()`, `del`, etc.)
- Any in-place modification of reactive objects

## What Does NOT Trigger Updates

- Assigning to `self.some_attr` (regular instance attributes are not reactive)
- Replacing `self.state` entirely (the property prevents this)
- Mutating objects that were not created as part of state
