# PySide6 Renderer

The PySideRenderer creates Qt widgets for desktop applications.

## Element Names

Use **lowercase** element names for Qt widgets:

```
action, button, checkbox, combobox, dialogbuttonbox, dock,
groupbox, itemmodel, itemselectionmodel, label, lineedit,
menu, menubar, progressbar, radiobutton, scrollarea, slider,
spinbox, standarditem, statusbar, tabwidget, textedit, toolbar,
treeview, treewidget, treewidgetitem, widget, window
```

These are pre-mapped aliases to Qt classes:

- `<button>` → `QPushButton`
- `<label>` → `QLabel`
- `<lineedit>` → `QLineEdit`
- `<window>` → `QMainWindow`

**Important:** Capital letters or dots in element names (like `<QPushButton>` or `<My.Widget>`) are treated as **Component references**, not elements. Use lowercase names for all Qt widgets.

### Dynamic Element Types

For dynamic widget types, use the special `<component>` element with `:is`:

```xml
<component :is="widget_type" />
```

The `:is` value can be any widget type string (case-insensitive):

```python
self.widget_type = "button"    # → QPushButton
self.widget_type = "Label"     # → QLabel (normalized to lowercase)
self.widget_type = "LineEdit"  # → QLineEdit (normalized to lowercase)
```

This is useful for rendering different widget types from data.

## Basic Example

```xml
<widget>
  <label text="Hello World" />
  <button text="Click me" @clicked="on_click" />
</widget>
```

## Attributes

Attributes map to Qt properties. If a Qt widget has a property, you can set it:

```xml
<!-- QLabel properties -->
<label
  text="Label text"
  alignment="AlignCenter"
  wordWrap="True"
/>

<!-- QLineEdit properties -->
<lineedit
  :text="state['input']"
  placeholderText="Type here..."
  maxLength="50"
/>

<!-- QPushButton properties -->
<button
  text="Submit"
  :enabled="state['valid']"
  checkable="True"
/>
```

**Rule:** If `widget.setPropertyName(value)` exists in Qt, use `propertyName="value"` in the template.

## Events

Qt signals become events. Use `@` prefix:

```xml
<button @clicked="handle_click" />
<lineedit @textChanged="handle_text" />
<slider @valueChanged="handle_value" />
<checkbox @stateChanged="handle_check" />
```

Common signals:

- `clicked` - buttons
- `textChanged` - text inputs
- `valueChanged` - sliders, spinboxes
- `stateChanged` - checkboxes
- `currentIndexChanged` - comboboxes
- `triggered` - actions

## Layouts

Widgets automatically get a box layout if they have children. Control layout with the `layout` attribute:

```xml
<!-- Box layout (default) -->
<widget :layout="{'type': 'Box', 'direction': 'TopToBottom'}">
  <button text="Button 1" />
  <button text="Button 2" />
</widget>

<!-- Grid layout -->
<widget :layout="{'type': 'Grid'}">
  <label text="Name:" grid_index="(0, 0)" />
  <lineedit grid_index="(0, 1)" />
  <label text="Email:" grid_index="(1, 0)" />
  <lineedit grid_index="(1, 1)" />
</widget>

<!-- Form layout -->
<widget :layout="{'type': 'Form'}">
  <lineedit form_label="Name" />
  <lineedit form_label="Email" />
</widget>
```

Layout types:

`Box`, `Grid`, `Form`, `Stacked`

## Special Widgets

### Window (QMainWindow)

```xml
<window>
  <menubar>
    <menu title="File">
      <action text="Open" @triggered="open_file" />
      <action text="Save" @triggered="save_file" />
    </menu>
  </menubar>

  <toolbar>
    <action text="New" @triggered="new_doc" />
  </toolbar>

  <!-- Central widget -->
  <widget>
    <label text="Main content here" />
  </widget>

  <statusbar />
</window>
```

### TabWidget

```xml
<tabwidget>
  <widget tab_label="Tab 1">
    <label text="Content 1" />
  </widget>
  <widget tab_label="Tab 2" tab_index="1">
    <label text="Content 2" />
  </widget>
</tabwidget>
```

### Dock Widgets

```xml
<window>
  <dock area="LeftDockWidgetArea">
    <label text="Sidebar content" />
  </dock>

  <widget>
    <label text="Main content" />
  </widget>
</window>
```

### Tree/List Views with Models

```xml
<treeview>
  <itemmodel>
    <!-- Model will be set on the view -->
  </itemmodel>
</treeview>
```

### Combo Boxes

```xml
<combobox :items="state['options']" @currentIndexChanged="on_select" />
```

## Special Attributes

These don't map to Qt properties but have custom handling:

| Attribute | Use | Example |
|-----------|-----|---------|
| `layout` | Set widget layout | `{'type': 'Box', 'direction': 'LeftToRight'}` |
| `size` | Set widget size | `(400, 300)` |
| `tab_label` | Tab title | `"Settings"` |
| `tab_index` | Tab position | `0` |
| `grid_index` | Grid cell | `(row, col)` or `(row, col, rowspan, colspan)` |
| `form_label` | Form label | `"Username"` |
| `form_index` | Form row | `0` |
| `area` | Dock area | `"LeftDockWidgetArea"` |

## Practical Example

```xml
<window>
  <widget :layout="{'type': 'Box', 'direction': 'TopToBottom'}">
    <label text="Enter your name:" />
    <lineedit
      :text="state['name']"
      @textChanged="lambda text: state.__setitem__('name', text)"
      placeholderText="Name..."
    />
    <button
      text="Submit"
      @clicked="submit"
      :enabled="len(state['name']) > 0"
    />
  </widget>
</window>

<script>
import collagraph as cg

class MyApp(cg.Component):
    def init(self):
        self.state["name"] = ""

    def submit(self):
        print(f"Hello, {self.state['name']}!")
</script>
```

## Key Points

1. **No CSS**: Style with Qt stylesheets or native properties
2. **Use bracket notation**: `state['key']` not `state.key` for reactivity
3. **Layouts are automatic**: Widgets with children get layouts
4. **Signals as events**: Check Qt docs for available signals
5. **Property discovery**: Use Qt documentation to find property names
