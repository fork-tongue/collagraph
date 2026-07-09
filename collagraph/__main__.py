from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

from observ import reactive

import collagraph as cg


def available_renderers():
    result = set()
    for renderer_type, name in {
        "PySideRenderer": "pyside",
        "PygfxRenderer": "pygfx",
        "DictRenderer": "dict",
    }.items():
        try:
            importlib.import_module("collagraph", renderer_type)
            result.add(name)
        except ImportError:
            continue
    return result


def load_component_class(component_path: Path, class_name: str | None = None):
    """Import a component file (.cgx or .py) and return its root component class."""
    if component_path.suffix == ".cgx":
        file_as_module = ".".join([*component_path.parts[:-1], component_path.stem])
        component_module = importlib.import_module(file_as_module)
        return component_module.__component_class

    # Plain Python module with view component(s): import it by its stem,
    # with its directory on sys.path so sibling imports work
    directory = str(component_path.parent.resolve())
    if directory not in sys.path:
        sys.path.insert(0, directory)
    module = importlib.import_module(component_path.stem)
    module_file = getattr(module, "__file__", None)
    if module_file is None or Path(module_file).resolve() != component_path.resolve():
        raise SystemExit(
            f"Cannot import {component_path}: the module name "
            f"{component_path.stem!r} is already taken by {module_file!r}. "
            "Rename the file to something unique."
        )
    return find_view_component_class(module, class_name, component_path)


def find_view_component_class(module, class_name: str | None, component_path: Path):
    """Find the root view component class in a plain Python module."""
    if class_name is not None:
        cls = getattr(module, class_name, None)
        if not (isinstance(cls, type) and issubclass(cls, cg.Component)):
            raise SystemExit(
                f"{component_path}: {class_name!r} is not a Component subclass"
            )
        return cls

    # Allow modules to mark their root component explicitly,
    # like compiled .cgx modules do
    explicit = getattr(module, "__component_class", None)
    if explicit is not None:
        return explicit

    candidates = [
        attr
        for attr in vars(module).values()
        if isinstance(attr, type)
        and issubclass(attr, cg.Component)
        and attr is not cg.Component
        and attr.__module__ == module.__name__
        and attr.view is not cg.Component.view
    ]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise SystemExit(f"No view component found in {component_path}")
    names = ", ".join(cls.__name__ for cls in candidates)
    hint = f"{component_path}:{candidates[-1].__name__}"
    raise SystemExit(
        f"Multiple view components found in {component_path}: {names}. "
        f"Select one by appending the class name: {hint}"
    )


def init_collagraph(
    renderer_type: str,
    component_path: Path,
    state: dict | None = None,
    hot_reload: bool = False,
    class_name: str | None = None,
):
    component_class = load_component_class(component_path, class_name)
    props = reactive(state or {})

    if renderer_type == "pygfx":
        import pygfx as gfx
        from rendercanvas.auto import RenderCanvas, loop

        canvas = RenderCanvas(size=(600, 400))
        wgpu_renderer = gfx.renderers.WgpuRenderer(canvas)

        camera = gfx.PerspectiveCamera(70)
        camera.local.z = 15
        camera.show_pos((0, 0, 0))

        controls = gfx.OrbitController(camera)
        controls.register_events(wgpu_renderer)

        container = gfx.Scene()

        def animate():
            wgpu_renderer.render(container, camera)

        renderer = cg.PygfxRenderer()
        renderer.add_on_change_handler(lambda: canvas.request_draw(animate))
        gui = cg.Collagraph(renderer=renderer, hot_reload=hot_reload)
        gui.render(component_class, container, state=props)

        loop.run()
    elif renderer_type == "pyside":
        from PySide6 import QtWidgets

        app = QtWidgets.QApplication()
        gui = cg.Collagraph(renderer=cg.PySideRenderer(), hot_reload=hot_reload)
        gui.render(component_class, app, state=props)
        app.exec()
    elif renderer_type == "dict":
        container = {"root": None}
        gui = cg.Collagraph(
            renderer=cg.DictRenderer(),
            event_loop_type=cg.EventLoopType.SYNC,
            hot_reload=hot_reload,
        )
        gui.render(component_class, container, state=props)
        # Start debugger to allow for inspection of container
        # and manipulation of props
        breakpoint()  # noqa: T100


def show_code(component_path: Path):
    """Pretty print the Python code that is compiled for a component."""
    from collagraph.sfc import print_source
    from collagraph.sfc.compiler import generate_source

    print_source(generate_source(component_path), component_path)


def existing_component_file(value):
    path = Path(value)
    class_name = None
    if not path.exists() and ":" in value:
        # Allow selecting a component class: path/to/module.py:ClassName
        path_str, _, name = value.rpartition(":")
        if name.isidentifier():
            path = Path(path_str)
            class_name = name
    if not path.exists():
        raise argparse.ArgumentTypeError(f"{value} does not exist")
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"{value} is not a file")
    if path.suffix not in (".cgx", ".py"):
        raise argparse.ArgumentTypeError(f"{value} is not a collagraph component")
    if class_name and path.suffix != ".py":
        raise argparse.ArgumentTypeError(
            f"{value}: selecting a component class is only supported for .py files"
        )
    return path, class_name


def json_contents(value):
    path = Path(value)
    if path.is_file():
        with path.open(mode="r", encoding="utf-8") as fh:
            try:
                return json.load(fh)
            except Exception:
                raise argparse.ArgumentTypeError(f"{value} is not valid json")
    else:
        try:
            return json.loads(value)
        except Exception:
            raise argparse.ArgumentTypeError(f"{value} is not valid json")


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
    parser.add_argument(
        "--state",
        type=json_contents,
        help="Optional state/props to load (json file or string)",
    )
    parser.add_argument(
        "component",
        type=existing_component_file,
        help=(
            "Path to component to render: a .cgx file or a .py module "
            "with a view component (append :ClassName to select a class)"
        ),
    )
    parser.add_argument(
        "--hot-reload",
        "-H",
        action="store_true",
        help="Enable hot reloading (reload on file changes)",
    )
    parser.add_argument(
        "--show-code",
        action="store_true",
        help="Pretty print the compiled Python code for the component and exit",
    )
    args = parser.parse_args()
    component_path, class_name = args.component

    if args.show_code:
        if component_path.suffix != ".cgx":
            parser.error("--show-code is only supported for .cgx files")
        show_code(component_path)
        return

    init_collagraph(
        args.renderer,
        component_path,
        args.state,
        args.hot_reload,
        class_name=class_name,
    )


if __name__ == "__main__":
    run()
