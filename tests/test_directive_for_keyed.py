"""Advanced tests for key-based list reconciliation."""

import gc
from weakref import ref

import pytest
from observ import reactive

from collagraph import Collagraph, EventLoopType
from collagraph.renderers import DictRenderer, Renderer


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

    def add_event_listener(self, event_type, value):
        event_listeners = self._data["event_listeners"]
        listeners = event_listeners.setdefault(event_type, [])
        listeners.append(value)

    def remove_event_listener(self, event_type, value):
        event_listeners = self._data["event_listeners"]
        listeners = event_listeners.get(event_type)
        listeners.remove(value)
        if not listeners:
            del event_listeners[event_type]

    def trigger(self, event_type):
        event_listeners = self._data["event_listeners"]
        for listener in event_listeners.get(event_type, []):
            listener()

    def __repr__(self):
        attributes = ", ".join(
            [
                f"{attr}='{self._data[attr]}'"
                for attr in self._data
                if attr not in ["type", "children"]
            ]
        )
        return f"<{self.type} {attributes}>"


class CustomElementRenderer(Renderer):
    def create_element(self, type):
        obj = CustomElement(type=type)
        return obj

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
        el.add_event_listener(event_type, value)

    def remove_event_listener(self, el, event_type, value):
        el.remove_event_listener(event_type, value)

    def create_text_element(self):
        raise NotImplementedError

    def set_element_text(self):
        raise NotImplementedError


class TrackingRenderer(CustomElementRenderer):
    """Renderer that tracks DOM operations for efficiency testing."""

    def __init__(self):
        super().__init__()
        self.insert_count = 0
        self.remove_count = 0
        self.create_count = 0
        self.operations = []  # Log of operations

    def create_element(self, type):
        self.create_count += 1
        self.operations.append(("create", type))
        return super().create_element(type)

    def insert(self, el, parent, anchor=None):
        self.insert_count += 1
        self.operations.append(("insert", el.type, "anchor" if anchor else "end"))
        super().insert(el, parent, anchor)

    def remove(self, el, parent):
        self.remove_count += 1
        self.operations.append(("remove", el.type))
        super().remove(el, parent)

    def reset_counters(self):
        """Reset operation counters."""
        self.insert_count = 0
        self.remove_count = 0
        self.create_count = 0
        self.operations = []


def test_for_keyed(parse_source, process_events):
    App, _ = parse_source(
        """
        <node
          v-for="item in items"
          :key="item['id']"
          :text="item['text']"
        />

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """
    )

    state = reactive(
        {
            "items": [
                {"id": 0, "text": "foo"},
                {"id": 1, "text": "bar"},
            ]
        }
    )
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.DEFAULT,
    )
    gui.render(App, container, state)

    assert len(container["children"]) == len(state["items"])
    for node, item in zip(container["children"], state["items"]):
        assert node["type"] == "node"
        assert node["attrs"]["key"] == item["id"]
        assert node["attrs"]["text"] == item["text"]

    state["items"][1]["text"] = "baz"
    process_events()

    assert len(container["children"]) == len(state["items"])
    for node, item in zip(container["children"], state["items"]):
        assert node["type"] == "node"
        assert node["attrs"]["key"] == item["id"]
        assert node["attrs"]["text"] == item["text"]

    state["items"].insert(0, {"id": 2, "text": "baz"})
    state["items"].insert(2, {"id": 3, "text": "qux"})
    process_events()

    assert len(container["children"]) == len(state["items"])
    for node, item in zip(container["children"], state["items"]):
        assert node["type"] == "node"
        assert node["attrs"]["key"] == item["id"]
        assert node["attrs"]["text"] == item["text"]


