"""
Example of how to render lists, tables and trees.
"""

import pygfx as gfx
from observ import reactive
from point_cloud import PointCloud, materials
from PySide6 import QtWidgets
from wgpu.gui.qt import WgpuCanvas

import collagraph as cg
from collagraph import h


class RenderWidget(cg.Component):
    def mounted(self):
        renderer = gfx.renderers.WgpuRenderer(self.element)

        camera = gfx.PerspectiveCamera(60, 16 / 9)
        camera.local.z = 15
        camera.show_pos((0, 0, 0))

        controls = gfx.OrbitController(camera)
        controls.register_events(renderer)

        self.gui = cg.Collagraph(renderer=cg.PygfxRenderer())
        element = h(
            "Group",
            {
                "name": "Landmarks",
            },
            h("AmbientLight"),
            h("PointLight"),
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
                    "geometry": gfx.sphere_geometry(),
                    "material": materials["other"],
                    "name": "Hip",
                    "local.position": [2, 2, 2],
                },
            ),
        )

        container = gfx.Scene()

        def animate():
            renderer.render(container, camera)

        self.gui.renderer.add_on_change_handler(lambda: self.element.request_draw(animate))
        self.gui.render(element, container)

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
    renderer.register_element("WgpuCanvas", WgpuCanvas)
    gui = cg.Collagraph(renderer=renderer)

    state = reactive({"count": 1000})

    # Define Qt structure and map state to the structure
    element = h(Example, state)

    # Pass in the app as a container. Can actually be any truthy object
    gui.render(element, app)
    app.exec()
