import math
from collections import namedtuple

import pytest
from observ import reactive

try:
    import pygfx as gfx
except ImportError:
    pytest.skip(reason="pygfx not installed", allow_module_level=True)

from collagraph import Collagraph, EventLoopType
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

    def equals(a, b):
        if len(a) != len(b):
            return False
        for x, y in zip(a, b):
            if x != y:
                return False
        return True

    renderer.insert(child1, parent)
    assert equals(parent.children, (child1,))

    renderer.insert(child2, parent)
    assert equals(parent.children, (child1, child2))

    renderer.insert(child2, parent, anchor=child1)
    assert equals(parent.children, (child2, child1))

    renderer.remove(child2, parent)
    assert equals(parent.children, (child1,))

    renderer.remove(child1, parent)
    assert equals(parent.children, ())


def test_pygfx_attributes():
    renderer = PygfxRenderer()

    # Set and unset attributes on Mesh
    mesh = gfx.Mesh()

    # Custom attribute 'custom_name'
    assert not hasattr(mesh, "custom_name")
    renderer.set_attribute(mesh, "custom_name", "foo")
    assert mesh.custom_name == "foo"

    renderer.remove_attribute(mesh, "custom_name", "foo")
    assert not hasattr(mesh, "custom_name")

    # Position attribute
    original_position_contents = mesh.local.position.tolist()
    renderer.set_attribute(mesh, "local.position", (3, 2, 5))

    assert mesh.local.position.tolist() == [3, 2, 5]

    renderer.remove_attribute(mesh, "local.position", [3, 2, 5])
    assert mesh.local.position.tolist() == original_position_contents

    # Rotation attribute
    original_rotation_contents = mesh.local.rotation.tolist()
    renderer.set_attribute(mesh, "local.rotation", [0, 1, 0, 0])
    assert mesh.local.rotation.tolist() == [0, 1, 0, 0]

    renderer.remove_attribute(mesh, "local.rotation", [1, 2, 3, 4])
    assert mesh.local.rotation.tolist() == original_rotation_contents

    # Matrix attribute
    original_matrix_contents = mesh.local.matrix.tolist()
    matrix = [[2, 0, 0, 0], [0, 2, 0, 0], [0, 0, 2, 0], [0, 0, 0, 1]]
    renderer.set_attribute(mesh, "local.matrix", matrix)
    assert mesh.local.matrix.tolist() == matrix

    renderer.remove_attribute(mesh, "local.matrix", [1] * 16)
    assert mesh.local.matrix.tolist() == original_matrix_contents

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


def test_pygfx_text_attributes_use_text_api(monkeypatch):
    renderer = PygfxRenderer()
    text = gfx.Text()

    calls = []

    def set_text(value):
        calls.append(("text", value))

    def set_markdown(value):
        calls.append(("markdown", value))

    monkeypatch.setattr(text, "set_text", set_text)
    monkeypatch.setattr(text, "set_markdown", set_markdown)

    renderer.set_attribute(text, "text", "Hello")
    renderer.set_attribute(text, "markdown", "**World**")

    assert calls == [("text", "Hello"), ("markdown", "**World**")]
    assert "text" not in text.__dict__
    assert "markdown" not in text.__dict__


def test_pygfx_create_text_element_returns_proxy():
    renderer = PygfxRenderer()

    proxy = renderer.create_element("TEXT_ELEMENT")

    assert isinstance(proxy, gfx.WorldObject)
    assert hasattr(proxy, "_cg_content")


def test_pygfx_text_proxy_content_update_resyncs_parent_text(monkeypatch):
    renderer = PygfxRenderer()
    parent = gfx.Text()
    proxy = renderer.create_element("TEXT_ELEMENT")

    calls = []

    def set_text(value):
        calls.append(value)

    monkeypatch.setattr(parent, "set_text", set_text)

    renderer.set_attribute(proxy, "content", "Hello")
    assert calls == []

    renderer.insert(proxy, parent)
    assert calls == ["Hello"]

    renderer.set_attribute(proxy, "content", "Updated")
    assert calls == ["Hello", "Updated"]


