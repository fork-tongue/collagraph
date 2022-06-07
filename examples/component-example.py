import pygfx as gfx
from wgpu.gui.auto import call_later, run, WgpuCanvas

import collagraph as cg
from collagraph import h


class Button(cg.Component):
    geometry = gfx.box_geometry()
    materials = {
        "default": gfx.MeshPhongMaterial(color=[1.0, 0.5, 0.0]),
        "pressed": gfx.MeshPhongMaterial(color=[0.0, 0.5, 0.0]),
        "hovered": gfx.MeshPhongMaterial(color=[1.0, 0.2, 0.0]),
    }

    def __init__(self, props):
        super().__init__(props)
        self.state["pressed"] = False
        self.state["hovered"] = False
        self.state["scale"] = self.props.get("scale", [0.85] * 3)

    def pressed(self, event):
        def release():
            self.state["pressed"] = False

        self.state["pressed"] = True
        call_later(2, release)

    def hover(self, hover):
        self.state["hovered"] = hover

    def render(self):
        material = (
            Button.materials["pressed"]
            if self.state["pressed"]
            else (
                Button.materials["hovered"]
                if self.state["hovered"]
                else Button.materials["default"]
            )
        )
        return h(
            "Mesh",
            {
                "position": self.props["position"],
                "scale": self.state["scale"],
                "geometry": Button.geometry,
                "material": material,
                "on_click": self.pressed,
                "on_pointer_enter": lambda ev: self.hover(True),
                "on_pointer_leave": lambda ev: self.hover(False),
            },
        )


class NumberPad(cg.Component):
    def __init__(self, props):
        super().__init__(props)
        self.state["columns"] = 4
        self.state["rows"] = 5

    def render(self):
        locations = []
        for x in range(self.state["columns"]):
            for y in range(self.state["rows"]):
                locations.append(
                    (
                        x - (self.state["columns"] - 1) / 2,
                        y - (self.state["rows"] - 1) / 2,
                        0,
                    )
                )
        return h(
            "Group", {}, *[h(Button, {"position": position}) for position in locations]
        )


if __name__ == "__main__":
    canvas = WgpuCanvas(size=(600, 400))
    renderer = gfx.renderers.WgpuRenderer(canvas)

    camera = gfx.PerspectiveCamera(60, 16 / 9)
    camera.position.z = 7
    camera.position.y = -2

    controls = gfx.OrbitController(camera.position.clone())
    controls.add_default_event_handlers(renderer, camera)

    gui = cg.Collagraph(
        renderer=cg.PygfxRenderer(), event_loop_type=cg.EventLoopType.QT
    )

    element = h(NumberPad, {})
    container = gfx.Scene()

    def animate():
        controls.update_camera(camera)
        renderer.render(container, camera)

    gui.render(element, container, callback=lambda: canvas.request_draw(animate))
    run()
