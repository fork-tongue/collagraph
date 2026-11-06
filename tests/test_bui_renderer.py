import pytest
from observ import reactive

import collagraph as cg

pytest.importorskip("blenderui")

import buipy
from blenderui import components as bc

from collagraph.renderers.bui_renderer import TextElement, Window


@pytest.fixture
def renderer():
    yield cg.BuiRenderer(headless=True)


def render(renderer, source, parse_source, state=None):
    Component, _ = parse_source(source)
    gui = cg.Collagraph(renderer=renderer, event_loop_type=cg.EventLoopType.SYNC)
    gui.render(Component, None, state=state)
    return gui


def click(window, el):
    window.render()
    x, y, w, h = el.rect
    window.ctx.press(x + w // 2, y + h // 2, 0)
    window.ctx.release(x + w // 2, y + h // 2, 0)


@pytest.mark.parametrize(
    "tag, typ",
    [
        ("window", Window),
        ("column", bc.Column),
        ("row", bc.Row),
        ("box", bc.Box),
        ("label", bc.Label),
        ("button", bc.Button),
        ("icon-button", bc.IconButton),
        ("checkbox", bc.Checkbox),
        ("toggle", bc.Toggle),
        ("number-field", bc.NumberField),
        ("number", bc.NumberField),
        ("NumberSlider", bc.NumberSlider),
        ("slider", bc.NumberSlider),
        ("text_field", bc.TextField),
        ("dropdown", bc.Dropdown),
        ("enum", bc.EnumRow),
        ("color-swatch", bc.ColorSwatch),
        ("progress", bc.ProgressBar),
        ("panel", bc.Panel),
        ("tabs", bc.Tabs),
        ("scroll-view", bc.ScrollView),
        ("split", bc.Split),
    ],
)
def test_create_element(renderer, tag, typ):
    el = renderer.create_element(tag)
    assert type(el) is typ


def test_create_unknown_element(renderer):
    with pytest.raises(ValueError):
        renderer.create_element("foo")


def test_register_element(renderer):
    class Fancy(bc.Row):
        pass

    cg.BuiRenderer.register_element("fancy-row", Fancy)
    assert isinstance(renderer.create_element("fancy-row"), Fancy)

    with pytest.raises(TypeError):
        cg.BuiRenderer.register_element("not-a-node", object)


def test_insert_with_anchor_and_move(renderer):
    parent = renderer.create_element("column")
    a, b, c = (renderer.create_element("label") for _ in range(3))
    for el, text in zip((a, b, c), "abc"):
        renderer.set_attribute(el, "text", text)

    renderer.insert(a, parent)
    renderer.insert(c, parent)
    renderer.insert(b, parent, anchor=c)
    assert [el.text for el in parent.children] == ["a", "b", "c"]

    # Move 'a' before 'c'
    renderer.insert(a, parent, anchor=c)
    assert [el.text for el in parent.children] == ["b", "a", "c"]

    renderer.remove(a, parent)
    assert [el.text for el in parent.children] == ["b", "c"]


def test_panel_children_go_into_body(renderer):
    panel = renderer.create_element("panel")
    label = renderer.create_element("label")
    renderer.insert(label, panel)
    assert panel.body.children == [label]
    renderer.remove(label, panel)
    assert panel.body.children == []


def test_text_elements(renderer):
    label = renderer.create_element("label")
    first, second = TextElement(), TextElement()
    renderer.set_element_text(first, "Hello")
    renderer.insert(first, label)
    assert label.text == "Hello"

    renderer.set_element_text(second, ", world")
    renderer.insert(second, label)
    assert label.text == "Hello, world"

    renderer.remove(first, label)
    assert label.text == ", world"

    # Value components use the text for their label
    checkbox = renderer.create_element("checkbox")
    renderer.insert(first, checkbox)
    assert checkbox.label == "Hello"

    # Containers don't support text
    with pytest.raises(TypeError):
        renderer.insert(TextElement(), renderer.create_element("column"))


def test_attributes(renderer):
    label = renderer.create_element("label")

    # Python properties
    renderer.set_attribute(label, "enabled", False)
    assert not label.enabled
    renderer.remove_attribute(label, "enabled", None)
    assert label.enabled

    # Kit node properties
    renderer.set_attribute(label, "bold", True)
    assert label.get("bold")
    renderer.remove_attribute(label, "bold", None)
    assert not label.get("bold")

    # Kebab-case attributes are converted to snake-case
    renderer.set_attribute(label, "text-align", "center")

    with pytest.raises(KeyError):
        renderer.set_attribute(label, "unknown", 1)


def test_value_attribute_does_not_emit(renderer):
    slider = renderer.create_element("slider")
    changes = []
    renderer.add_event_listener(slider, "change", changes.append)

    renderer.set_attribute(slider, "value", 0.5)
    assert slider.value == 0.5
    assert changes == []

    renderer.remove_attribute(slider, "value", None)
    assert slider.value == 0.0


def test_event_listeners(renderer):
    button = renderer.create_element("button")
    calls = []

    def first():
        calls.append("first")

    def second():
        calls.append("second")

    renderer.add_event_listener(button, "click", first)
    renderer.add_event_listener(button, "clicked", second)
    button.click()
    assert calls == ["first", "second"]

    renderer.remove_event_listener(button, "click", first)
    button.click()
    assert calls == ["first", "second", "second"]

    with pytest.raises(ValueError):
        renderer.add_event_listener(button, "unknown", first)


def test_counter(renderer, parse_source):
    gui = render(
        renderer,
        """
        <window title="Counter" :size="(300, 160)">
          <label>Count: {{ count }}</label>
          <button @click="bump">Bump</button>
        </window>

        <script>
        import collagraph as cg

        class Counter(cg.Component):
            def init(self):
                self.state["count"] = 0

            def bump(self):
                self.state["count"] += 1
        </script>
        """,
        parse_source,
    )

    assert len(renderer.windows) == 1
    window = renderer.windows[0]
    assert window.title == "Counter"
    assert window.size == (300, 160)
    assert window.host is None

    label, button = window.children
    assert label.text == "Count: 0"
    assert button.text == "Bump"

    click(window, button)
    assert label.text == "Count: 1"
    assert gui.fragment


def test_value_component_events(renderer, parse_source):
    gui = render(
        renderer,
        """
        <column>
          <checkbox :value="checked" @change="toggle">Check</checkbox>
          <label>{{ "on" if checked else "off" }}</label>
        </column>

        <script>
        import collagraph as cg

        class Example(cg.Component):
            def init(self):
                self.state["checked"] = False

            def toggle(self, value):
                self.state["checked"] = value
        </script>
        """,
        parse_source,
    )

    # Non-window top-level elements are wrapped in a window
    window = renderer.windows[0]
    (column,) = window.children
    checkbox, label = column.children
    assert checkbox.label == "Check"
    assert label.text == "off"

    window.render()
    x, y, _, h = checkbox.rect
    window.ctx.press(x + 5, y + h // 2, 0)
    window.ctx.release(x + 5, y + h // 2, 0)
    assert checkbox.value is True
    assert label.text == "on"
    assert gui.fragment


def test_for_loop_keyed(renderer, parse_source):
    state = reactive({"items": ["a", "b", "c"]})
    gui = render(
        renderer,
        """
        <column>
          <label v-for="item in items" :key="item" :text="item" />
        </column>

        <script>
        import collagraph as cg

        class Example(cg.Component):
            pass
        </script>
        """,
        parse_source,
        state=state,
    )

    (column,) = renderer.windows[0].children

    def texts():
        return [child.text for child in column.children]

    assert texts() == ["a", "b", "c"]

    state["items"] = ["c", "a", "b"]
    assert texts() == ["c", "a", "b"]

    state["items"].insert(1, "d")
    assert texts() == ["c", "d", "a", "b"]

    state["items"].remove("a")
    assert texts() == ["c", "d", "b"]

    state["items"].reverse()
    assert texts() == ["b", "d", "c"]
    assert gui.fragment


def test_if_and_unmount(renderer, parse_source):
    state = reactive({"show": True})
    gui = render(
        renderer,
        """
        <window>
          <label v-if="show" text="visible" />
          <button text="end" />
        </window>

        <script>
        import collagraph as cg

        class Example(cg.Component):
            pass
        </script>
        """,
        parse_source,
        state=state,
    )

    window = renderer.windows[0]
    assert [child.type for child in window.children] == ["label", "button"]

    state["show"] = False
    assert [child.type for child in window.children] == ["button"]

    state["show"] = True
    assert [child.type for child in window.children] == ["label", "button"]

    gui.fragment.unmount()
    assert renderer.windows == []


def test_default_event_loop_without_windows(renderer, parse_source):
    """Without open (host) windows, the renderer flushes synchronously."""
    Component, _ = parse_source(
        """
        <label :text="text" />

        <script>
        import collagraph as cg

        class Example(cg.Component):
            pass
        </script>
        """
    )
    state = reactive({"text": "foo"})
    gui = cg.Collagraph(renderer=renderer)
    gui.render(Component, None, state=state)

    (label,) = renderer.windows[0].children
    assert label.text == "foo"
    state["text"] = "bar"
    assert label.text == "bar"


def test_window_render(renderer):
    window = renderer.create_element("window")
    renderer.insert(window, None)
    raster = window.render(200, 100)
    assert isinstance(raster, buipy.Raster)
    assert raster.size == (200, 100)


class FakeHost:
    """Stands in for a bui.host.Window: collects the timers."""

    def __init__(self):
        self.is_open = True
        self.timers = []

    def after(self, ms, fn):
        self.timers.append(fn)

    def fire(self):
        timers, self.timers = self.timers, []
        for fn in timers:
            fn()


def test_threadsafe_scheduler_headless(renderer):
    # There is no event loop to run callbacks on
    assert renderer.get_threadsafe_scheduler() is None


def test_threadsafe_scheduler():
    import threading

    renderer = cg.BuiRenderer()
    window = Window()
    window.host = FakeHost()
    renderer.windows.append(window)

    schedule = renderer.get_threadsafe_scheduler()
    assert len(window.host.timers) == 1

    calls = []
    thread = threading.Thread(
        target=schedule, args=(lambda: calls.append(threading.current_thread()),)
    )
    thread.start()
    thread.join()
    assert calls == []

    # The poll timer runs the callback on the main thread and keeps polling
    window.host.fire()
    assert calls == [threading.main_thread()]
    assert len(window.host.timers) == 1

    # When the window is replaced (e.g. by a full hot reload), polling moves
    # to the new window
    new_window = Window()
    new_window.host = FakeHost()

    def replace_window():
        window.host.is_open = False
        renderer.windows.remove(window)
        renderer.windows.append(new_window)

    schedule(replace_window)
    window.host.fire()
    assert window.host.timers == []
    assert len(new_window.host.timers) == 1

    # Polling stops when all windows are closed...
    new_window.host.is_open = False
    new_window.host.fire()
    assert new_window.host.timers == []

    # ...and starts again when a window opens
    third = renderer.create_element("window")
    third.open = lambda show=True: setattr(third, "host", FakeHost())
    renderer.insert(third, None)
    assert len(third.host.timers) == 1
