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
import random

import pygfx as gfx
from wgpu.gui.auto import run, WgpuCanvas

from collagraph import Collagraph, create_element as h, EventLoopType
from collagraph.renderers import PygfxRenderer


class SelectableObjectsCanvas(WgpuCanvas):
    def _object_under_pointer(self, event):
        info = renderer.get_pick_info((event["x"], event["y"]))
        return info["world_object"]

    def handle_click(self, event):
        if wobject := self._object_under_pointer(event):
            if handle_event := getattr(wobject, "handle_event", None):
                handle_event({"event_type": "click"})

    def handle_move(self, event):
        if wobject := self._object_under_pointer(event):
            if handle_event := getattr(wobject, "handle_event", None):
                handle_event({"event_type": "hover"})


sphere_geom = gfx.sphere_geometry(radius=0.5)
materials = {
    "default": gfx.MeshPhongMaterial(color=[1, 1, 1]),
    "selected": gfx.MeshPhongMaterial(color=[1, 0, 0]),
    "hovered": gfx.MeshPhongMaterial(color=[1, 0.6, 0]),
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
                "onClick": lambda event: set_selected(index),
                "onHover": lambda event: set_hovered(index),
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


def Landmark(props):
    props.setdefault("selected", False)

    def toggle():
        props["selected"] = not props["selected"]

    return h(
        "Group",
        props,
        h(
            "Point",
            {
                "scale": [2 if props["selected"] else 1] * 3,
                "color": [1, 0.5, 0, 0.1],
            },
        ),
        h(
            "Point",
            {
                "scale": [0.5, 0.5, 0.5],
                "color": [1, 1, 1, 1],
                "onClick": lambda event: toggle(),
            },
        ),
    )


if __name__ == "__main__":
    canvas = SelectableObjectsCanvas(size=(600, 400))
    canvas.add_event_handler(canvas.handle_move, "pointer_move")
    canvas.add_event_handler(canvas.handle_click, "pointer_down")
    # Newer releases of pygfx don't need the following patch for Qt autogui
    try:
        canvas.setMouseTracking(True)
        canvas._subwidget.setMouseTracking(True)
    except ValueError:
        pass
    renderer = gfx.renderers.WgpuRenderer(canvas)
    camera = gfx.PerspectiveCamera(60, 16 / 9)
    camera.position.z = 15

    controls = gfx.OrbitControls(camera.position.clone())
    controls.add_default_event_handlers(canvas, camera)

    gui = Collagraph(renderer=PygfxRenderer(), event_loop_type=EventLoopType.QT)

    # Should be possible to create this element
    # by rendering JSX to dict.
    # Jinja supports rendering templates to Python objects
    # so could be an interesting starting place.
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
            # {"count": 20},
        ),
        h(
            Landmark,
            {
                "name": "funk",
            },
        ),
        h(
            Landmark,
            {
                "position": [4, 4, -4],
            },
        ),
        h(
            "Point",
            {
                "name": "Hip",
                "position": [2, 2, 2],
                "color": [1, 0.4, 0],
            },
        ),
        h(
            "Point",
            {
                "name": "Hap",
                "position": [-2, 0, -6],
                "color": [0.8, 1, 0],
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
