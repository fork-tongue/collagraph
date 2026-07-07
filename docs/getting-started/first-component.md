# First Component

A collagraph component is a `.cgx` file with a template and a script section.

## The Counter

Create a file `counter.cgx`:

```html
<widget>
  <label>Count: {{ count }}</label>
  <button @clicked="bump">bump</button>
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

Run it:

```sh
uv run collagraph counter.cgx
```

## Breakdown

### Template

The template defines what gets rendered. Each tag corresponds to a widget or element in the target renderer.

- `<widget>` -- a plain QWidget container (PySide6 renderer)
- `Count: {{ count }}` -- text content with interpolation. The expression inside `{{ }}` is evaluated as Python and updates automatically when state changes.
- `@clicked="bump"` -- an event handler. Calls the `bump` method when the button is clicked.

### Script

The `<script>` section contains a Python class that extends `cg.Component`:

- **`init()`** -- called after the component is created. Initialize `self.state` here.
- **`self.state`** -- a reactive dictionary. Changes to state automatically re-evaluate bound expressions in the template.
- **Methods** -- any method on the class can be referenced in the template.

## Running from Python

You can also render components programmatically:

```python
from PySide6 import QtWidgets
import collagraph as cg
from counter import Counter  # imports .cgx files directly

app = QtWidgets.QApplication()
gui = cg.Collagraph(renderer=cg.PySideRenderer())
gui.render(Counter, app)
app.exec()
```

After `import collagraph`, Python's import system is extended to load `.cgx` files as modules.
