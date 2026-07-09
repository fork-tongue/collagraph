# CLI

Collagraph includes a CLI to run components directly without writing a Python entry point.

## Usage

```sh
collagraph [OPTIONS] <component>
```

Or with uv:

```sh
uv run collagraph [OPTIONS] <component>
```

The component can be a `.cgx` file or a `.py` module containing a [Python view](../guide/python-views.md) component. When a `.py` module defines multiple view components, select one by appending the class name:

```sh
uv run collagraph examples/pyside/todo_view.py:TodoApp
```

Alternatively, a module can mark its root component by assigning `__component_class = MyComponent` at module level.

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--renderer {pyside,pygfx,dict}` | `pyside` | Renderer to use |
| `--state <json>` | - | Initial state as JSON string or path to JSON file |
| `--hot-reload`, `-H` | off | Enable hot reload (auto-update on file changes) |
| `--show-code` | off | Pretty print the compiled Python code for the component and exit (`.cgx` only) |

## Examples

```sh
# Run a PySide component
uv run collagraph examples/pyside/counter.cgx

# Run a Python view component
uv run collagraph examples/pyside/counter_view.py

# Run a Pygfx component
uv run collagraph --renderer pygfx examples/pygfx/pygfx-component.cgx

# Run with initial state
uv run collagraph --state '{"name": "World"}' hello.cgx

# Run with hot reload
uv run collagraph -H examples/pyside/counter.cgx

# Inspect the Python code that is compiled for a component
uv run collagraph --show-code examples/pyside/counter.cgx
```

## Debugging Compiled Components

Templates are compiled to Python render methods. Besides `--show-code`, you can set the `CGX_DEBUG` environment variable to have the generated source written to a temporary file that is used as the compile filename. Debuggers (pdb, PyCharm, VS Code) can then step through the generated render methods with correct source display:

```sh
CGX_DEBUG=1 uv run collagraph examples/pyside/counter.cgx
```
