# Slots

Slots let you pass template content from a parent into a child component's layout. See [Vue Slots](https://vuejs.org/guide/components/slots.html) for the concept.

## Default Slot

Define a `<slot>` in the child:

```html title="Card.cgx"
<widget>
  <label text="Card Title" />
  <slot />
</widget>
```

Provide content from the parent:

```html
<Card>
  <label text="This goes into the slot" />
</Card>
```

## Named Slots

Use `name` to define multiple slots:

```html title="Layout.cgx"
<widget>
  <slot name="header" />
  <widget>
    <slot />
  </widget>
  <slot name="footer" />
</widget>
```

Direct content to named slots with `v-slot:name` or the `#` shorthand:

```html
<!-- Using v-slot: -->
<Layout>
  <label v-slot:header text="Page Title" />
  <label text="Main content goes to default slot" />
  <label v-slot:footer text="Footer text" />
</Layout>

<!-- Using # shorthand (equivalent) -->
<Layout>
  <label #header text="Page Title" />
  <label text="Main content goes to default slot" />
  <label #footer text="Footer text" />
</Layout>
```

## Fallback Content

Slot content is optional. Define fallback content inside the `<slot>`:

```html title="Button.cgx"
<button>
  <slot>
    <label text="Default label" />
  </slot>
</button>
```

If no content is provided, the fallback is rendered.
