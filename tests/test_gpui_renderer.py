"""
Tests for the GPUI renderer (gpyui).

gpyui keeps a retained tree of Python control handles which is only sent to
the native GPUI side once `Application.run()` is called. These tests inspect
that Python tree, so they run without opening a window.
"""

import asyncio

import pytest

gpyui = pytest.importorskip("gpyui")

from observ import reactive  # noqa: E402

from collagraph import Collagraph  # noqa: E402
from collagraph.renderers.gpui_renderer import (  # noqa: E402
    GpuiElement,
    GpuiRenderer,
)


def click(control):
    """Simulate a native event (as gpyui would dispatch it)."""
    emit(control, "click")


def emit(control, name, value=None):
    if name == "change" and hasattr(control, "_receive_native"):
        control._receive_native(value)
    control._handlers[name](gpyui.Event(control, name, value))


def render(parse_source, source, state=None):
    App, _ = parse_source(source)
    app = gpyui.Application(title="test")
    renderer = GpuiRenderer()
    gui = Collagraph(renderer=renderer)
    props = reactive(state or {})
    gui.render(App, app, state=props)
    # Keep the collagraph instance alive for as long as the app,
    # just like an application's main function would
    app._test_gui = gui
    return app, gui, props


def test_counter(parse_source):
    app, _, _ = render(
        parse_source,
        """
        <column>
          <label>Count: {{ count }}</label>
          <button @click="bump">bump</button>
        </column>

        <script>
        import collagraph as cg

        class Counter(cg.Component):
            def init(self):
                self.state["count"] = 0

            def bump(self):
                self.state["count"] += 1
        </script>
        """,
    )
    (column,) = app.children
    assert isinstance(column, gpyui.Column)
    label, button = column.children
    assert isinstance(label, gpyui.Label)
    assert isinstance(button, gpyui.Button)
    assert label.text == "Count: 0"
    assert button.text == "bump"

    click(button)
    assert label.text == "Count: 1"
    click(button)
    assert label.text == "Count: 2"


def test_construction_properties_and_coercion(parse_source):
    app, _, _ = render(
        parse_source,
        """
        <column gap="12" padding="8">
          <slider minimum="10" maximum="20" value="15" step="0.5" />
          <radio-group :items="['a', 'b', 'c']" value="2" />
          <switch text="Dark mode" value="true" />
          <text-input placeholder="Name" disabled />
        </column>

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """,
    )
    (column,) = app.children
    assert column._style == {"gap": 12.0, "padding": 8.0}
    slider, radio, switch, text_input = column.children
    assert isinstance(slider, gpyui.Slider)
    assert (slider.minimum, slider.maximum, slider.value) == (10, 20, 15)
    assert slider.step == 0.5
    assert isinstance(radio, gpyui.RadioGroup)
    assert radio.items == ["a", "b", "c"]
    assert radio.value == 2
    assert switch.value is True
    assert isinstance(text_input, gpyui.TextInput)
    assert text_input.placeholder == "Name"
    assert text_input.disabled is True


def test_change_event_passes_value(parse_source):
    app, _, _ = render(
        parse_source,
        """
        <column>
          <slider :value="volume" @change="set_volume" />
          <label>{{ volume }}</label>
        </column>

        <script>
        import collagraph as cg

        class App(cg.Component):
            def init(self):
                self.state["volume"] = 30

            def set_volume(self, value):
                self.state["volume"] = value
        </script>
        """,
    )
    slider, label = app.children[0].children
    assert label.text == "30"
    emit(slider, "change", 70.0)
    assert slider.value == 70
    assert label.text == "70.0"


def test_dynamic_construction_only_property_rebuilds(parse_source):
    app, _, props = render(
        parse_source,
        """
        <column>
          <label>before</label>
          <slider :maximum="maximum" />
          <label>after</label>
        </column>

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """,
        state={"maximum": 50},
    )
    before, slider, after = app.children[0].children
    assert slider.maximum == 50

    props["maximum"] = 80
    new_before, new_slider, new_after = app.children[0].children
    assert new_slider is not slider
    assert slider.disposed
    assert new_slider.maximum == 80
    assert (new_before, new_after) == (before, after)


def test_v_if_and_v_for(parse_source):
    app, _, props = render(
        parse_source,
        """
        <column>
          <label>header</label>
          <label v-if="show">conditional</label>
          <tag v-for="item in items" :key="item" :text="item" />
          <label>footer</label>
        </column>

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """,
        state={"show": False, "items": ["a", "b"]},
    )
    column = app.children[0]

    def texts():
        return [child.text for child in column.children]

    assert texts() == ["header", "a", "b", "footer"]
    props["show"] = True
    assert texts() == ["header", "conditional", "a", "b", "footer"]
    tags = column.children[2:4]
    props["items"] = ["b", "c", "a"]
    assert texts() == ["header", "conditional", "b", "c", "a", "footer"]
    # Keyed items retain their controls
    assert column.children[2] is tags[1]
    assert column.children[4] is tags[0]
    props["show"] = False
    props["items"] = []
    assert texts() == ["header", "footer"]


