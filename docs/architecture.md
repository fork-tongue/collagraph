# Architecture Overview

Collagraph's architecture is built around **fine-grained reactivity** with direct DOM updates.

## Core Principle

**No Virtual DOM.** Updates are surgical and direct.

When you write:
```xml
<label :text="state['count']" />
```

This creates a watcher that:

1. Evaluates `state['count']`
2. Tracks the dependency
3. Calls `renderer.set_attribute(label, 'text', value)` immediately
4. When `state['count']` changes, repeats step 3 with new value

No diffing, no reconciliation, no comparing old vs new trees.

## Inspiration

**Svelte/Solid-style**, not React VDOM:

- Svelte: Compile-time optimized reactivity
- Solid: Fine-grained reactive primitives
- Collagraph: Runtime fine-grained reactivity via `observ` library

## Key Components

### 1. Observ Library

Provides reactive primitives:

```python
from observ import reactive, computed, watch_effect

# Reactive state
state = reactive({"count": 0})

# Computed values (memoized)
doubled = computed(lambda: state["count"] * 2)

# Side effects (watchers)
watch_effect(lambda: print(f"Count: {state['count']}"))

# Change state
state["count"] = 5  # Triggers watcher, recomputes doubled
```

**How it works:**

- `reactive()` wraps objects in proxies that track access
- When property accessed, current watcher registers dependency
- When property changes, notifies all dependent watchers
- Scheduler batches updates to avoid redundant work

### 2. Fragment System

Fragments are rendering nodes, NOT virtual DOM nodes.

**What they do:**

- Create real DOM elements via renderer
- Set up watchers for reactive attributes
- Handle mounting/unmounting
- Manage parent-child relationships

**What they don't do:**

- Store virtual trees
- Perform diffing
- Clone or patch elements

**Example flow:**
```python
# Fragment for <label :text="state['count']" />
fragment = Fragment(renderer, tag="label")

# Set reactive binding
fragment.set_bind("text", lambda: state["count"])

# On mount:
fragment.mount(parent)
  → renderer.create_element("label")
  → Creates watcher: watch_effect(lambda: renderer.set_attribute(el, "text", state["count"]))
  → renderer.insert(el, parent)
```

When `state["count"]` changes, the watcher fires and directly updates the element. No tree comparison.

### 3. Component System

Components are similar to Vue components:

```python
class Counter(Component):
    def init(self):
        self.state["count"] = 0

    def increment(self):
        self.state["count"] += 1
```

**Key differences from React:**

- No render function that returns virtual DOM
- Instead, `.cgx` template compiles to fragment creation
- State changes trigger watchers, not re-renders
- No reconciliation phase

## The Exception: Lists

Lists (v-for) are the one place where reconciliation happens:

```xml
<item v-for="item in items" :key="item['id']" />
```

**Why?**

- Items can reorder
- Need to preserve element identity
- Can't just update content in-place

**How it works:**

- Tracks fragments by key
- When list changes, diffs keys (old vs new)
- Reuses fragments with matching keys
- Moves DOM elements to new positions
- Creates/removes fragments as needed

This is similar to React's key-based reconciliation, but only for lists. Everything else is direct updates.

## Update Flow

### Single Attribute Update

```
User action
  ↓
state["count"] = 5
  ↓
Proxy intercepts assignment
  ↓
Notifies dependent watchers
  ↓
Watcher re-evaluates: state["count"]
  ↓
renderer.set_attribute(el, "text", "5")
  ↓
Element updated
```

No diffing, no tree traversal, no reconciliation.

### List Update

```
User action
  ↓
state["items"] = [...]
  ↓
ListFragment watcher triggers
  ↓
Extract keys from new list
  ↓
Diff keys: removed, added, moved
  ↓
Remove old fragments
Create new fragments
Move existing fragments
  ↓
renderer.remove() / renderer.insert()
  ↓
DOM updated
```

Only lists do diffing. Everything else is direct.

## Performance Implications

**Pros:**

- No VDOM overhead
- No diffing for simple updates
- Minimal memory usage
- Fast updates for data-driven UIs

**Cons:**

- Watchers have memory cost
- Large numbers of bindings = more watchers
- Must be careful with computed values (memoization helps)

**Best practices:**

- Use computed values for derived state
- Avoid creating reactive objects in loops
- Use `:key` for lists that reorder
- Batch state updates when possible

## Comparison

| Framework | Model | Update Method |
|-----------|-------|---------------|
| **React** | VDOM | Reconciliation, diffing |
| **Vue 2** | VDOM | Patch-based diffing |
| **Vue 3** | VDOM + Reactive | Optimized VDOM |
| **Svelte** | Compiled | Direct DOM updates (compiled) |
| **Solid** | Fine-grained | Reactive primitives |
| **Collagraph** | Fine-grained | Direct DOM via watchers |

Collagraph is closest to Solid's model: fine-grained reactive updates without VDOM.

## Summary

1. **Fine-grained reactivity** via `observ` library
2. **Direct DOM updates** via renderer, no VDOM
3. **Watchers** connect reactive state to DOM elements
4. **Lists** are the exception - they use key-based reconciliation
5. **Inspired by Svelte/Solid**, not React

This architecture enables efficient updates while maintaining a declarative component model.
