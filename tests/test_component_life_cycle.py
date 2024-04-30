from observ import reactive

import collagraph
from collagraph.renderers.dict_renderer import format_dict


def test_component_basic_lifecycle(parse_source):
    Counter, namespace = parse_source(
        """
        <counter
          :count="count"
          @bump="bump"
        />

        <script>
        import collagraph

        class Counter(collagraph.Component):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.state["count"] = self.props.get("count", 0)

            def bump(self):
                self.state["count"] += self.props.get("step_size", 1)
        </script>
        """
    )

    SpecialCounter, namespace = parse_source(
        """
        <counter
          v-bind="props"
          :count="count"
          @bump="bump"
        >
          <SpecialCounter
            v-for="props in props.get('subs', [])"
            v-bind="props"
          />
        </counter>

        <script>
        import collagraph

        try:
            import Counter
        except:
            pass

        class SpecialCounter(Counter):
            lifecycle = []

            def mounted(self):
                super().mounted()
                SpecialCounter.lifecycle.append(f"{self.props['name']}:mounted")

            def updated(self):
                super().updated()
                SpecialCounter.lifecycle.append(f"{self.props['name']}:updated")

            def before_unmount(self):
                super().before_unmount()
                SpecialCounter.lifecycle.append(f"{self.props['name']}:before_unmount")
        </script>
        """,
        namespace=namespace,
    )

    Counters, namespace = parse_source(
        """
        <counters>
          <SpecialCounter
            v-for="i, prop in enumerate(props['counters'])"
            v-bind="prop"
            :idx="i"
          />
        </counters>

        <script>
        import collagraph

        try:
            import SpecialCounter
        except:
            pass

        class Counters(collagraph.Component):
            pass
        </script>
        """,
        namespace=namespace,
    )

    gui = collagraph.Collagraph(
        collagraph.DictRenderer(),
        event_loop_type=collagraph.EventLoopType.SYNC,
    )
    container = {"type": "root"}
    state = reactive(
        {
            "counters": [
                {
                    "name": "parent",
                    "subs": [
                        {"name": "child"},
                    ],
                },
            ]
        }
    )

    assert SpecialCounter.lifecycle == []

    gui.render(Counters, container, state=state)

    assert "children" in container["children"][0], format_dict(container)
    assert len(container["children"][0]["children"]) == 1, format_dict(container)
    parent_counter = container["children"][0]["children"][0]
    assert "children" in parent_counter, format_dict(container)
    assert len(parent_counter["children"]) == 1, format_dict(container)
    child_counter = container["children"][0]["children"][0]["children"][0]
    assert parent_counter["attrs"]["name"] == "parent"
    assert child_counter["attrs"]["name"] == "child"
    assert parent_counter["attrs"]["count"] == 0
    assert child_counter["attrs"]["count"] == 0

    assert SpecialCounter.lifecycle == [
        "child:mounted",
        "parent:mounted",
    ]

    # Reset lifecycle
    SpecialCounter.lifecycle = []

    for i in range(1, 6):
        # Update state by triggering all listeners, which should trigger a re-render
        for listener in parent_counter["handlers"]["bump"]:
            listener()

        assert parent_counter["attrs"]["count"] == i
        assert SpecialCounter.lifecycle == ["parent:updated"]
        SpecialCounter.lifecycle = []

    for i in range(1, 8):
        # Update state by triggering all listeners, which should trigger a re-render
        for listener in child_counter["handlers"]["bump"]:
            listener()

        assert child_counter["attrs"]["count"] == i
        assert SpecialCounter.lifecycle == ["child:updated"]
        SpecialCounter.lifecycle = []

    state["counters"] = []

    assert "children" not in container["children"][0]

    assert SpecialCounter.lifecycle == [
        "parent:before_unmount",
        "child:before_unmount",
    ]


# TODO: add tests with more complex component 'geometry' (more layers)
# to really put the update system to the test
