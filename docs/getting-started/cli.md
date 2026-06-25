# CLI

Collagraph includes a CLI to run components directly without writing a Python entry point.

## Usage

```sh
collagraph [OPTIONS] <component.cgx>
```

Or with uv:

```sh
uv run collagraph [OPTIONS] <component.cgx>
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--renderer {pyside,pygfx,dict}` | `pyside` | Renderer to use |
| `--state <json>` | - | Initial state as JSON string or path to JSON file |
| `--hot-reload`, `-H` | off | Enable hot reload (auto-update on file changes) |

## Examples

```sh
# Run a PySide component
uv run collagraph examples/pyside/counter.cgx

# Run a Pygfx component
uv run collagraph --renderer pygfx examples/pygfx/pygfx-component.cgx

# Run with initial state
uv run collagraph --state '{"name": "World"}' hello.cgx

# Run with hot reload
uv run collagraph -H examples/pyside/counter.cgx
```
