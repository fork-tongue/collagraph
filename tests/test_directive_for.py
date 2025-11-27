from observ import reactive

from collagraph import Collagraph, EventLoopType
from collagraph.renderers import DictRenderer
from collagraph.renderers.dict_renderer import format_dict


def test_for_simple(parse_source):
    """
    Render a node with a 1_000 children.
    This ensures that collagraph will not trigger a RecursionError.
    """
    number_of_items = 1_000
    App, _ = parse_source(
        f"""
        <node
          v-for="i in range({number_of_items})"
          :value="i"
        />

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """
    )

    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container)

    assert len(container["children"]) == number_of_items, format_dict(container)
    for idx, child in enumerate(container["children"]):
        assert child["attrs"]["value"] == idx


def test_for_with_children(parse_source):
    values = ["a", "b", "c"]
    App, _ = parse_source(
        f"""
        <node
          v-for="i, text in enumerate({values})"
          :value="i"
        >
          <item :text="text" />
        </node>

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """
    )

    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container)

    assert len(container["children"]) == len(values), format_dict(container)
    for idx, child in enumerate(container["children"]):
        assert child["attrs"]["value"] == idx
        assert child["children"][0]["attrs"]["text"] == values[idx]


def test_for_between_other_tags(parse_source):
    App, _ = parse_source(
        """
        <foo />
        <node
          v-for="i in values"
          :value="i"
        />
        <bar />

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """
    )

    container = {"type": "root"}
    state = reactive({"values": list(range(10))})
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    assert len(container["children"]) == len(state["values"]) + 2
    assert container["children"][0]["type"] == "foo"
    assert container["children"][-1]["type"] == "bar"
    for child in container["children"][1:-1]:
        assert child["type"] == "node"

    state["values"].append(len(state["values"]))

    # Test response to changes in size of v-for
    assert len(container["children"]) == len(state["values"]) + 2
    assert container["children"][0]["type"] == "foo"
    assert container["children"][-1]["type"] == "bar"
    for child in container["children"][1:-1]:
        assert child["type"] == "node"

    state["values"].pop(3)
    state["values"].pop(3)

    assert len(container["children"]) == len(state["values"]) + 2
    assert container["children"][0]["type"] == "foo"
    assert container["children"][-1]["type"] == "bar"
    for child in container["children"][1:-1]:
        assert child["type"] == "node"

    state["values"].clear()

    assert len(container["children"]) == len(state["values"]) + 2
    assert container["children"][0]["type"] == "foo"
    assert container["children"][-1]["type"] == "bar"
    for child in container["children"][1:-1]:
        assert child["type"] == "node"

    state["values"] = [1, 2, 3]

    assert len(container["children"]) == len(state["values"]) + 2
    assert container["children"][0]["type"] == "foo"
    assert container["children"][-1]["type"] == "bar"
    for child in container["children"][1:-1]:
        assert child["type"] == "node"


def test_for_between_if_tags(parse_source):
    App, _ = parse_source(
        """
        <foo v-if="foo" />
        <node
          v-for="i in range(10)"
          :value="i"
        />
        <bar v-if="bar" />

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """
    )

    state = reactive(
        {
            "foo": False,
            "bar": False,
        }
    )
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    assert len(container["children"]) == 10
    for idx, child in enumerate(container["children"]):
        assert child["attrs"]["value"] == idx

    state["foo"] = True

    assert len(container["children"]) == 11
    assert container["children"][0]["type"] == "foo", format_dict(container)

    state["bar"] = True

    assert len(container["children"]) == 12
    assert container["children"][0]["type"] == "foo"
    assert container["children"][11]["type"] == "bar"


def test_for_simple_reactive(parse_source):
    App, _ = parse_source(
        """
        <node
          v-for="i in items"
          :value="i"
        />

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """
    )

    state = reactive({"items": ["a", "b"]})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    items = [child["attrs"]["value"] for child in container["children"]]
    assert items == state["items"], format_dict(container)

    state["items"][1] = "c"

    items = [child["attrs"]["value"] for child in container["children"]]
    assert items == state["items"], format_dict(container)


def test_for_reactive(parse_source):
    App, _ = parse_source(
        """
        <node
          v-for="i in items"
          :value="i"
        />

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """
    )

    state = reactive({"items": ["a", "b"]})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    items = [child["attrs"]["value"] for child in container["children"]]
    assert items == state["items"], format_dict(container)

    state["items"].append("c")

    items = [child["attrs"]["value"] for child in container["children"]]
    assert items == state["items"], format_dict(container)

    state["items"].pop(1)

    items = [child["attrs"]["value"] for child in container["children"]]
    assert items == state["items"], format_dict(container)

    state["items"] = ["d", "e"]

    items = [child["attrs"]["value"] for child in container["children"]]
    assert items == state["items"], format_dict(container)


