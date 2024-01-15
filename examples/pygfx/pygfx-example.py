from point_cloud import materials, PointCloud, sphere_geom
import pygfx as gfx
from wgpu.gui.auto import run, WgpuCanvas

import collagraph as cg
from collagraph import h


if __name__ == "__main__":
    canvas = WgpuCanvas(size=(600, 400))
    renderer = gfx.renderers.WgpuRenderer(canvas)

    camera = gfx.PerspectiveCamera(60, 16 / 9)
    camera.local.z = 15
    camera.show_pos((0, 0, 0))

    controls = gfx.OrbitController(camera)
    controls.register_events(renderer)

    gui = cg.Collagraph(renderer=cg.PygfxRenderer())

    element = h(
        "Group",
        {
            "name": "Landmarks",
        },
        h("AmbientLight"),
        h("PointLight", {"local.position": (0, 70, 70), "cast_shadow": True}),
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
                "local.position": (2, 2, 2),
                "geometry": sphere_geom,
                "material": materials["other"],
            },
        ),
    )

    container = gfx.Scene()

    def animate():
        renderer.render(container, camera)

    gui.render(element, container, callback=lambda: canvas.request_draw(animate))
    canvas.request_draw(animate)
    run()
