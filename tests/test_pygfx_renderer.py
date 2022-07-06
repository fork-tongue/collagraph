from collections import namedtuple
import math

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

    obj = renderer.create_element("scene")
    assert isinstance(obj, gfx.Scene)

    obj = renderer.create_element("Mesh")
    assert isinstance(obj, gfx.Mesh)

    obj = renderer.create_element("MeshBasicMaterial")
    assert isinstance(obj, gfx.MeshBasicMaterial)

    with pytest.raises(ValueError):
        renderer.create_element("Foo")


def test_pygfx_text_element_not_supported():
    renderer = PygfxRenderer()
    obj = renderer.create_element("scene")

    with pytest.raises(NotImplementedError):
        renderer.create_text_element()

    with pytest.raises(NotImplementedError):
        renderer.set_element_text(obj, "Foo")


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

    # Set and unset attributes on Mesh
    mesh = gfx.Mesh()

    # Custom attribute 'name'
    renderer.set_attribute(mesh, "name", "foo")
    assert mesh.name == "foo"

    renderer.remove_attribute(mesh, "name", "foo")
    assert not hasattr(mesh, "name")

    # Position attribute
    original_position_contents = mesh.position.to_array()
    renderer.set_attribute(mesh, "position", [3, 2, 5])
    assert mesh.position == gfx.linalg.Vector3(3, 2, 5)

    renderer.remove_attribute(mesh, "position", [3, 2, 5])
    assert mesh.position.to_array() == original_position_contents

    # Rotation attribute
    original_rotation_contents = mesh.rotation.to_array()
    renderer.set_attribute(mesh, "rotation", [1, 2, 3, 4])
    assert mesh.rotation == gfx.linalg.Quaternion(1, 2, 3, 4)

    renderer.remove_attribute(mesh, "rotation", [1, 2, 3, 4])
    assert mesh.rotation.to_array() == original_rotation_contents

    # Matrix attribute
    original_matrix_contents = mesh.matrix.to_array()
    renderer.set_attribute(mesh, "matrix", [1] * 16)
    assert mesh.matrix == gfx.linalg.Matrix4(*[1] * 16)

    renderer.remove_attribute(mesh, "matrix", [1] * 16)
    assert mesh.matrix.to_array() == original_matrix_contents

    # Set and unset attributes on Material
    material = gfx.LineMaterial()

    # Color attribute
    original_color_hex = material.color.hex
    renderer.set_attribute(material, "color", [1, 0.5, 0, 0.8])
    assert material.color.hex == gfx.Color(1, 0.5, 0, 0.8).hex

    renderer.remove_attribute(material, "color", [1, 0.5, 0, 0.8])
    assert material.color.hex == original_color_hex

    # Opacity attribute
    original_opacity = material.opacity
    renderer.set_attribute(material, "opacity", 0.5)
    assert math.isclose(material.opacity, 0.5)

    renderer.remove_attribute(material, "opacity", 0.5)
    assert material.opacity == original_opacity

    # Clipping planes attribute
    original_clipping_planes = material.clipping_planes.copy()
    renderer.set_attribute(material, "clipping_planes", [(0, 1, 2, 3)])
    assert material.clipping_planes[0] == (0, 1, 2, 3)

    renderer.remove_attribute(material, "clipping_planes", [(0, 1, 2, 3)])
    assert material.clipping_planes == original_clipping_planes


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
