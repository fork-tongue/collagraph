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
import logging
import random

import pygfx as gfx
from wgpu.gui.auto import run, WgpuCanvas

from pygui import create_element as h, EventLoopType, PyGui
from pygui.renderers import PygfxRenderer

try:
    # If rich is available, use it to improve (traceback) logs
    from rich.logging import RichHandler
    from rich.traceback import install
    import shutil

    terminal_width = shutil.get_terminal_size((100, 20)).columns - 2
    install(width=terminal_width)

    FORMAT = "%(message)s"
    logging.basicConfig(
        level="WARN",
        format=FORMAT,
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )
except ModuleNotFoundError:
    pass


logger = logging.getLogger(__name__)


class SelectableObjectsCanvas(WgpuCanvas):
    def handle_event(self, event):
        if event["event_type"] == "pointer_down":
            info = renderer.get_pick_info((event["x"], event["y"]))
            wobject = info["world_object"]
            if wobject:
                if handle_event := getattr(wobject, "handle_event", None):
                    handle_event({"event_type": "click"})

        super().handle_event(event)


sphere_geom = gfx.sphere_geometry(radius=0.5)
materials = {
    False: gfx.MeshPhongMaterial(color=[1, 1, 1]),
    True: gfx.MeshPhongMaterial(color=[1, 0, 0]),
}


def PointCloud(props):
    random.seed(0)

    # Set some default values for props
    props.setdefault("selected", -1)
    props.setdefault("count", 50)

    def set_selected(index):
        logger.debug(f"select: {index}")
        if props["selected"] == index:
            props["selected"] = -1
        else:
            props["selected"] = index

    def random_point(index, selected):
        return h(
            "Mesh",
            {
                "geometry": sphere_geom,
                "material": materials[index == selected],
                "position": [
                    random.randint(-10, 10),
                    random.randint(-10, 10),
                    random.randint(-10, 10),
                ],
                "key": index,
                "onClick": lambda event: set_selected(index),
            },
        )

    selected = props["selected"]
    number_of_points = props["count"]

    return h(
        "Group",
        props,
        *[random_point(i, selected) for i in range(number_of_points)],
    )


def Landmark(props):
    props.setdefault("selected", False)

    def toggle():
        logger.debug("toggle")
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
    renderer = gfx.renderers.WgpuRenderer(canvas)
    camera = gfx.PerspectiveCamera(70, 16 / 9)
    camera.position.z = 15

    controls = gfx.OrbitControls(camera.position.clone())
    controls.add_default_event_handlers(canvas, camera)

    gui = PyGui(renderer=PygfxRenderer(), event_loop_type=EventLoopType.QT)

    # Should be possible to create this element
    # by rendering JSX to dict...
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
            # {"count": 200},
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
