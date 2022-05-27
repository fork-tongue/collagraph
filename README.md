[![PyPI version](https://badge.fury.io/py/collagraph.svg)](https://badge.fury.io/py/collagraph)
[![CI status](https://github.com/fork-tongue/collagraph/workflows/CI/badge.svg)](https://github.com/fork-tongue/collagraph/actions)

# Collagraph 📓

Reactive user interfaces.

> The word [Collagraphy](https://en.wikipedia.org/wiki/Collagraphy) is derived from the Greek word _koll_ or _kolla_, meaning glue, and graph, meaning the activity of drawing.

Inspired by Vue and React.


## Features

Write your Python interfaces in a declarative manner with plain render functions, component classes or even single-file components using Vue-like syntax, but with Python!

* Reactivity (made possible by leveraging [observ](https://github.com/fork-tongue/observ))
* Function components
* Class components with local state and life-cycle methods/hooks
* Single-file components with Vue-like syntax (`.cgx` files)
* Custom renderers

Here is an example that shows a simple counter, made with a function component:

```python
from PySide6 import QtWidgets
from observ import reactive
import collagraph as cg

# Declare some reactive state
state = reactive({"count": 0})

# Define function that adjusts the state
def bump():
    state["count"] += 1

# Declare how the state should be rendered
def Counter(props):
    return cg.h(
        "widget",
        {},
        cg.h("label", {"text": f"Count: {props['count']}"}),
        cg.h("button", {"text": "Bump", "on_clicked": bump}),
    )

# Create a Collagraph instance with a PySide renderer 
# and register with the Qt event loop
gui = cg.Collagraph(
    renderer=cg.PySideRenderer(),
    event_loop_type=cg.EventLoopType.QT,
)
# Render the function component into a container 
# (in this case the app but can be another widget)
app = QtWidgets.QApplication()
gui.render(cg.h(Counter, state), app)
app.exec()
```

For more examples, please take a look at the [examples folder](examples).

Currently there are two renderers:

* [PysideRenderer](collagraph/renderers/pyside_renderer.py): for rendering PySide6 applications
* [PygfxRenderer](collagraph/renderers/pygfx_renderer.py): for rendering 3D graphic scenes with [Pygfx](https://github.com/pygfx/pygfx)

It is possible to create a custom Renderer using the [Renderer](collagraph/renderers/__init__.py) interface, to render to other UI frameworks, for instance wxPython, or even the browser DOM.