def test_for_reactive_pop(parse_source):
    App, _ = parse_source(
        """
        <before />
        <node
          v-for="i in items"
          :value="i"
        />
        <after />

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """
    )

    state = reactive({"items": ["a", "b", "c"]})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)

    items = [child["attrs"]["value"] for child in container["children"][1:-1]]
    assert items == state["items"], format_dict(container)

    state["items"].pop()

    items = [child["attrs"]["value"] for child in container["children"][1:-1]]
    assert items == state["items"], format_dict(container)


def test_example(parse_source):
    App, _ = parse_source(
        """
        <node
          v-for="i, text in enumerate(props['items'])"
          :value="i + 1"
        >
          <item :text="text" :blaat="props['other']" />
        </node>

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """
    )

    state = reactive({"items": ["a", "b", "c"], "other": "toet"})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state)

    assert len(container["children"]) == 3
    assert container["children"][0]["attrs"]["value"] == 1
    assert container["children"][0]["children"][0]["attrs"]["text"] == "a"
    assert container["children"][0]["children"][0]["attrs"]["blaat"] == "toet"


def test_looped_example(parse_source):
    App, _ = parse_source(
        """
        <node
          v-for="i, text in enumerate(props['items'])"
          :value="text"
        >
          <item
            v-for="j, text in enumerate(props['items'])"
            :value="i * len(props['items']) + j"
            :content="text"
          />
        </node>

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """
    )

    state = reactive({"items": ["a", "b", "c"]})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state)

    assert len(container["children"]) == 3
    counter = 0
    for idx, value in enumerate(state["items"]):
        assert container["children"][idx]["attrs"]["value"] == value
        assert len(container["children"][idx]["children"]) == 3
        for child, val in zip(container["children"][idx]["children"], state["items"]):
            assert child["attrs"]["value"] == counter
            assert child["attrs"]["content"] == val
            counter += 1

    state["items"][2] = "d"

    assert len(container["children"]) == 3
    counter = 0
    for idx, value in enumerate(state["items"]):
        assert container["children"][idx]["attrs"]["value"] == value
        assert len(container["children"][idx]["children"]) == 3
        for child, val in zip(container["children"][idx]["children"], state["items"]):
            assert child["attrs"]["value"] == counter
            assert child["attrs"]["content"] == val
            counter += 1


def test_consecutive_lists(parse_source):
    App, _ = parse_source(
        """
        <node_a
          v-for="i, text in enumerate(a)"
          :index="i"
          :text="text"
        />
        <node_b
          v-for="i, text in enumerate(b)"
          :index="i"
          :text="text"
        />

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """
    )

    state = reactive({"a": ["a", "b", "c"], "b": ["x", "y", "z"]})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state)

    def assert_consistency():
        assert len(container["children"]) == len(state["a"]) + len(state["b"])
        for idx, value in enumerate(state["a"]):
            assert container["children"][idx]["type"] == "node_a", format_dict(
                container
            )
            assert container["children"][idx]["attrs"]["index"] == idx
            assert container["children"][idx]["attrs"]["text"] == value
        for idx, value in enumerate(state["b"]):
            child_idx = idx + len(state["a"])
            assert container["children"][child_idx]["type"] == "node_b"
            assert container["children"][child_idx]["attrs"]["index"] == idx
            assert container["children"][child_idx]["attrs"]["text"] == value, (
                format_dict(container)
            )

    assert_consistency()

    state["a"].pop()

    assert_consistency()

    state["a"].append("d")

    assert_consistency()

    state["a"][1] = "e"

    assert_consistency()

    state["b"].insert(0, "w")

    assert_consistency()


def test_for_regression(parse_source):
    _, namespace = parse_source(
        """
        <counter
          :count="count"
        />
        <script>
        import collagraph as cg
        class Counter(cg.Component):
            pass
        </script>
        """
    )
    Counters, namespace = parse_source(
        """
        <counters>
          <Counter
            v-for="i, prop in enumerate(props['counters'])"
            v-bind="prop"
            :idx="i"
          />
        </counters>

        <script>
        import collagraph as cg

        try:
            import Counter
        except:
            pass

        class Counters(cg.Component):
            pass
        </script>
        """,
        namespace=namespace,
    )
    gui = Collagraph(DictRenderer())
    container = {"type": "root"}
    state = reactive({"counters": [{"count": 0}]})

    gui.render(Counters, container, state=state)

    assert "children" in container["children"][0], format_dict(container)
    assert len(container["children"][0]["children"]) == 1, format_dict(container)


