# Template Syntax

Collagraph uses a Vue-inspired template syntax. If you know Vue, you already know most of this. The key difference is that all expressions are **Python** instead of JavaScript.

For full Vue template syntax documentation, see: [Vue Template Syntax](https://vuejs.org/guide/essentials/template-syntax.html)

## File Format

A `.cgx` file has a template section and a `<script>` section:

```html
<div>
  <!-- template here -->
</div>

<script>
import collagraph as cg

class MyComponent(cg.Component):
    pass
</script>
```

The template is everything outside the `<script>` tag. Unlike Vue, there's no `<template>` wrapper needed.

### Multiple Root Nodes

Unlike Vue 2 (but like Vue 3), collagraph supports **multiple root nodes** in a template. There's no need to wrap everything in a single container element:

```html
<label text="First" />
<label text="Second" />
<button text="Third" />

<script>
import collagraph as cg

class Multi(cg.Component):
    pass
</script>
```

## Text Interpolation

Elements can contain text content, with double curly braces for dynamic expressions:

```html
<text>Hello, {{ name }}!</text>
<text>{{ count }} items remaining</text>
```

Expressions inside `{{ }}` are evaluated as Python. Static and dynamic parts can be mixed freely, and multiline text is normalized (leading indentation after line breaks is stripped). To render literal braces, escape them with a backslash: `\{{`.

!!! note "Renderer support"
    Text content requires the renderer to support text elements. The Pygfx renderer supports it inside `<text>` elements. The PySide6 renderer supports it inside widgets that display text, such as `<label>` and `<button>` (see [PySide6 Renderer](../renderers/pyside.md#text-content)):

    ```html
    <label>Hello, {{ name }}!</label>
    <button @clicked="bump">bump</button>
    ```

    For other Qt widgets, set text via the `text` attribute instead:

    ```html
    <lineedit :text="f'Hello, {name}'" />
    ```

## Attribute Binding

Static attributes:

```html
<button text="Click me" />
```

Dynamic attributes (prefix with `:`):

```html
<label :text="f'Count: {count}'" />
<button :enabled="items > 0" />
```

The expression after `:` is evaluated as Python. See [Vue Attribute Bindings](https://vuejs.org/guide/essentials/template-syntax.html#attribute-bindings) for the concept.

## Event Handling

Prefix with `@`:

```html
<button @clicked="handle_click" />
<lineedit @text_edited="handle_change" />
```

You can use inline expressions:

```html
<button @clicked="lambda: set_count(count + 1)" />
```

See [Vue Event Handling](https://vuejs.org/guide/essentials/event-handling.html) for the concept.

## Conditional Rendering

```html
<label v-if="show" text="Visible" />
<label v-else text="Hidden" />
```

With `v-else-if`:

```html
<label v-if="status == 'loading'" text="Loading..." />
<label v-else-if="status == 'error'" text="Error!" />
<label v-else text="Done" />
```

See [Vue Conditional Rendering](https://vuejs.org/guide/essentials/conditional.html).

## List Rendering

```html
<label v-for="item in items" :key="item" :text="item" />
```

With index:

```html
<label v-for="(item, index) in items" :key="index" :text="f'{index}: {item}'" />
```

See [Vue List Rendering](https://vuejs.org/guide/essentials/list.html).

## Component Usage

Import and use components by their class name:

```html
<TodoList :items="items" @clicked="handle_complete" />

<script>
from todo_list import TodoList
import collagraph as cg

class App(cg.Component):
    pass
</script>
```

Component names in templates use PascalCase.

## Slots

Define where child content goes:

```html
<!-- Card.cgx -->
<widget>
  <slot />
</widget>
```

Provide content to slots:

```html
<Card>
  <label text="I go in the default slot" />
</Card>
```

Named slots:

```html
<!-- Layout.cgx -->
<widget>
  <slot name="header" />
  <slot />
  <slot name="footer" />
</widget>

<!-- Usage -->
<Layout>
  <label slot="header" text="Header" />
  <label text="Body content" />
  <label slot="footer" text="Footer" />
</Layout>
```

## Comments

HTML comments are supported:

```html
<!-- This is a comment -->
<label text="visible" />
```
