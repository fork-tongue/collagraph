# Directives Reference

Collagraph supports Vue-style directives. For full conceptual documentation, see [Vue Directives](https://vuejs.org/api/built-in-directives.html).

All directive expressions are **Python**.

## v-if / v-else-if / v-else

Conditionally render elements.

```html
<label v-if="loading" text="Loading..." />
<label v-else-if="error" :text="f'Error: {error}'" />
<label v-else text="Ready" />
```

- `v-if` evaluates its expression as a boolean
- `v-else-if` and `v-else` must immediately follow a `v-if` or `v-else-if` sibling
- Only one branch is rendered at a time

See [Vue v-if](https://vuejs.org/guide/essentials/conditional.html).

## v-for

Render a list of elements.

```html
<!-- Simple iteration -->
<label v-for="item in items" :key="item" :text="item" />

<!-- With index -->
<label v-for="(item, idx) in items" :key="idx" :text="f'{idx}. {item}'" />

<!-- Over a range -->
<label v-for="i in range(5)" :key="i" :text="f'Item {i}'" />
```

!!! warning "Always provide `:key`"
    The `:key` attribute helps collagraph identify which items changed, were added, or removed. Use a unique, stable value.

    With keys, existing elements are reused and moved into place instead of being destroyed and recreated (using a longest-increasing-subsequence algorithm to minimize moves). This also preserves widget state — such as selection and expansion in Qt tree views — across reorders.

See [Vue v-for](https://vuejs.org/guide/essentials/list.html).

## Attribute Binding (`:`)

Shorthand for dynamic attribute binding.

```html
<!-- These are equivalent -->
<label v-bind:text="name" />
<label :text="name" />
```

The expression is evaluated as Python:

```html
<button :enabled="len(items) > 0" />
<label :text="f'{count} items'" />
<widget :visible="show_panel" />
```

## Event Binding (`@`)

Shorthand for event listeners.

```html
<!-- Method reference -->
<button @clicked="handle_click" />

<!-- Inline expression -->
<button @clicked="lambda: increment(1)" />
```

## ref

Capture a reference to an element or component instance:

```html
<lineedit ref="name_input" />
```

Access via `self.refs["name_input"]` in the component class.

## slot

Direct content to a named slot in a child component. `#` is shorthand for `v-slot:`:

```html
<MyLayout>
  <label v-slot:header text="Title" />
  <label text="Body" />
  <!-- # is shorthand for v-slot: -->
  <label #footer text="Footer" />
</MyLayout>
```

## Summary Table

| Directive | Shorthand | Purpose | Vue Docs |
|-----------|-----------|---------|----------|
| `v-if` | - | Conditional rendering | [Link](https://vuejs.org/guide/essentials/conditional.html) |
| `v-else-if` | - | Else-if branch | [Link](https://vuejs.org/guide/essentials/conditional.html#v-else-if) |
| `v-else` | - | Else branch | [Link](https://vuejs.org/guide/essentials/conditional.html#v-else) |
| `v-for` | - | List rendering | [Link](https://vuejs.org/guide/essentials/list.html) |
| `v-bind:attr` | `:attr` | Dynamic attribute binding | [Link](https://vuejs.org/guide/essentials/template-syntax.html#attribute-bindings) |
| `v-on:event` | `@event` | Event listener | [Link](https://vuejs.org/guide/essentials/event-handling.html) |
| `v-slot:name` | `#name` | Named slot target | [Link](https://vuejs.org/guide/components/slots.html#named-slots) |
| `ref` | - | Template reference | [Link](https://vuejs.org/guide/essentials/template-refs.html) |