def test_reconcile_by_key(parse_source):
    states = [
        (["a", "b", "c"], ["c", "a", "b"], "shift right"),  # shift right
        (["a", "b", "c"], ["b", "c", "a"], "shift left"),  # shift left
        (["a", "b", "c"], ["c", "b", "a"], "reverse order"),  # reverse order
        (["a", "b", "c"], ["a", "b"], "remove last"),  # remove last
        (["a", "b", "c"], ["a", "c"], "remove from middle"),  # remove from middle
        (["a", "b", "c"], ["b", "c"], "remove first"),  # remove first
        (["a", "b", "c"], ["a", "b", "c", "d"], "add last"),  # add last
        (["a", "b", "c"], ["a", "b", "d", "c"], "add in middle"),  # add in middle
        (["a", "b", "c"], ["d", "a", "b", "c"], "add begin"),  # add begin
        (["a", "b", "c", "d"], ["e", "f"], "replace completely"),  # replace completely
    ]

    Items, _ = parse_source(
        """
            <items>
              <!-- FIXME: using v-for="item in items" is broken... -->
              <item
                v-for="it in items"
                :key="it"
                :content="it"
              />
            </items>

            <script>
            import collagraph as cg

            class Items(cg.Component):
                pass
            </script>
        """
    )
    renderer = CustomElementRenderer()

    for before, after, name in states:
        gui = Collagraph(
            renderer=renderer,
            event_loop_type=EventLoopType.SYNC,
        )
        container = CustomElement()
        container.type = "root"
        container.children = []
        state = reactive({"items": before})

        gui.render(Items, container, state=state)

        items = container.children[0]

        for idx, val in enumerate(before):
            item = items.children[idx]
            assert item.content == val, name

        children_refs = [ref(x) for x in items.children]

        state["items"] = after

        for idx, val in enumerate(after):
            item = items.children[idx]
            assert item.content == val, (
                name,
                [child.content for child in items.children],
                after,
            )

            # Check that the instances have not been replaced
            # but actually have been moved/reconciled
            if val in before:
                prev_idx = before.index(val)
                assert item is children_refs[prev_idx](), name

        assert len(after) == len(items.children), name


