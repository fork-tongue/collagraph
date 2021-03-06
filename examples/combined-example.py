"""
Example of how to render lists, tables and trees.
"""
from observ import reactive
from point_cloud import materials, PointCloud, sphere_geom
import pygfx as gfx
from PySide6 import QtWidgets
from wgpu.gui.qt import WgpuCanvas

import collagraph as cg
from collagraph import h


class RenderWidget(cg.Component):
    def mounted(self):
        renderer = gfx.renderers.WgpuRenderer(self.element)

        camera = gfx.PerspectiveCamera(60, 16 / 9)
        camera.position.z = 15

        controls = gfx.OrbitController(camera.position.clone())
        controls.add_default_event_handlers(renderer, camera)

        self.gui = cg.Collagraph(
            renderer=cg.PygfxRenderer(), event_loop_type=cg.EventLoopType.QT
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
                self.props,
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

        self.gui.render(
            element, container, callback=lambda: self.element.request_draw(animate)
        )

    def render(self):
        return h("WgpuCanvas", {"minimum_height": 400, "minimum_width": 600})


def Example(props):
    def add(event):
        props["count"] += 1

    def remove(event):
        if props["count"] > 0:
            props["count"] -= 1

    return h(
        "Window",
        {},
        h(
            "Widget",
            {},
            h(
                RenderWidget,
                props,
            ),
            h(
                "Widget",
                {
                    "layout": {
                        "type": "Box",
                        "direction": "LeftToRight",
                    },
                    "maximum-height": 50,
                },
                h("Button", {"text": "Add", "on_clicked": add}),
                h("Button", {"text": "Remove", "on_clicked": remove}),
            ),
        ),
    )


if __name__ == "__main__":
    app = QtWidgets.QApplication()

    renderer = cg.PySideRenderer()
    renderer.register("WgpuCanvas", WgpuCanvas)
    gui = cg.Collagraph(renderer=renderer, event_loop_type=cg.EventLoopType.QT)

    state = reactive({"count": 50})

    # Define Qt structure and map state to the structure
    element = h(Example, state)

    # Pass in the app as a container. Can actually be any truthy object
    gui.render(element, app)
    app.exec()
