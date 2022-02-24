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
import pygui
from wgpu.gui.auto import run, WgpuCanvas


class MyCanvas(WgpuCanvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_event = None

    def handle_event(self, event):
        if event["event_type"] == "pointer_down":
            self.last_event = event
        elif event["event_type"] == "pointer_up" and self.last_event:
            has_moved = (
                self.last_event["x"] != event["x"] or self.last_event["y"] != event["y"]
            )
            if not has_moved:
                info = renderer.get_pick_info((event["x"], event["y"]))
                wobject = info["world_object"]
                if wobject:
                    if handle_event := getattr(wobject, "handle_event", None):
                        handle_event({"event_type": "click"})
            self.last_event = None

        super().handle_event(event)


sphere_geom = gfx.sphere_geometry(radius=0.5)
materials = {
    False: gfx.MeshPhongMaterial(color=[1, 1, 1]),
    True: gfx.MeshPhongMaterial(color=[1, 0, 0]),
}


def PointCloud(props):
    random.seed(0)

    def random_point(index, selected):
        return pygui.create_element(
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
                # "color": [1, 0, 0] if index == selected else [1, 1, 1],
                "onClick": lambda event: set_state(lambda state: {"selected": index}),
            },
        )

    state, set_state = pygui.use_state({"selected": -1})
    selected = state["selected"]
    number_of_points = props.get("count", 50)

    return pygui.create_element(
        "Group",
        props,
        *[random_point(i, selected) for i in range(number_of_points)],
    )


def Landmark(props):
    state, set_state = pygui.use_state({"selected": False})
    return pygui.create_element(
        "Group",
        props,
        pygui.create_element(
            "Point",
            {
                "scale": [2 if state["selected"] else 1] * 3,
                "color": [1, 0.5, 0, 0.1],
            },
        ),
        pygui.create_element(
            "Point",
            {
                "scale": [0.5, 0.5, 0.5],
                "color": [1, 1, 1, 1],
                "onClick": lambda event: set_state(
                    lambda state: {"selected": not state["selected"]}
                ),
            },
        ),
    )


if __name__ == "__main__":
    canvas = MyCanvas(size=(600, 400))
    renderer = gfx.renderers.WgpuRenderer(canvas)
    camera = gfx.PerspectiveCamera(70, 16 / 9)
    camera.position.z = 15

    controls = gfx.OrbitControls(camera.position.clone())
    controls.add_default_event_handlers(canvas, camera)

    # Should be possible to create this element
    # by rendering JSX to dict...
    element = pygui.create_element(
        "Group",
        {
            "name": "Landmarks",
        },
        pygui.create_element(
            PointCloud,
            {"count": 50},
        ),
        pygui.create_element(
            Landmark,
            {
                "name": "funk",
            },
        ),
        pygui.create_element(
            Landmark,
            {
                "position": [4, 4, -4],
            },
        ),
        pygui.create_element(
            "Point",
            {
                "name": "Hip",
                "position": [2, 2, 2],
                "color": [1, 0, 0],
            },
        ),
        pygui.create_element(
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

    pygui.render(element, container, callback=lambda: canvas.request_draw(animate))
    canvas.request_draw(animate)
    run()
