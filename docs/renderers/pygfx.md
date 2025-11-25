# Pygfx Renderer

The PygfxRenderer creates 3D graphics objects using the Pygfx library.

## What is Pygfx?

Pygfx is a modern rendering engine for Python. The PygfxRenderer allows you to build 3D scenes declaratively.

## Supported Elements

Any Pygfx WorldObject can be used. Common types:

**Scene Objects:**

- `Scene` - Root container for 3D objects
- `Group` - Container for grouping objects
- `Mesh` - 3D geometry with material

**Geometry:**

- `BoxGeometry`, `SphereGeometry`, `PlaneGeometry`
- `CylinderGeometry`, `ConeGeometry`, `TorusGeometry`

**Materials:**

- `MeshBasicMaterial`, `MeshPhongMaterial`, `MeshStandardMaterial`
- `PointsMaterial`, `LineMaterial`

**Lights:**

- `AmbientLight`, `DirectionalLight`, `PointLight`, `SpotLight`

**Cameras:**

- `PerspectiveCamera`, `OrthographicCamera`

Element names are case-insensitive: `<Mesh />`, `<mesh />`, or `<MESH />` all work.

## Basic Example

```xml
<scene>
  <ambientlight :color="(1, 1, 1, 1)" />

  <mesh
    :geometry="box_geom"
    :material="material"
    :local.position="(0, 0, -5)"
  />

  <perspectivecamera
    :local.position="(0, 0, 0)"
  />
</scene>

<script>
import collagraph as cg
import pygfx as gfx

class MyScene(cg.Component):
    def init(self):
        self.box_geom = gfx.box_geometry(1, 1, 1)
        self.material = gfx.MeshPhongMaterial(color=(1, 0, 0, 1))
</script>
```

## Attributes

### Dot Notation for Nested Properties

Use dots to access nested properties:

```xml
<!-- Transform properties -->
<mesh
  :local.position="(x, y, z)"
  :local.rotation="(x, y, z, w)"
  :local.scale="(x, y, z)"
/>

<!-- Camera properties -->
<perspectivecamera
  :fov="45"
  :local.position="(0, 0, 10)"
  :local.look_at="(0, 0, 0)"
/>

<!-- Material properties -->
<mesh
  :material.color="(r, g, b, a)"
  :material.opacity="0.5"
/>
```

### Common Attributes

**Transform (all objects):**

- `local.position` - tuple `(x, y, z)`
- `local.rotation` - quaternion `(x, y, z, w)`
- `local.scale` - tuple `(sx, sy, sz)` or scalar
- `local.matrix` - 4x4 transform matrix

**Mesh:**

- `geometry` - Pygfx geometry object
- `material` - Pygfx material object
- `visible` - boolean

**Light:**

- `color` - tuple `(r, g, b, a)` (0-1 range)
- `intensity` - float

**Camera:**

- `fov` - field of view in degrees (PerspectiveCamera)
- `zoom` - zoom factor (OrthographicCamera)

## Events

Pygfx provides pointer events:

```xml
<mesh
  @pointer_down="on_click"
  @pointer_up="on_release"
  @pointer_move="on_move"
  @pointer_enter="on_enter"
  @pointer_leave="on_leave"
  @click="on_click"
  @double_click="on_double"
/>
```

## Practical Example

```xml
<scene>
  <!-- Lighting -->
  <ambientlight :color="(0.5, 0.5, 0.5, 1)" />
  <directionallight
    :color="(1, 1, 1, 1)"
    :local.position="(1, 1, 1)"
  />

  <!-- Objects -->
  <mesh
    v-for="obj in state['objects']"
    :key="obj['id']"
    :geometry="obj['geometry']"
    :material="obj['material']"
    :local.position="obj['position']"
    @click="lambda e: select_object(obj)"
  />

  <!-- Camera -->
  <perspectivecamera
    :fov="50"
    :local.position="state['camera_pos']"
  />
</scene>

<script>
import collagraph as cg
import pygfx as gfx

class Scene3D(cg.Component):
    def init(self):
        # Create geometry (reused by all objects)
        sphere = gfx.sphere_geometry(radius=1)

        # Create objects
        self.state["objects"] = [
            {
                "id": 1,
                "geometry": sphere,
                "material": gfx.MeshPhongMaterial(color=(1, 0, 0, 1)),
                "position": (-2, 0, -5),
            },
            {
                "id": 2,
                "geometry": sphere,
                "material": gfx.MeshPhongMaterial(color=(0, 1, 0, 1)),
                "position": (0, 0, -5),
            },
            {
                "id": 3,
                "geometry": sphere,
                "material": gfx.MeshPhongMaterial(color=(0, 0, 1, 1)),
                "position": (2, 0, -5),
            },
        ]

        self.state["camera_pos"] = (0, 0, 0)

    def select_object(self, obj):
        print(f"Selected object {obj['id']}")
</script>
```

## Hierarchy

Objects follow Pygfx's scene graph structure:

```xml
<scene>
  <group :local.position="(0, 0, -5)">
    <!-- All children inherit parent's transform -->
    <mesh :local.position="(-1, 0, 0)" />  <!-- At (-1, 0, -5) in world -->
    <mesh :local.position="(1, 0, 0)" />   <!-- At (1, 0, -5) in world -->
  </group>
</scene>
```

## Key Points

1. **No 2D UI**: Pygfx is for graphics, not UI widgets
2. **Dot notation**: Access nested properties with `local.position`, `material.color`, etc.
3. **Geometry/Material refs**: Create once in component, reference in template
4. **Transforms accumulate**: Child transforms are relative to parent
5. **Coordinate system**: Right-handed, Y-up
6. **Use bracket notation**: `state['key']` for reactivity

## Integration with Canvas

The renderer needs a canvas to display. When using with Qt:

```python
from collagraph import Collagraph, EventLoopType
from collagraph.renderers import PygfxRenderer
from wgpu.gui.qt import WgpuCanvas

canvas = WgpuCanvas()
renderer = PygfxRenderer(canvas)

gui = Collagraph(
    renderer=renderer,
    event_loop_type=EventLoopType.QT,
)

root = gui.render(MyScene, canvas)
canvas.show()
```

See `examples/pygfx/` for complete examples.
