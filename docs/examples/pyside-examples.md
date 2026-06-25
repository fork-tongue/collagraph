# PySide6 Examples

These examples demonstrate common patterns with the PySide6 renderer. Run them with:

```sh
uv run collagraph examples/pyside/<file>.cgx
```

## Counter

A minimal reactive component:

```html title="counter.cgx"
<widget>
  <label :text="f'Count: {count}'" />
  <button text="bump" @clicked="bump" />
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

## Todo App

Demonstrates list management, text input, events, and child components:

```html title="todo_example.cgx"
<window title="My First TODO app">
  <widget name="main-content">
    <label text="What do you want to do?" />
    <lineedit :text="text" @text_edited="handle_change" />
    <button text="Add" @clicked="handle_submit" />
    <label text="To do:" />
    <TodoList
      :items="items"
      @clicked="handle_complete"
    />
  </widget>
</window>

<script>
import collagraph as cg
from todo_list import TodoList

class TodoApp(cg.Component):
    def init(self):
        self.state["items"] = ["Groceries", "Laundry"]
        self.state["text"] = ""

    def handle_change(self, event):
        self.state["text"] = event

    def handle_submit(self):
        if todo := self.state["text"]:
            if todo in self.state["items"]:
                return
            self.state["items"].append(todo)
            self.state["text"] = ""

    def handle_complete(self, event):
        self.state["items"].remove(event)
</script>
```

## Layouts

Collagraph supports all standard Qt layouts:

```html title="layout_example.cgx (excerpt)"
<!-- Horizontal box layout -->
<groupbox title="Horizontal" :layout="{'type': 'Box', 'direction': 'LeftToRight'}">
  <button v-for="i in range(4)" :key="i" :text="f'Button {i}'" />
</groupbox>

<!-- Grid layout -->
<groupbox title="Grid" :layout="{'type': 'Grid'}">
  <label text="Name:" grid_index="(0, 0)" />
  <lineedit grid_index="(0, 1)" />
</groupbox>

<!-- Form layout -->
<groupbox title="Form" :layout="{'type': 'Form'}">
  <lineedit form_label="Name:" form_index="0" />
  <combobox form_label="Type:" form_index="1" />
</groupbox>
```

## Window with Menus

```html
<window>
  <menubar>
    <menu title="File">
      <action text="Open" @triggered="open_file" />
      <action separator />
      <action text="Quit" @triggered="quit" />
    </menu>
  </menubar>
  <widget>
    <!-- content -->
  </widget>
</window>
```

## More Examples

See the [`examples/pyside/`](https://github.com/fork-tongue/collagraph/tree/master/examples/pyside) directory for:

- `slider_example.cgx` -- Slider widgets
- `combobox_example.cgx` -- Dropdown menus
- `tabs_example.cgx` -- Tab widgets
- `tree_widget_example.cgx` -- Tree views
- `dialog_example.cgx` -- Dialogs
- `template_refs.cgx` -- Using template refs
- `big_list.cgx` -- Performance with large lists