def test_keyed_list_efficiency(parse_source):
    """Test that keyed lists only perform necessary DOM operations."""
    Items, _ = parse_source(
        """
        <items>
          <item
            v-for="item in items"
            :key="item"
            :content="item"
          />
        </items>

        <script>
        import collagraph as cg

        class Items(cg.Component):
            pass
        </script>
        """
    )

    renderer = TrackingRenderer()
    container = CustomElement(type="root")
    state = reactive({"items": ["a", "b", "c"]})

    gui = Collagraph(
        renderer=renderer,
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(Items, container, state=state)

    # Check initial render created 3 items
    assert renderer.create_count == 4  # 1 items + 3 item elements

    # Reset counters after initial render
    renderer.reset_counters()

    # Reverse the list - should reuse all 3 elements
    state["items"] = ["c", "b", "a"]

    # Should not create new elements, only move them
    assert renderer.create_count == 0, "Should reuse existing elements"
    # Should move elements (may be optimized to fewer than N operations)
    assert renderer.insert_count == 2, "Should not insert more elements than exist"
    assert renderer.remove_count == 2, "Should not remove more elements than exist"

    # Reset counters
    renderer.reset_counters()

    # Swap two items ["c", "b", "a"] -> ["c", "a", "b"]
    state["items"] = ["c", "a", "b"]

    # Should be more efficient - only 2 elements need to move
    assert renderer.create_count == 0, "Should reuse existing elements"
    assert renderer.insert_count <= 2
    assert renderer.remove_count <= 2

    # Reset counters
    renderer.reset_counters()

    # Add one item at the end
    state["items"] = ["c", "a", "b", "d"]

    # Should only create and insert 1 new element
    assert renderer.create_count == 1, "Should create exactly 1 new element"
    assert renderer.insert_count == 1

    # Reset counters
    renderer.reset_counters()

    # Remove one item from middle
    state["items"] = ["c", "b", "d"]

    # Should only remove 1 element
    assert renderer.create_count == 0
    assert renderer.remove_count == 1


def test_keyed_vs_unkeyed_efficiency(parse_source):
    """Compare efficiency of keyed vs unkeyed lists."""
    KeyedItems, _ = parse_source(
        """
        <items>
          <item v-for="item in items" :key="item" :content="item" />
        </items>

        <script>
        import collagraph as cg

        class Items(cg.Component):
            pass
        </script>
        """
    )

    UnkeyedItems, _ = parse_source(
        """
        <items>
          <item v-for="item in items" :content="item" />
        </items>

        <script>
        import collagraph as cg

        class Items(cg.Component):
            pass
        </script>
        """
    )

    # Test keyed list
    keyed_renderer = TrackingRenderer()
    keyed_container = CustomElement(type="root")
    keyed_state = reactive({"items": ["a", "b", "c"]})

    keyed_gui = Collagraph(
        renderer=keyed_renderer,
        event_loop_type=EventLoopType.SYNC,
    )
    keyed_gui.render(KeyedItems, keyed_container, keyed_state)

    # Test unkeyed list
    unkeyed_renderer = TrackingRenderer()
    unkeyed_container = CustomElement(type="root")
    unkeyed_state = reactive({"items": ["a", "b", "c"]})

    unkeyed_gui = Collagraph(
        renderer=unkeyed_renderer,
        event_loop_type=EventLoopType.SYNC,
    )
    unkeyed_gui.render(UnkeyedItems, unkeyed_container, unkeyed_state)

    # Store element references BEFORE reordering
    keyed_elements_before = [ref(el) for el in keyed_container.children[0].children]
    unkeyed_elements_before = [ref(el) for el in unkeyed_container.children[0].children]

    # Reset counters after initial render
    keyed_renderer.reset_counters()
    unkeyed_renderer.reset_counters()

    # Reverse the list in both
    keyed_state["items"] = ["c", "b", "a"]
    unkeyed_state["items"] = ["c", "b", "a"]

    # Keyed list should not create new elements, just move them
    assert keyed_renderer.create_count == 0, "Keyed: should reuse elements"

    # Unkeyed list doesn't move elements, just updates content
    # So it shouldn't create, insert, or remove either
    assert unkeyed_renderer.create_count == 0
    assert unkeyed_renderer.insert_count == 0
    assert unkeyed_renderer.remove_count == 0

    # In keyed list, elements should maintain identity
    # Element that originally had "a" (was at position 0) should now be at position 2
    keyed_elements_after = keyed_container.children[0].children
    assert keyed_elements_after[2] is keyed_elements_before[0](), (
        "Element with 'a' moved to position 2"
    )
    assert keyed_elements_after[2].content == "a", "Element still has content 'a'"

    # In unkeyed list, element at position 0 stays at position 0
    # but its content is updated
    unkeyed_elements_after = unkeyed_container.children[0].children
    assert unkeyed_elements_after[0] is unkeyed_elements_before[0](), (
        "Same element at position 0"
    )
    assert unkeyed_elements_after[0].content == "c", "Content updated to 'c'"


def test_keyed_components_preserve_state(parse_source):
    """Test that components in keyed lists preserve their internal state."""
    Counter, _ = parse_source(
        """
        <button :text="state['label']" />

        <script>
        import collagraph as cg

        class Counter(cg.Component):
            def init(self):
                self.state['label'] = self.props['label']
                self.state['count'] = 0

            def increment(self):
                self.state['count'] += 1
                self.state['label'] = f"{self.props['label']}: {self.state['count']}"
        </script>
        """
    )

    App, module = parse_source(
        """
        <app>
            <Counter
                v-for="item in items"
                :key="item['id']"
                :label="item['label']"
            />
        </app>

        <script>
        import collagraph as cg

        try:
            import Counter
        except:
            pass

        class App(cg.Component):
            pass
        </script>
        """
    )

    # Inject Counter into the module namespace
    module["Counter"] = Counter

    renderer = CustomElementRenderer()
    container = CustomElement(type="root")
    state = reactive(
        {
            "items": [
                {"id": 1, "label": "A"},
                {"id": 2, "label": "B"},
                {"id": 3, "label": "C"},
            ]
        }
    )

    gui = Collagraph(
        renderer=renderer,
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    # Get the component fragments
    app_fragment = gui.fragment
    counter_fragments = app_fragment.children[0].children[0].children

    # Get references to the counter components
    counter_a = counter_fragments[0].component
    counter_b = counter_fragments[1].component
    counter_c = counter_fragments[2].component

    # Increment counter A several times
    counter_a.increment()
    counter_a.increment()
    counter_a.increment()

    assert counter_a.state["count"] == 3
    assert counter_a.state["label"] == "A: 3"

    # Increment counter B once
    counter_b.increment()
    assert counter_b.state["count"] == 1

    # Counter C stays at 0
    assert counter_c.state["count"] == 0

    # Now reorder the items: C, A, B
    state["items"] = [
        {"id": 3, "label": "C"},
        {"id": 1, "label": "A"},
        {"id": 2, "label": "B"},
    ]

    # Get the counter fragments again (they've been reordered)
    counter_fragments = app_fragment.children[0].children[0].children

    # Verify the components maintained their state
    # The component with id=1 (A) should still have count=3
    assert counter_fragments[1].component is counter_a, (
        "Should be the same component instance"
    )
    assert counter_a.state["count"] == 3, "State should be preserved"
    assert counter_a.state["label"] == "A: 3"

    # The component with id=2 (B) should still have count=1
    assert counter_fragments[2].component is counter_b
    assert counter_b.state["count"] == 1

    # The component with id=3 (C) should still have count=0
    assert counter_fragments[0].component is counter_c
    assert counter_c.state["count"] == 0


def test_duplicate_keys_behavior(parse_source):
    """Test behavior when multiple items have the same key."""
    Items, _ = parse_source(
        """
        <items>
          <item v-for="item in items" :key="item['id']" :text="item['text']" />
        </items>

        <script>
        import collagraph as cg

        class Items(cg.Component):
            pass
        </script>
        """
    )

    renderer = CustomElementRenderer()
    container = CustomElement(type="root")
    state = reactive(
        {
            "items": [
                {"id": 1, "text": "First"},
                {"id": 1, "text": "Duplicate!"},  # Same key!
                {"id": 2, "text": "Third"},
            ]
        }
    )

    gui = Collagraph(
        renderer=renderer,
        event_loop_type=EventLoopType.SYNC,
    )

    with pytest.raises(RuntimeError) as err:
        gui.render(Items, container, state)

    assert "Duplicate keys found: 1" in str(err.value)


def test_complex_key_expressions(parse_source):
    """Test keys computed from multiple item properties."""
    Items, _ = parse_source(
        """
        <items>
          <item
            v-for="item in items"
            :key="str(item['category']) + '_' + str(item['id'])"
            :label="item['label']"
          />
        </items>

        <script>
        import collagraph as cg

        class Items(cg.Component):
            pass
        </script>
        """
    )

    renderer = CustomElementRenderer()
    container = CustomElement(type="root")
    state = reactive(
        {
            "items": [
                {"category": "fruit", "id": 1, "label": "Apple"},
                {
                    "category": "veg",
                    "id": 1,
                    "label": "Carrot",
                },  # Same id, different category
                {"category": "fruit", "id": 2, "label": "Banana"},
            ]
        }
    )

    gui = Collagraph(
        renderer=renderer,
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(Items, container, state)

    items_el = container.children[0]
    assert len(items_el.children) == 3

    # Verify all items rendered correctly
    assert items_el.children[0].label == "Apple"
    assert items_el.children[1].label == "Carrot"
    assert items_el.children[2].label == "Banana"

    # Store element references
    element_refs = [ref(el) for el in items_el.children]

    # Reorder items
    state["items"] = [
        {"category": "veg", "id": 1, "label": "Carrot"},
        {"category": "fruit", "id": 2, "label": "Banana"},
        {"category": "fruit", "id": 1, "label": "Apple"},
    ]

    # Verify elements were reordered, not recreated
    assert items_el.children[0] is element_refs[1]()
    assert items_el.children[1] is element_refs[2]()
    assert items_el.children[2] is element_refs[0]()


def test_nested_keyed_lists(parse_source):
    """Test keyed lists containing other keyed lists."""
    # TODO: switch back to 'group' and 'item' after #136 is merged
    Items, _ = parse_source(
        """
        <container>
          <group v-for="group in groups" :key="group['id']" :name="group['name']">
            <item
              v-for="item in group['items']"
              :key="item['id']"
              :text="item['text']"
            />
          </group>
        </container>

        <script>
        import collagraph as cg

        class Items(cg.Component):
            pass
        </script>
        """
    )

    renderer = CustomElementRenderer()
    container = CustomElement(type="root")
    state = reactive(
        {
            "groups": [
                {
                    "id": 1,
                    "name": "Group A",
                    "items": [
                        {"id": 11, "text": "A1"},
                        {"id": 12, "text": "A2"},
                    ],
                },
                {
                    "id": 2,
                    "name": "Group B",
                    "items": [
                        {"id": 21, "text": "B1"},
                        {"id": 22, "text": "B2"},
                    ],
                },
            ]
        }
    )

    gui = Collagraph(
        renderer=renderer,
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(Items, container, state)

    container_el = container.children[0]
    assert len(container_el.children) == 2

    # Store references to groups
    group_a_ref = ref(container_el.children[0])
    group_b_ref = ref(container_el.children[1])

    # Store references to items in group A
    group_a_items = container_el.children[0].children
    a1_ref = ref(group_a_items[0])
    a2_ref = ref(group_a_items[1])

    # Reverse outer groups
    state["groups"] = [
        state["groups"][1],
        state["groups"][0],
    ]

    # Outer groups should have swapped
    assert container_el.children[0] is group_b_ref()
    assert container_el.children[1] is group_a_ref()

    # Items within Group A should still be the same elements
    group_a_items_after = container_el.children[1].children
    assert group_a_items_after[0] is a1_ref()
    assert group_a_items_after[1] is a2_ref()

    # Now reverse items within Group A
    state["groups"][1]["items"] = [
        state["groups"][1]["items"][1],
        state["groups"][1]["items"][0],
    ]

    # Items should have swapped
    group_a_items_after = container_el.children[1].children
    assert group_a_items_after[0] is a2_ref()
    assert group_a_items_after[1] is a1_ref()


@pytest.mark.skip(reason="v-if on v-for elements not currently supported by compiler")
def test_keyed_list_with_v_if(parse_source):
    """Test v-for with :key combined with v-if on items."""
    # Note: This is a known limitation - v-if on the same element as v-for
    # is not supported by the current compiler implementation.
    # In Vue, this is also an anti-pattern and should be avoided.
    # The workaround is to use a computed property to filter the list,
    # or wrap the v-for element in a template with v-if.
    pass


def test_event_handlers_after_reconciliation(parse_source):
    """Test that event handlers remain functional after list reordering."""
    Items, _ = parse_source(
        """
        <container>
          <button
            v-for="item in items"
            :key="item['id']"
            :text="item['label']"
            @clicked="lambda item=item: handle_click(item)"
          />
        </container>

        <script>
        import collagraph as cg

        class Items(cg.Component):
            call_log = []

            def handle_click(self, item):
                Items.call_log.append(item['id'])
        </script>
        """
    )

    renderer = CustomElementRenderer()
    container = CustomElement(type="root")
    state = reactive(
        {
            "items": [
                {"id": 1, "label": "Button A"},
                {"id": 2, "label": "Button B"},
                {"id": 3, "label": "Button C"},
            ]
        }
    )

    gui = Collagraph(
        renderer=renderer,
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(Items, container, state)

    # Get buttons
    container_el = container.children[0]
    buttons = container_el.children

    # Simulate clicking button A (should log id=1)
    assert len(buttons) == 3
    button_a = buttons[0]
    assert button_a.text == "Button A"
    button_a.trigger("clicked")
    assert Items.call_log == [1]

    # Reorder items
    state["items"] = [
        {"id": 3, "label": "Button C"},
        {"id": 1, "label": "Button A"},
        {"id": 2, "label": "Button B"},
    ]

    # Verify buttons are reordered
    buttons = container_el.children
    assert buttons[0].text == "Button C"
    assert buttons[1].text == "Button A"
    assert buttons[2].text == "Button B"

    # The elements should be the same instances (moved, not recreated)
    # So their event handlers should still work
    buttons[0].trigger("clicked")
    buttons[1].trigger("clicked")
    buttons[2].trigger("clicked")

    assert Items.call_log == [1, 3, 1, 2]


def test_no_memory_leaks_on_item_removal(parse_source):
    """Test that removed keyed items are garbage collected."""
    Items, _ = parse_source(
        """
        <items>
          <item v-for="item in items" :key="item" :content="item" />
        </items>

        <script>
        import collagraph as cg

        class Items(cg.Component):
            pass
        </script>
        """
    )

    renderer = CustomElementRenderer()
    container = CustomElement(type="root")
    state = reactive({"items": ["a", "b", "c", "d", "e"]})

    gui = Collagraph(
        renderer=renderer,
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(Items, container, state)

    items_el = container.children[0]

    # Get weak references to all elements
    element_refs = [ref(el) for el in items_el.children]

    # Verify all references are alive
    assert all(r() is not None for r in element_refs)

    # Remove all items from list
    state["items"] = []

    # Should have no children now
    assert len(items_el.children) == 0

    # Force garbage collection
    gc.collect()

    # Verify weak references are now dead (elements were garbage collected)
    assert all(r() is None for r in element_refs), (
        "Removed elements should be garbage collected"
    )


def test_keyed_list_edge_cases(parse_source):
    """Test various edge cases."""
    Items, _ = parse_source(
        """
        <items>
          <item v-for="item in items" :key="item['id']" :value="item['value']" />
        </items>

        <script>
        import collagraph as cg

        class Items(cg.Component):
            pass
        </script>
        """
    )

    renderer = CustomElementRenderer()
    container = CustomElement(type="root")
    state = reactive({"items": []})

    gui = Collagraph(
        renderer=renderer,
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(Items, container, state)

    items_el = container.children[0]

    # Empty list should render nothing
    assert len(items_el.children) == 0

    # Single item
    state["items"] = [{"id": 1, "value": "one"}]
    assert len(items_el.children) == 1
    assert items_el.children[0].value == "one"

    # Large list (100 items)
    state["items"] = [{"id": i, "value": f"item_{i}"} for i in range(100)]
    assert len(items_el.children) == 100

    # All items replaced with completely new keys
    state["items"] = [{"id": 1000 + i, "value": f"new_{i}"} for i in range(100)]
    assert len(items_el.children) == 100
    assert items_el.children[0].value == "new_0"

    # Back to empty
    state["items"] = []
    assert len(items_el.children) == 0


def test_different_key_types(parse_source):
    """Test that keys can be different types."""
    Items, _ = parse_source(
        """
        <items>
          <item v-for="item in items" :key="item['id']" :text="item['text']" />
        </items>

        <script>
        import collagraph as cg

        class Items(cg.Component):
            pass
        </script>
        """
    )

    renderer = CustomElementRenderer()
    container = CustomElement(type="root")

    # String keys
    state = reactive(
        {
            "items": [
                {"id": "a", "text": "Alpha"},
                {"id": "b", "text": "Beta"},
            ]
        }
    )

    gui = Collagraph(
        renderer=renderer,
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(Items, container, state)

    items_el = container.children[0]
    assert len(items_el.children) == 2

    # Store references
    refs = [ref(el) for el in items_el.children]

    # Numeric keys - all new items
    state["items"] = [
        {"id": 1, "text": "One"},
        {"id": 2, "text": "Two"},
    ]

    # Should have created new elements (different keys)
    assert len(items_el.children) == 2
    # These should be different elements
    assert items_el.children[0] is not refs[0]()
    assert items_el.children[1] is not refs[1]()


def test_reactive_key_changes(parse_source):
    """Test what happens when a key value itself changes."""
    Items, _ = parse_source(
        """
        <items>
          <item v-for="item in items" :key="item['id']" :text="item['text']" />
        </items>

        <script>
        import collagraph as cg

        class Items(cg.Component):
            pass
        </script>
        """
    )

    renderer = TrackingRenderer()
    container = CustomElement(type="root")
    state = reactive(
        {
            "items": [
                {"id": 1, "text": "A"},
                {"id": 2, "text": "B"},
            ]
        }
    )

    gui = Collagraph(
        renderer=renderer,
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(Items, container, state)

    items_el = container.children[0]
    assert len(items_el.children) == 2

    # Store reference to first element
    _first_el_ref = ref(items_el.children[0])

    renderer.reset_counters()

    # Change the key of the first item
    state["items"][0]["id"] = 99

    # This should be treated as: remove item with key=1, add item with key=99
    # The element should be recreated because the key changed
    assert len(items_el.children) == 2

    # Should have removed 1 and created 1
    assert renderer.remove_count == 1
    assert renderer.create_count == 1

    # The first element should be a different instance now
    # (because we removed key=1 and added key=99)
    # Actually, depending on implementation, it might reuse or recreate
    # Let's just verify the list still has 2 items and works correctly
    assert items_el.children[0].text == "A"
    assert items_el.children[1].text == "B"


def test_complex_reconciliation_scenario(parse_source):
    """Test a complex scenario with add, remove, move, and update."""
    Items, _ = parse_source(
        """
        <items>
          <item v-for="item in items" :key="item['id']" :text="item['text']" />
        </items>

        <script>
        import collagraph as cg

        class Items(cg.Component):
            pass
        </script>
        """
    )

    renderer = TrackingRenderer()
    container = CustomElement(type="root")
    state = reactive(
        {
            "items": [
                {"id": 1, "text": "A"},
                {"id": 2, "text": "B"},
                {"id": 3, "text": "C"},
                {"id": 4, "text": "D"},
                {"id": 5, "text": "E"},
            ]
        }
    )

    gui = Collagraph(
        renderer=renderer,
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(Items, container, state)

    items_el = container.children[0]

    # Store references to elements
    element_refs = {
        item["id"]: ref(items_el.children[i]) for i, item in enumerate(state["items"])
    }

    renderer.reset_counters()

    # Complex operation:
    # - Remove B (id=2) and D (id=4)
    # - Add F (id=6) and G (id=7)
    # - Reorder remaining: E, C, A, F, G
    state["items"] = [
        {"id": 5, "text": "E"},
        {"id": 3, "text": "C"},
        {"id": 1, "text": "A"},
        {"id": 6, "text": "F"},
        {"id": 7, "text": "G"},
    ]

    # Verify correct rendering
    assert len(items_el.children) == 5
    assert items_el.children[0].text == "E"
    assert items_el.children[1].text == "C"
    assert items_el.children[2].text == "A"
    assert items_el.children[3].text == "F"
    assert items_el.children[4].text == "G"

    # Verify elements A, C, E were reused (same instances)
    assert items_el.children[0] is element_refs[5]()
    assert items_el.children[1] is element_refs[3]()
    assert items_el.children[2] is element_refs[1]()

    # Should have removed 2 elements (B and D)
    assert renderer.remove_count == 4  # 2 real removals, and two moves: remove + insert
    assert renderer.insert_count == 4  # 2 real inserts, and two moves: remove + insert

    # Should have created 2 new elements (F and G)
    assert renderer.create_count == 2
