# Installation

## Requirements

- Python 3.13 or later
- At least one renderer backend (PySide6, Pygfx or BUI)

## Install with pip

```sh
# Desktop apps (PySide6)
pip install collagraph[pyside]

# 3D graphics (Pygfx)
pip install collagraph[pygfx]

# Desktop apps with Blender's UI (BUI)
pip install collagraph[bui]

# Both PySide6 and Pygfx
pip install collagraph[pyside,pygfx]
```

!!! note
    BUI is licensed under the GPL: applications that you distribute with the
    BUI renderer have to be distributed under the terms of the GPL as well.
    See the [BUI renderer](../renderers/bui.md) page for details.

## Install with uv

```sh
uv add collagraph[pyside]
```

## Development Setup

```sh
git clone https://github.com/fork-tongue/collagraph.git
cd collagraph

# Basic dev setup
uv sync

# Full setup with all renderers
uv sync --all-groups
```