def test_pygfx_text_multiple_proxies_concatenate_in_children_order(monkeypatch):
    renderer = PygfxRenderer()
    parent = gfx.Text()

    calls = []

    def set_text(value):
        calls.append(value)

    monkeypatch.setattr(parent, "set_text", set_text)

    a = renderer.create_element("TEXT_ELEMENT")
    b = renderer.create_element("TEXT_ELEMENT")
    c = renderer.create_element("TEXT_ELEMENT")

    renderer.set_attribute(a, "content", "A")
    renderer.set_attribute(b, "content", "B")
    renderer.set_attribute(c, "content", "C")

    renderer.insert(a, parent)
    renderer.insert(b, parent)
    renderer.insert(c, parent)

    assert calls[-1] == "ABC"


def test_pygfx_text_anchor_insert_updates_composition_order(monkeypatch):
    renderer = PygfxRenderer()
    parent = gfx.Text()

    calls = []

    def set_text(value):
        calls.append(value)

    monkeypatch.setattr(parent, "set_text", set_text)

    a = renderer.create_element("TEXT_ELEMENT")
    b = renderer.create_element("TEXT_ELEMENT")
    c = renderer.create_element("TEXT_ELEMENT")

    renderer.set_attribute(a, "content", "A")
    renderer.set_attribute(b, "content", "B")
    renderer.set_attribute(c, "content", "C")

    renderer.insert(a, parent)
    renderer.insert(c, parent)
    renderer.insert(b, parent, anchor=c)

    assert calls[-1] == "ABC"


def test_pygfx_text_remove_middle_proxy_recomputes_joined_text(monkeypatch):
    renderer = PygfxRenderer()
    parent = gfx.Text()

    calls = []

    def set_text(value):
        calls.append(value)

    monkeypatch.setattr(parent, "set_text", set_text)

    a = renderer.create_element("TEXT_ELEMENT")
    b = renderer.create_element("TEXT_ELEMENT")
    c = renderer.create_element("TEXT_ELEMENT")

    renderer.set_attribute(a, "content", "A")
    renderer.set_attribute(b, "content", "B")
    renderer.set_attribute(c, "content", "C")

    renderer.insert(a, parent)
    renderer.insert(b, parent)
    renderer.insert(c, parent)
    renderer.remove(b, parent)

    assert calls[-1] == "AC"


def test_pygfx_text_proxy_update_after_remove_does_not_resync(monkeypatch):
    renderer = PygfxRenderer()
    parent = gfx.Text()
    proxy = renderer.create_element("TEXT_ELEMENT")

    calls = []

    def set_text(value):
        calls.append(value)

    monkeypatch.setattr(parent, "set_text", set_text)

    renderer.set_attribute(proxy, "content", "A")
    renderer.insert(proxy, parent)
    renderer.remove(proxy, parent)

    call_count = len(calls)
    renderer.set_attribute(proxy, "content", "B")

    assert len(calls) == call_count


def test_pygfx_text_sync_ignores_non_proxy_children(monkeypatch):
    renderer = PygfxRenderer()
    parent = gfx.Text()

    calls = []

    def set_text(value):
        calls.append(value)

    monkeypatch.setattr(parent, "set_text", set_text)

    proxy_a = renderer.create_element("TEXT_ELEMENT")
    proxy_b = renderer.create_element("TEXT_ELEMENT")
    non_proxy = gfx.WorldObject()

    renderer.set_attribute(proxy_a, "content", "A")
    renderer.set_attribute(proxy_b, "content", "B")

    renderer.insert(proxy_a, parent)
    renderer.insert(non_proxy, parent)
    renderer.insert(proxy_b, parent)

    assert calls[-1] == "AB"


def test_pygfx_template_text_children_update(parse_source, monkeypatch):
    App, _ = parse_source(
        """
        <scene>
          <text>Hello {{name}}!</text>
        </scene>

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """
    )

    calls = []
    original_set_text = gfx.Text.set_text

    def set_text(self, value):
        calls.append(value)
        original_set_text(self, value)

    monkeypatch.setattr(gfx.Text, "set_text", set_text)

    state = reactive({"name": "World"})
    container = gfx.Scene()
    gui = Collagraph(PygfxRenderer(), event_loop_type=EventLoopType.SYNC)

    gui.render(App, container, state)
    assert calls[-1] == "Hello World!"

    state["name"] = "Collagraph"
    assert calls[-1] == "Hello Collagraph!"


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
