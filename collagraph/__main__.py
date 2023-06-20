import argparse
import importlib
from pathlib import Path

import collagraph as cg


def available_renderers():
    result = set()
    for renderer_type, name in {
        "PySideRenderer": "pyside",
        "PygfxRenderer": "pygfx",
        "DictRenderer": "dict",
        "DomRenderer": "dom",
    }.items():
        try:
            importlib.import_module("collagraph", renderer_type)
            result.add(name)
        except ImportError:
            continue
    return result


def init_collagraph(renderer_type: str, component_path: Path):
    Component, _ = cg.cgx.cgx.load(component_path)

    if renderer_type == "pygfx":
        import pygfx as gfx
        from wgpu.gui.auto import run, WgpuCanvas

        canvas = WgpuCanvas(size=(600, 400))
        wgpu_renderer = gfx.renderers.WgpuRenderer(canvas)

        camera = gfx.PerspectiveCamera(70, 16 / 9)
        camera.position.z = 15

        controls = gfx.OrbitController(camera.position.clone())
        controls.add_default_event_handlers(wgpu_renderer, camera)

        container = gfx.Scene()

        def animate():
            controls.update_camera(camera)
            wgpu_renderer.render(container, camera)

        gui = cg.Collagraph(
            renderer=cg.PygfxRenderer(),
            event_loop_type=cg.EventLoopType.QT,
        )
        gui.render(
            cg.h(Component),
            container,
            callback=lambda: canvas.request_draw(animate),
        )

        run()
    elif renderer_type == "pyside":
        from PySide6 import QtWidgets

        app = QtWidgets.QApplication()
        gui = cg.Collagraph(renderer=cg.PySideRenderer())
        gui.render(cg.h(Component), app)
        app.exec()
    elif renderer_type == "dict":
        container = {"root": None}
        gui = cg.Collagraph(
            renderer=cg.DictRenderer(),
            event_loop_type=cg.EventLoopType.SYNC,
        )
        gui.render(cg.h(Component), container)
        print(container)  # noqa
        # Start debugger to allow for manipulation of container
        breakpoint()
    elif renderer_type == "dom":
        raise NotImplementedError


def existing_component_file(value):
    path = Path(value)
    if not path.exists():
        raise argparse.ArgumentTypeError(f"{value} does not exist")
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"{value} is not a file")
    if path.suffix != ".cgx":
        raise argparse.ArgumentTypeError(f"{value} is not a collagraph component")
    return path


def run():
    parser = argparse.ArgumentParser(
        description="Run collagraph components directly",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--renderer",
        default="pyside",
        choices=available_renderers(),
        help="The type of renderer to use",
    )
    # parser.add_argument(
    #     "--state",
    #     help="Optional state to load (json file or string)",
    # )
    parser.add_argument(
        "component",
        type=existing_component_file,
        help="Path to component to render",
    )
    args = parser.parse_args()

    init_collagraph(args.renderer, args.component)


if __name__ == "__main__":
    run()
