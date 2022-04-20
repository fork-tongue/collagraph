"""
Example of how to render lists, tables and trees.
"""
import random

from observ import reactive
import pygfx as gfx
from PySide6 import QtWidgets
from wgpu.gui.qt import WgpuCanvas

from collagraph import Collagraph, create_element as h, EventLoopType
from collagraph.components import Component
from collagraph.renderers import PygfxRenderer, PySideRenderer


sphere_geom = gfx.sphere_geometry(radius=0.5)
materials = {
    "default": gfx.MeshPhongMaterial(color=[1, 1, 1]),
    "selected": gfx.MeshPhongMaterial(color=[1, 0, 0]),
    "hovered": gfx.MeshPhongMaterial(color=[1, 0.6, 0]),
    "other": gfx.MeshPhongMaterial(color=[1, 0, 0.5]),
}


def PointCloud(props):
    random.seed(0)

    # Set some default values for props
    props.setdefault("selected", -1)
    props.setdefault("hovered", -1)
    props.setdefault("count", 50)

    def set_hovered(index):
        props["hovered"] = index

    def set_selected(index):
        if props["selected"] == index:
            props["selected"] = -1
        else:
            props["selected"] = index

    def random_point(index, selected, hovered):
        material = materials["default"]
        if index == selected:
            material = materials["selected"]
        elif index == hovered:
            material = materials["hovered"]
        return h(
            "Mesh",
            {
                "geometry": sphere_geom,
                "material": material,
                "position": [
                    random.randint(-10, 10),
                    random.randint(-10, 10),
                    random.randint(-10, 10),
                ],
                "key": index,
                "on_click": lambda event: set_selected(index),
                "on_pointer_move": lambda event: set_hovered(index),
            },
        )

    selected = props["selected"]
    hovered = props["hovered"]

    number_of_points = props["count"]

    return h(
        "Group",
        props,
        *[random_point(i, selected, hovered) for i in range(number_of_points)],
    )


class RenderWidget(Component):
    def mounted(self):
        renderer = gfx.renderers.WgpuRenderer(self.element)

        camera = gfx.PerspectiveCamera(60, 16 / 9)
        camera.position.z = 15

        controls = gfx.OrbitController(camera.position.clone())
        controls.add_default_event_handlers(renderer, camera)

        self.gui = Collagraph(
            renderer=PygfxRenderer(), event_loop_type=EventLoopType.QT
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

        self.gui.render(
            element, container, callback=lambda: self.element.request_draw(animate)
        )
        self.element.request_draw(animate)

    def render(self):
        return h("WgpuCanvas", {"minimum_height": 400, "minimum_width": 600})


def Example(props):
    def add(event):
        pass

    def remove(event):
        pass

    return h(
        "Window",
        props,
        h(
            "Widget",
            {},
            h(
                RenderWidget,
                {},
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

    renderer = PySideRenderer()
    renderer.register("WgpuCanvas", WgpuCanvas)
    gui = Collagraph(renderer=renderer, event_loop_type=EventLoopType.QT)

    state = reactive({"state": []})

    # Define Qt structure and map state to the structure
    element = h(Example, state)

    # Pass in the app as a container. Can actually be any truthy object
    gui.render(element, app)
    app.exec()
