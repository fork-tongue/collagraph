# Pygfx Examples

These examples demonstrate 3D scene rendering with Pygfx. Run them with:

```sh
uv run collagraph --renderer pygfx examples/pygfx/<file>.cgx
```

## Interactive Sphere

A sphere that changes color on hover:

```html title="pygfx-component.cgx"
<group>
  <ambient-light />
  <directional-light />
  <mesh
    :material="material()"
    :geometry="sphere"
    @pointer_enter="lambda ev: hover(True)"
    @pointer_leave="lambda ev: hover(False)"
  />
</group>

<script>
import pygfx as gfx
import collagraph as cg

sphere = gfx.sphere_geometry(radius=3)
red = gfx.MeshPhongMaterial(color=(1, 0.2, 0.2), pick_write=True)
blue = gfx.MeshPhongMaterial(color=(0.2, 0.4, 1.0), pick_write=True)

class Ball(cg.Component):
    def material(self):
        hovered = self.state.get("hovered", False)
        return red if hovered else blue

    def hover(self, hover):
        self.state["hovered"] = hover
</script>
```

## Point Cloud

A dynamic point cloud with selection and hover state. Uses `v-for` to render multiple 3D objects and accepts props via CLI `--state`:

```sh
uv run collagraph --renderer pygfx --state '{"count": 100}' examples/pygfx/point_cloud.cgx
```

```html title="point_cloud.cgx"
<ambient-light />
<point-light />
<group>
  <Point
    v-for="idx, position in enumerate(positions)"
    :position="position"
    :material="'selected' if idx == selected else 'hovered' if idx == hovered else 'default'"
    :index="idx"
    @selected="set_selected"
    @hovered="set_hovered"
  />
</group>

<script>
import random
import pygfx as gfx
import collagraph
from observ import watch
from point import Point

class PointCloud(collagraph.Component):
    def init(self):
        self.state["positions"] = []
        self.state["hovered"] = -1
        self.state["selected"] = -1

        self.watchers = {}
        self.watchers["count"] = watch(
            lambda: self.props["count"],
            self.update_positions,
            immediate=True,
        )

    def update_positions(self):
        new_count = self.props["count"]
        old_count = len(self.state["positions"])
        if new_count > old_count:
            self.state["positions"].extend(
                [(random.randint(-20, 20), random.randint(-20, 20), random.randint(-20, 20))
                 for _ in range(new_count - old_count)]
            )
        elif new_count < old_count:
            del self.state["positions"][0:old_count - new_count]

    def set_hovered(self, index):
        self.state["hovered"] = index

    def set_selected(self, index):
        if self.state["selected"] == index:
            self.state["selected"] = -1
        else:
            self.state["selected"] = index
</script>
```

## Combined PySide + Pygfx

You can embed a Pygfx canvas inside a PySide6 application. See [`examples/pygfx/combined-example.py`](https://github.com/fork-tongue/collagraph/tree/master/examples/pygfx/combined-example.py) for a full example of rendering 3D content within a Qt widget layout.

## More Examples

See the [`examples/pygfx/`](https://github.com/fork-tongue/collagraph/tree/master/examples/pygfx) directory for:

- `point.cgx` -- Individual point component with hover/select
- `button.cgx` / `numberpad.cgx` -- Reusable 3D UI components
- `component-example.py` -- Pygfx with timer-based interaction
- `render_widget.cgx` -- Wrapping PygfxRenderer inside a PySide widget
