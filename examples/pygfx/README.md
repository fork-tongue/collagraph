# Points

## Basic example

```shell
uv run collagraph --renderer pygfx examples/pygfx/pygfx-component.cgx
```
Shows a simple sphere that changes material when hovered (notice the `pick_write=True` in the material instantiate call). This also shows how to run a component file directly with collagraph cli.


## Point cloud example

```shell
uv run collagraph --renderer pygfx --state '{"count": 100}' examples/pygfx/point_cloud.cgx
```
Shows a point cloud. Adjust the count to see how far you can push it.


## Component example

```shell
uv run python examples/pygfx/component-example.py
```
Shows a 'numberpad' with pads you can click, which will be highlighted for a bit and then turn back to their normal state again with a timer. The timer is set with `call_later` in `button.cgx`.


## Combined example

```shell
uv run python examples/pygfx/combined-example.py
```
Shows how to integrate a canvas drawn with Pygfx renderer into a PySide app.

The `PySideRenderer` in `combined-example.py` registers the `WgpuCanvas` class so that the renderer knows which class to create for a `<wgpucanvas />` element.
The `render_widget.cgx` component instantiates a `PygfxRenderer` that renders the point cloud example into a `Scene` object. Note that the amount of points can now be adjusted with the buttons in PySide.
