# Collagraph Documentation

This directory contains documentation for Collagraph, built with MkDocs.

## Building Documentation

Install documentation dependencies:
```bash
uv sync --group docs
```

Build and serve locally:
```bash
uv run mkdocs serve
```

Then open http://127.0.0.1:8000 in your browser.

Build static site:
```bash
uv run mkdocs build
```

Output will be in `site/` directory.

Deploy to GitHub Pages:
```bash
uv run mkdocs gh-deploy
```

This builds the docs and pushes to the `gh-pages` branch.

## Documentation Structure

- `index.md` - Home page and overview
- `renderers/` - Renderer-specific documentation
  - `overview.md` - General renderer concepts
  - `pyside.md` - PySide6/Qt renderer
  - `pygfx.md` - Pygfx 3D renderer
- `api/` - API reference
  - `renderer.md` - Renderer interface

## Writing Guidelines

Keep documentation:
- **Concise** - Get to the point quickly
- **Practical** - Focus on usage, not theory
- **Plain text** - Minimal formatting, mostly markdown
- **Example-driven** - Show, don't just tell
