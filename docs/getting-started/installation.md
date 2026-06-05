# Installation

## Requirements

- Python 3.10 or later
- At least one renderer backend (PySide6 or Pygfx)

## Install with pip

```sh
# Desktop apps (PySide6)
pip install collagraph[pyside]

# 3D graphics (Pygfx)
pip install collagraph[pygfx]

# Both
pip install collagraph[pyside,pygfx]
```

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
