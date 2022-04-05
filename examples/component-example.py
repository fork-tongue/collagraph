import pygfx as gfx
from wgpu.gui.auto import run, WgpuCanvas

from collagraph import Collagraph, Component, create_element as h, EventLoopType
from collagraph.renderers import PygfxRenderer


class Track(Component):
    track_geometry = gfx.cylinder_geometry()
    track_material = gfx.MeshPhongMaterial(color=[1, 0.5, 1])

    def render(self):
        return h(
            "Mesh",
            {
                **self.props,
                "geometry": Track.track_geometry,
                "material": Track.track_material,
            },
        )


class Scrubber(Component):
    scrubber_geometry = gfx.sphere_geometry()
    scrubber_material = gfx.MeshPhongMaterial(color=[0.5, 1, 0.5])

    def __init__(self, props):
        super().__init__(props)
        self._captured = False
        self._sphere = None
        self._mouse_pos = (0, 0)
        self.position = [0, 0, 0]

    def mouse_down(self, event):
        if not self._sphere:
            self._sphere = event.current_target
        self._sphere.set_pointer_capture(event.pointer_id)
        self._captured = True
        self._mouse_pos = event.x, event.y

    def mouse_move(self, event):
        if not self._captured:
            return

        pos = event.x, event.y
        diff = (
            pos[0] - self._mouse_pos[0],
            pos[1] - self._mouse_pos[1],
        )

        new_pos = [
            self.position[0],
            self.position[1],
            self.position[2] - diff[0] / 40,
        ]

        self._mouse_pos = pos
        # FIXME: updating one element of self.position doesn't update component
        self.position = new_pos

    def mouse_up(self, event):
        self._captured = False

    def render(self):
        return h(
            "Mesh",
            {
                **self.props,
                **self.state,
                "geometry": Scrubber.scrubber_geometry,
                "material": Scrubber.scrubber_material,
                "on_pointer_down": self.mouse_down,
                "on_pointer_move": self.mouse_move,
                "on_pointer_up": self.mouse_up,
            },
        )


class Slider(Component):
    def render(self):
        return h(
            "Group",
            self.state,
            h(
                Track,
                {
                    "scale": [0.5, 0.5, 10],
                },
            ),
            h(Scrubber, {}),
        )


if __name__ == "__main__":
    canvas = WgpuCanvas(size=(600, 400))
    renderer = gfx.renderers.WgpuRenderer(canvas)

    camera = gfx.PerspectiveCamera(60, 16 / 9)
    camera.position.x = 15

    controls = gfx.OrbitControls(camera.position.clone())
    controls.add_default_event_handlers(renderer, canvas, camera)

    gui = Collagraph(renderer=PygfxRenderer(), event_loop_type=EventLoopType.QT)

    # Should be possible to create this element
    # by rendering JSX to dict.
    # Jinja supports rendering templates to Python objects
    # so could be an interesting starting place.
    element = h(Slider, {})

    container = gfx.Scene()

    controls.update_camera(camera)

    def animate():
        # print(camera.rotation)
        renderer.render(container, camera)

    gui.render(element, container, callback=lambda: canvas.request_draw(animate))
    canvas.request_draw(animate)
    run()