def test_removed_controls_get_disposed(parse_source):
    app, _, props = render(
        parse_source,
        """
        <column>
          <label v-if="show">conditional</label>
        </column>

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """,
        state={"show": True},
    )
    column = app.children[0]
    (label,) = column.children

    async def toggle():
        props["show"] = False
        # Let the scheduler flush and the renderer collect
        for _ in range(3):
            await asyncio.sleep(0)

    asyncio.run(toggle())
    assert column.children == ()
    assert label.disposed


def test_style_and_visible(parse_source):
    app, _, props = render(
        parse_source,
        """
        <row :style="style" :visible="visible">
          <label bold>Title</label>
        </row>

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """,
        state={"style": {"gap": 4, "background": "muted"}, "visible": True},
    )
    (row,) = app.children
    assert isinstance(row, gpyui.Row)
    assert row._style == {"gap": 4, "background": "muted"}
    assert row.children[0]._style == {"bold": True}

    props["visible"] = False
    assert row.visible is False
    props["style"] = {"gap": 8, "background": "muted"}
    assert app.children[0] is row
    assert row._style["gap"] == 8
    # Removing a style property requires a fresh control
    props["style"] = {"gap": 8}
    assert app.children[0] is not row
    assert app.children[0]._style == {"gap": 8}
    assert app.children[0].visible is False


def test_text_in_container_becomes_label(parse_source):
    app, _, props = render(
        parse_source,
        """
        <column>Hello {{ name }}</column>

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """,
        state={"name": "world"},
    )
    (label,) = app.children[0].children
    assert isinstance(label, gpyui.Label)
    assert label.text == "Hello world"
    props["name"] = "GPUI"
    assert label.text == "Hello GPUI"


def test_ref_is_element_handle(parse_source):
    app, gui, _ = render(
        parse_source,
        """
        <text-input ref="input" />

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """,
    )
    component = gui.fragment.component
    handle = component.refs["input"]
    assert isinstance(handle, GpuiElement)
    assert handle.control is app.children[0]


@pytest.mark.parametrize(
    "source,error,message",
    [
        ("<not-a-control />", ValueError, "Unknown gpui element type"),
        ("<label foo='bar' />", AttributeError, "Unknown attribute 'foo'"),
        ("<label @click='bump' />", ValueError, "does not support the 'click'"),
    ],
)
def test_errors(parse_source, source, error, message):
    App, _ = parse_source(
        f"""
        {source}

        <script>
        import collagraph as cg

        class App(cg.Component):
            def bump(self):
                pass
        </script>
        """
    )
    gui = Collagraph(renderer=GpuiRenderer())
    with pytest.raises(error, match=message):
        gui.render(App, gpyui.Application())


def test_register_element():
    class Card(gpyui.Container):
        pass

    try:
        GpuiRenderer.register_element("my-card", Card)
        renderer = GpuiRenderer()
        el = renderer.create_element("my-card")
        app = gpyui.Application()
        renderer.insert(el, app)
        assert isinstance(app.children[0], Card)
    finally:
        GpuiRenderer.ELEMENTS.pop("mycard", None)

    with pytest.raises(TypeError, match="Control subclass"):
        GpuiRenderer.register_element("nope", lambda: gpyui.Label())


def test_window_configures_application(parse_source):
    app, _, props = render(
        parse_source,
        """
        <window
          :title="title"
          :theme="'dark' if dark else 'light'"
          width="320"
          height="240"
        >
          <label>first</label>
          <label v-if="dark">second</label>
        </window>

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """,
        state={"title": "Hello", "dark": False},
    )
    assert app.title == "Hello"
    assert app.theme.mode == "light"
    assert (app.width, app.height) == (320, 240)
    # The children of the window are the roots of the application
    assert [child.text for child in app.children] == ["first"]

    props["title"] = "World"
    props["dark"] = True
    assert app.title == "World"
    assert app.theme.mode == "dark"
    assert [child.text for child in app.children] == ["first", "second"]


def test_window_requires_application(parse_source):
    App, _ = parse_source(
        """
        <window title="nope" />

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """
    )
    gui = Collagraph(renderer=GpuiRenderer())
    with pytest.raises(TypeError, match=r"gpyui\.Application"):
        gui.render(App, gpyui.Column())


def test_theme_object_attribute(parse_source):
    theme = gpyui.Theme("shadcn-blue", mode="dark")
    app, _, _ = render(
        parse_source,
        """
        <window :theme="theme" />

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """,
        state={"theme": theme},
    )
    assert app.theme == theme
