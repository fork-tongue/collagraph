"""Test v-for directive with keys - nested components."""

from observ import reactive

from collagraph import Collagraph, EventLoopType
from tests.conftest import CustomElement, CustomElementRenderer


def test_nested_components_with_complex_hierarchy(parse_source):
    """
    Test reordering of components that contain:
    - Multiple child elements
    - Nested components
    - Mixed hierarchies
    """
    # Inner component that renders a container with nested content
    InnerWidget, _ = parse_source(
        """
        <inner-container :id="props['id']">
            <label :text="state['label']" />
            <value :text="props['value']" />
        </inner-container>

        <script>
        import collagraph as cg

        class InnerWidget(cg.Component):
            def init(self):
                self.state['label'] = f"Label {self.props['id']}"
        </script>
        """
    )

    # Outer component that contains multiple elements and a nested component
    Card, card_module = parse_source(
        """
        <card :id="props['id']">
            <header :text="state['title']" />
            <InnerWidget :id="props['id']" :value="state['count']" />
            <footer :text="state['footer']" />
        </card>

        <script>
        import collagraph as cg

        try:
            import InnerWidget
        except:
            pass

        class Card(cg.Component):
            def init(self):
                self.state['title'] = f"Card {self.props['id']}"
                self.state['count'] = 0
                self.state['footer'] = "Footer"

            def increment(self):
                self.state['count'] += 1
        </script>
        """
    )

    App, module = parse_source(
        """
        <app>
            <Card
                v-for="item in items"
                :key="item['id']"
                :id="item['id']"
            />
        </app>

        <script>
        import collagraph as cg

        try:
            import Card
        except:
            pass

        class App(cg.Component):
            pass
        </script>
        """
    )

    # Inject components into appropriate namespaces
    card_module["InnerWidget"] = InnerWidget
    module["Card"] = Card

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

    # Get the app container
    app_el = container.children[0]

    # Verify initial structure
    assert len(app_el.children) == 3, "Should have 3 cards"

    # Check first card structure
    card_a = app_el.children[0]
    assert card_a.type == "card"
    assert card_a.id == "A"
    assert len(card_a.children) == 3  # header, inner-container, footer
    assert card_a.children[0].type == "header"
    assert card_a.children[1].type == "inner-container"
    assert card_a.children[2].type == "footer"

    # Check inner-container structure
    inner_a = card_a.children[1]
    assert inner_a.id == "A"
    assert len(inner_a.children) == 2  # label, value
    assert inner_a.children[0].type == "label"
    assert inner_a.children[1].type == "value"

    # Get component references
    app_fragment = gui.fragment
    card_fragments = app_fragment.children[0].children[0].children
    card_comp_a = card_fragments[0].component
    card_comp_b = card_fragments[1].component
    card_comp_c = card_fragments[2].component

    # Modify state
    card_comp_a.increment()
    card_comp_a.increment()  # A: count = 2
    card_comp_b.increment()  # B: count = 1

    # Verify state changes reflected in DOM
    assert app_el.children[0].children[1].children[1].text == 2
    assert app_el.children[1].children[1].children[1].text == 1
    assert app_el.children[2].children[1].children[1].text == 0

    # Now reorder: C, A, B
    state["items"] = [
        {"id": "C"},
        {"id": "A"},
        {"id": "B"},
    ]

    # Verify components maintained their state
    card_fragments = app_fragment.children[0].children[0].children
    assert card_fragments[0].component is card_comp_c
    assert card_fragments[1].component is card_comp_a
    assert card_fragments[2].component is card_comp_b

    assert card_comp_a.state["count"] == 2
    assert card_comp_b.state["count"] == 1
    assert card_comp_c.state["count"] == 0

    # CRITICAL: Verify DOM order is correct
    assert len(app_el.children) == 3

    # Check card order
    assert app_el.children[0].id == "C", "First card should be C"
    assert app_el.children[1].id == "A", "Second card should be A"
    assert app_el.children[2].id == "B", "Third card should be B"

    # Verify nested structure is intact for reordered card A
    card_a_after = app_el.children[1]
    assert card_a_after.type == "card"
    assert len(card_a_after.children) == 3
    assert card_a_after.children[0].type == "header"
    assert card_a_after.children[0].text == "Card A"
    assert card_a_after.children[1].type == "inner-container"
    assert card_a_after.children[1].id == "A"
    assert card_a_after.children[2].type == "footer"

    # Verify nested inner component structure
    inner_a_after = card_a_after.children[1]
    assert len(inner_a_after.children) == 2
    assert inner_a_after.children[0].type == "label"
    assert inner_a_after.children[0].text == "Label A"
    assert inner_a_after.children[1].type == "value"
    assert inner_a_after.children[1].text == 2  # State preserved!

    # Verify all cards maintain correct nested structure
    for i, card_id in enumerate(["C", "A", "B"]):
        card = app_el.children[i]
        assert card.id == card_id
        inner = card.children[1]
        assert inner.id == card_id
        assert len(inner.children) == 2
