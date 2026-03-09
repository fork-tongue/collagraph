"""Test reordering of components with multiple root elements."""

from observ import reactive

from collagraph import Collagraph, EventLoopType
from collagraph.renderers import Renderer


class CustomElement:
    def __init__(self, *args, type=None, **kwargs):
        super().__setattr__(
            "_data",
            {
                "type": type,
                "children": [],
                "event_listeners": {},
                **kwargs,
            },
        )

    def __getattr__(self, name):
        if name.startswith("_"):
            return super().__getattr__(name)
        return self._data[name]

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
        self._data[name] = value

    def __repr__(self):
        attrs = {
            k: v
            for k, v in self._data.items()
            if k not in ["children", "event_listeners"]
        }
        return f"<{self.type} {attrs}>"


class CustomElementRenderer(Renderer):
    def create_element(self, type):
        return CustomElement(type=type)

    def insert(self, el, parent, anchor=None):
        idx = parent.children.index(anchor) if anchor else len(parent.children)
        parent.children.insert(idx, el)

    def remove(self, el, parent):
        parent.children.remove(el)

    def set_attribute(self, el, attr: str, value):
        setattr(el, attr, value)

    def remove_attribute(self, el, attr: str, value):
        delattr(el, attr)

    def add_event_listener(self, el, event_type, value):
        pass

    def remove_event_listener(self, el, event_type, value):
        pass

    def create_text_element(self):
        raise NotImplementedError

    def set_element_text(self):
        raise NotImplementedError


def test_multi_root_component_reordering(parse_source):
    """
    Test that components with multiple root elements maintain
    correct order when the list is reordered.
    """
    # Component that renders multiple elements at root (no single wrapper)
    # This uses a template fragment (no single root element)
    MultiRoot, _ = parse_source(
        """
        <template>
            <header :text="props['id'] + '-header'" />
            <content :text="props['id'] + '-content'" />
            <footer :text="props['id'] + '-footer'" />
        </template>

        <script>
        import collagraph as cg

        class MultiRoot(cg.Component):
            pass
        </script>
        """
    )

    App, module = parse_source(
        """
        <app>
            <MultiRoot
                v-for="item in items"
                :key="item['id']"
                :id="item['id']"
            />
        </app>

        <script>
        import collagraph as cg

        try:
            import MultiRoot
        except:
            pass

        class App(cg.Component):
            pass
        </script>
        """
    )

    module["MultiRoot"] = MultiRoot

    renderer = CustomElementRenderer()
    container = CustomElement(type="root")
    state = reactive(
        {
            "items": [
                {"id": "A"},
                {"id": "B"},
                {"id": "C"},
            ]
        }
    )

    gui = Collagraph(
        renderer=renderer,
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    app_el = container.children[0]

    # Verify initial structure - should be 9 elements total (3 components x 3 each)
    assert len(app_el.children) == 9, f"Got {len(app_el.children)}"

    # Verify order: A's elements, then B's elements, then C's elements
    expected_initial = [
        "A-header",
        "A-content",
        "A-footer",
        "B-header",
        "B-content",
        "B-footer",
        "C-header",
        "C-content",
        "C-footer",
    ]

    actual_initial = [child.text for child in app_el.children]
    assert actual_initial == expected_initial, f"Initial order wrong: {actual_initial}"

    # Reorder: C, A, B
    state["items"] = [
        {"id": "C"},
        {"id": "A"},
        {"id": "B"},
    ]

    # CRITICAL: Verify the elements maintain correct order within each component
    # AND the components are in the correct order
    expected_after = [
        "C-header",
        "C-content",
        "C-footer",  # C's elements in order
        "A-header",
        "A-content",
        "A-footer",  # A's elements in order
        "B-header",
        "B-content",
        "B-footer",  # B's elements in order
    ]

    actual_after = [child.text for child in app_el.children]
    assert actual_after == expected_after, (
        f"After reordering, expected {expected_after} but got {actual_after}"
    )


def test_mixed_component_element_component(parse_source):
    """
    Test component with pattern: Component, element, Component at root.
    """
    InnerComp, _ = parse_source(
        """
        <inner :id="props['id']" />

        <script>
        import collagraph as cg

        class InnerComp(cg.Component):
            pass
        </script>
        """
    )

    MixedRoot, mixed_module = parse_source(
        """
        <InnerComp :id="props['id'] + '-inner1'" />
        <divider :id="props['id'] + '-divider'" />
        <InnerComp :id="props['id'] + '-inner2'" />

        <script>
        import collagraph as cg

        try:
            import InnerComp
        except:
            pass

        class MixedRoot(cg.Component):
            pass
        </script>
        """
    )

    App, module = parse_source(
        """
        <app>
            <MixedRoot
                v-for="item in items"
                :key="item['id']"
                :id="item['id']"
            />
        </app>

        <script>
        import collagraph as cg

        try:
            import MixedRoot
        except:
            pass

        class App(cg.Component):
            pass
        </script>
        """
    )

    mixed_module["InnerComp"] = InnerComp
    module["MixedRoot"] = MixedRoot

    renderer = CustomElementRenderer()
    container = CustomElement(type="root")
    state = reactive(
        {
            "items": [
                {"id": "X"},
                {"id": "Y"},
            ]
        }
    )

    gui = Collagraph(
        renderer=renderer,
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    app_el = container.children[0]

    # Each MixedRoot has 3 children: inner, divider, inner
    # So we expect 6 elements total
    assert len(app_el.children) == 6

    expected_initial = [
        "X-inner1",
        "X-divider",
        "X-inner2",
        "Y-inner1",
        "Y-divider",
        "Y-inner2",
    ]

    actual_initial = [child.id for child in app_el.children]
    assert actual_initial == expected_initial, f"Initial order wrong: {actual_initial}"

    # Reverse order
    state["items"] = [
        {"id": "Y"},
        {"id": "X"},
    ]

    expected_after = [
        "Y-inner1",
        "Y-divider",
        "Y-inner2",
        "X-inner1",
        "X-divider",
        "X-inner2",
    ]

    actual_after = [child.id for child in app_el.children]
    assert actual_after == expected_after, (
        f"After reordering, expected {expected_after} but got {actual_after}"
    )
