# Events

Components communicate upward through events, similar to [Vue's Component Events](https://vuejs.org/guide/components/events.html).

## Listening to Events

Use `@` to listen to events on elements or child components:

```html
<button @clicked="handle_click" />
<MyComponent @update="handle_update" />
```

## Emitting Events

Use `self.emit()` to fire custom events from a child component:

```python
class TodoItem(cg.Component):
    def complete(self):
        self.emit("completed", self.props["item"])
```

Parent listens:

```html
<TodoItem :item="item" @completed="handle_complete" />
```

```python
class TodoApp(cg.Component):
    def handle_complete(self, item):
        self.state["items"].remove(item)
```

## Event Arguments

Events can pass any number of arguments:

```python
# Emitting
self.emit("resize", width, height)

# Handling
def handle_resize(self, width, height):
    self.state["size"] = (width, height)
```

## Native Widget Events

For PySide6 widgets, event names correspond to Qt signals:

```html
<button @clicked="on_click" />
<lineedit @text_edited="on_text" />
<slider @value_changed="on_value" />
```

For Pygfx objects, use pygfx event names:

```html
<mesh @pointer_enter="on_enter" @pointer_leave="on_leave" />
```
