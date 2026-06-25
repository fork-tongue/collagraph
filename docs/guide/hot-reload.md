# Hot Reload

Collagraph supports hot reload for development: edit a `.cgx` file and the running application updates without restarting.

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

1. A file watcher (powered by [watchdog](https://github.com/gorakhargosh/watchdog)) monitors `.cgx` files
2. When a file changes, its component is recompiled
3. All instances of that component are re-rendered with their current state preserved
4. Renderer-specific state (e.g., window geometry) is saved and restored

## State Preservation

During hot reload:

- `self.state` is preserved across reloads
- Window positions and sizes are maintained (PySide6)
- The component tree is unmounted and remounted with the new template

## Limitations

- Changes to `init()` won't re-run (state is preserved, not re-initialized)
- Structural changes to props may require a manual restart
- Only works with `.cgx` files (not plain Python component definitions)
