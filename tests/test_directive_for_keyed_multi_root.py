"""Test v-for directive with keys - multi-root components."""

from observ import reactive

from collagraph import Collagraph, EventLoopType
from tests.conftest import CustomElement, CustomElementRenderer


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

    # Verify initial structure - should be 9 elements total
    # (3 components x 3 elements each)
    assert len(app_el.children) == 9, f"Expected 9 elements, got {len(app_el.children)}"

    # Verify order of elements: A, B, C
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
        <divider :text="props['id'] + '-divider'" />
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

    # Extract identifier from each child (id or text depending on element type)
    actual_initial = [
        child._data.get("id") or child._data.get("text") for child in app_el.children
    ]
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

    # Extract identifier from each child (id or text depending on element type)
    actual_after = [
        child._data.get("id") or child._data.get("text") for child in app_el.children
    ]
    assert actual_after == expected_after, (
        f"After reordering, expected {expected_after} but got {actual_after}"
    )
