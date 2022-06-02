"""
Followed the following guide:
https://pomb.us/build-your-own-react/
and implemented it in Python.

Example 'React' code:

<Group name="Landmarks">
  <Point name="Hip" position="[1, 1, 1]" />
</Group>

This can be transpiled to a tree of 'VNodes'.
Instead of JSX/Vue template, this could also be just creating
the tree of VNodes 'manually'.
VNodes are essentially a description of the to-be-displayed item.

1. Create tree of VNodes
2. Render the tree (see __init__.py)
    - Split up the work in smaller chunks (node-by-node)
    - Build up a 'work-in-progress' tree of 'fibers'
    - Once it is ready, compare this tree with the 'current' tree (reconciliation)
    - The renderer that is called during reconciliation creates the actual 'dom' nodes,
      so a PygfxRenderer for instance would know how to reconcile a tree of pygfx
      objects.

"""
from point_cloud import materials, PointCloud, sphere_geom
import pygfx as gfx
from wgpu.gui.auto import run, WgpuCanvas

import collagraph as cg
from collagraph import h


if __name__ == "__main__":
    canvas = WgpuCanvas(size=(600, 400))
    renderer = gfx.renderers.WgpuRenderer(canvas)

    camera = gfx.PerspectiveCamera(60, 16 / 9)
    camera.position.z = 15

    controls = gfx.OrbitController(camera.position.clone())
    controls.add_default_event_handlers(renderer, camera)

    gui = cg.Collagraph(
        renderer=cg.PygfxRenderer(),
        event_loop_type=cg.EventLoopType.QT,
    )

    element = h(
        "Group",
        {
            "name": "Landmarks",
        },
        h(
            PointCloud,
            # When increasing this number, it will take longer
            # and longer for pygfx to create the render pipeline
            # (compiling shaders and such), so be careful...
            {"count": 50},
        ),
        h(
            "Mesh",
            {
                "name": "Hip",
                "position": [2, 2, 2],
                "geometry": sphere_geom,
                "material": materials["other"],
            },
        ),
    )

    container = gfx.Scene()

    def animate():
        controls.update_camera(camera)
        renderer.render(container, camera)

    gui.render(element, container, callback=lambda: canvas.request_draw(animate))
    canvas.request_draw(animate)
    run()
