# Hot Reload

Collagraph supports hot reload for development: edit a `.cgx` file or a [Python view](python-views.md) component and the running application updates without restarting.

## Enabling Hot Reload

### Via CLI

```sh
uv run collagraph -H my_component.cgx
```

### Programmatically

```python
gui = cg.Collagraph(renderer=cg.PySideRenderer(), hot_reload=True)
```

## How It Works

1. A file watcher (powered by [watchdog](https://github.com/gorakhargosh/watchdog)) monitors the `.cgx` files and Python view component modules used in the component tree
2. When a file changes, its module is recompiled/reimported
3. All instances of its components are re-rendered with their current state preserved
4. Renderer-specific state (e.g., window geometry) is saved and restored

## Python View Components

Hot reload also works for components that use the [view API](python-views.md) instead of a template. Any `.py` module that defines a view component used in the tree is watched. Since these run as regular Python scripts, enable hot reload programmatically:

```python
if __name__ == "__main__":
    app = QtWidgets.QApplication()
    gui = cg.Collagraph(renderer=cg.PySideRenderer(), hot_reload=True)
    gui.render(Counter, app)
    app.exec()
```

This works even when the component is defined in the script you run directly (the `__main__` module): on reload, the file is re-executed under a substitute module name, so the `if __name__ == "__main__":` block does **not** run again.

## State Preservation

During hot reload:

- `self.state` is preserved across reloads
- Window positions and sizes are maintained (PySide6)
- The component tree is unmounted and remounted with the new template

## Limitations

- Changes to `init()` won't re-run (state is preserved, not re-initialized)
- Structural changes to props may require a manual restart
- Plain Python modules are only watched when they define a view component (a `Component` subclass with a `view` method); other Python code, like utility modules, won't trigger a reload
