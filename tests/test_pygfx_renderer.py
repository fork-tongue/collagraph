from collections import namedtuple

import pytest

try:
    import pygfx as gfx
except ImportError:
    pytest.skip(reason="pygfx not installed", allow_module_level=True)

from collagraph.renderers import PygfxRenderer


def test_pygfx_create_element():
    renderer = PygfxRenderer()

    obj = renderer.create_element("Scene")
    assert isinstance(obj, gfx.Scene)

    obj = renderer.create_element("Mesh")
    assert isinstance(obj, gfx.Mesh)

    obj = renderer.create_element("MeshBasicMaterial")
    assert isinstance(obj, gfx.MeshBasicMaterial)

    with pytest.raises(ValueError):
        renderer.create_element("Foo")


def test_pygfx_insert_remove():
    renderer = PygfxRenderer()

    parent = gfx.Scene()

    child1 = gfx.WorldObject()
    child2 = gfx.WorldObject()

    renderer.insert(child1, parent)
    assert parent.children == (child1,)

    renderer.insert(child2, parent)
    assert parent.children == (child1, child2)

    renderer.insert(child2, parent, anchor=child1)
    assert parent.children == (child2, child1)

    renderer.remove(child2, parent)
    assert parent.children == (child1,)

    renderer.remove(child1, parent)
    assert parent.children == ()


def test_pygfx_attributes():
    renderer = PygfxRenderer()

    mesh = gfx.Mesh()

    renderer.set_attribute(mesh, "name", "foo")
    assert mesh.name == "foo"

    renderer.set_attribute(mesh, "position", [3, 2, 5])
    assert mesh.position == gfx.linalg.Vector3(3, 2, 5)

    renderer.set_attribute(mesh, "rotation", [1, 2, 3, 4])
    assert mesh.rotation == gfx.linalg.Quaternion(1, 2, 3, 4)

    renderer.set_attribute(mesh, "matrix", [1] * 16)
    assert mesh.matrix == gfx.linalg.Matrix4(*[1] * 16)

    material = gfx.Material()

    renderer.set_attribute(material, "color", [1, 0.5, 0, 0.8])
    assert material.color == [1, 0.5, 0, 0.8]

    # The pygfx renderer does not support removing attributes
    with pytest.raises(NotImplementedError):
        renderer.remove_attribute(material, "color", [1, 0.5, 0, 0.8])


def test_event_handlers():
    renderer = PygfxRenderer()

    count = 0

    def counter(event):
        nonlocal count
        count += 1

    obj = gfx.Scene()
    renderer.add_event_listener(obj, "click", counter)

    Event = namedtuple("Event", ["type", "cancelled"], defaults=[False])
    event = Event("click")
    obj.handle_event(event)

    assert count == 1

    renderer.remove_event_listener(obj, "click", counter)

    obj.handle_event(event)

    assert count == 1
