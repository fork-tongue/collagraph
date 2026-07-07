# Pygfx Renderer

The `PygfxRenderer` maps template tags to [Pygfx](https://github.com/pygfx/pygfx) 3D scene objects.

## Setup

```sh
pip install collagraph[pygfx]
```

## Running

```sh
uv run collagraph --renderer pygfx my_scene.cgx
```

Or programmatically:

```python
import pygfx as gfx
from rendercanvas.auto import RenderCanvas, loop
import collagraph as cg

canvas = RenderCanvas(size=(800, 600))
wgpu_renderer = gfx.renderers.WgpuRenderer(canvas)

camera = gfx.PerspectiveCamera(70)
camera.local.z = 15

scene = gfx.Scene()

renderer = cg.PygfxRenderer()
renderer.add_on_change_handler(lambda: canvas.request_draw(animate))

gui = cg.Collagraph(renderer=renderer)
gui.render(MyScene, scene)

def animate():
    wgpu_renderer.render(scene, camera)

loop.run()
```

## Available Elements

Tags map to Pygfx classes (case-insensitive, hyphens removed):

```html
<mesh />              <!-- gfx.Mesh -->
<group />             <!-- gfx.Group -->
<scene />             <!-- gfx.Scene -->
<points />            <!-- gfx.Points -->
<line />              <!-- gfx.Line -->
<ambient-light />     <!-- gfx.AmbientLight -->
<directional-light /> <!-- gfx.DirectionalLight -->
<point-light />       <!-- gfx.PointLight -->
```

Any class in the `pygfx` module can be used as a tag. The tag name is matched case-insensitively with hyphens and underscores stripped.

## Attributes

Attributes map directly to properties on the Pygfx object:

```html
<mesh :geometry="sphere" :material="mat" />
```

### Dot Notation

Use dot notation to set nested properties:

```html
<mesh :local.position="(1, 2, 3)" />
<mesh :local.scale="(2, 2, 2)" />
```

This traverses the object hierarchy: `mesh.local.position = (1, 2, 3)`.

## Text

`<text>` elements (`gfx.Text`) support text content directly, including `{{ }}` interpolation:

```html
<text
  :font_size="14"
  :material="label_material"
  screen_space
>
  {{ landmark['name'] }}
</text>
```

Alternatively, set the `text` or `markdown` attribute, which call `set_text()` / `set_markdown()` on the `gfx.Text` object:

```html
<text :text="label" :font_size="14" />
<text :markdown="'**bold** label'" :font_size="14" />
```

See [`examples/pygfx/landmarks.cgx`](https://github.com/fork-tongue/collagraph/tree/master/examples/pygfx/landmarks.cgx) for an interactive example with text labels.

## Events

Pygfx objects support pointer events:

```html
<mesh
  @pointer_enter="lambda ev: hover(True)"
  @pointer_leave="lambda ev: hover(False)"
  @pointer_down="handle_click"
/>
```

!!! note
    For pointer events to work, materials must have `pick_write=True`:
    ```python
    material = gfx.MeshPhongMaterial(color=(1, 0, 0), pick_write=True)
    ```

## Example

```html title="sphere.cgx"
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

## On-Change Handlers

The `PygfxRenderer` uses on-change handlers to trigger canvas redraws when the scene changes:

```python
renderer = cg.PygfxRenderer()
renderer.add_on_change_handler(lambda: canvas.request_draw(animate))
```

Every time an element is created, inserted, removed, or has an attribute changed, all registered handlers are called.