def test_for_expression(parse_source):
    # FIXME: renaming labl to label makes the compiler think it is a component tag
    # Should at least warn, better yet: prevent this from being a problem...
    Labels, _ = parse_source(
        """
        <widget>
          <label
            v-for="idx, (labl, suffix) in enumerate(zip(labels, suffixes))"
            :key="idx"
            :text="labl"
            :suffix="suffix"
          />
        </widget>

        <script lang="python">
        import collagraph as cg

        class Labels(cg.Component):
            pass
        </script>
        """
    )
    state = reactive({"labels": [], "suffixes": []})
    gui = Collagraph(DictRenderer(), event_loop_type=EventLoopType.SYNC)
    container = {"type": "root"}
    gui.render(Labels, container, state=state)

    widget = container["children"][0]
    assert widget["type"] == "widget"

    assert "children" not in widget

    for labels, suffixes in (
        (["Foo"], ["x"]),
        (["Foo", "Bar"], ["x", "y"]),
        ([], []),
        (["a", "b", "c", "d"], ["1", "2", "3", "4"]),
    ):
        state["labels"], state["suffixes"] = labels, suffixes
        if len(labels) > 0:
            assert "children" in widget and len(widget["children"]) == len(labels), (
                labels,
                suffixes,
            )
        else:
            assert "children" not in widget, (labels, suffixes)

        for idx, (label, suffix) in enumerate(zip(labels, suffixes)):
            assert widget["children"][idx]["attrs"]["text"] == label
            assert widget["children"][idx]["attrs"]["suffix"] == suffix


def test_for_event_handlers(parse_source):
    Buttons, _ = parse_source(
        """
        <button
          v-for="name, callback in buttons"
          :key="name"
          @callback="callback"
        />

        <script>
        import collagraph as cg

        class Buttons(cg.Component):
            def init(self):
                self.state["buttons"] = [
                    ["first", self.on_first],
                    ["second", self.on_second],
                ]

            def on_first(self):
                self.props["callback"]("First")

            def on_second(self):
                self.props["callback"]("Second")
        </script>
        """
    )

    calls = []
    state = {"callback": lambda value: calls.append(value)}

    gui = Collagraph(DictRenderer())
    container = {"type": "root"}
    gui.render(Buttons, container, state)

    first_button, second_button = container["children"]
    assert first_button["attrs"]["key"] == "first"
    assert second_button["attrs"]["key"] == "second"

    for handler in first_button["handlers"]["callback"]:
        handler()

    assert calls == ["First"]

    for handler in second_button["handlers"]["callback"]:
        handler()

    assert calls == ["First", "Second"]


def test_for_lambdas(parse_source):
    Buttons, _ = parse_source(
        """
        <button
          v-for="name in buttons"
          :key="name"
          @callback="lambda: on_button(name)"
        />

        <script>
        import collagraph as cg

        class Buttons(cg.Component):
            def init(self):
                self.state["buttons"] = ["first", "second"]

            def on_button(self, value):
                self.props["callback"](value)
        </script>
        """
    )

    calls = []
    state = {"callback": lambda value: calls.append(value)}

    gui = Collagraph(DictRenderer())
    container = {"type": "root"}
    gui.render(Buttons, container, state)

    first_button, second_button = container["children"]
    assert first_button["attrs"]["key"] == "first"
    assert second_button["attrs"]["key"] == "second"

    for handler in first_button["handlers"]["callback"]:
        handler()

    assert calls == ["first"]

    for handler in second_button["handlers"]["callback"]:
        handler()

    assert calls == ["first", "second"]


def test_for_context_and_naming(parse_source):
    """
    Make sure that using a loop variable can have the same
    name as an element.
    """
    Items, _ = parse_source(
        """
        <item
          v-for="item in items"
          :value="item['value']"
        />
        <script>
        import collagraph as cg
        class Items(cg.Component):
            pass
        </script>
        """
    )
    state = reactive({"items": [{"value": "a"}, {"value": "b"}]})

    gui = Collagraph(DictRenderer())
    container = {"type": "root"}
    gui.render(Items, container, state)

    first_item, second_item = container["children"]
    assert first_item["attrs"]["value"] == "a"
    assert second_item["attrs"]["value"] == "b"
