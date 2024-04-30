from collagraph import DictRenderer, EventLoopType, Collagraph


def test_load_string(parse_source):
    Item, namespace = parse_source(
        """
        <item :value="value" />

        <script>
        import collagraph

        class Item(collagraph.Component):
            pass
        </script>
        """
    )

    App, _ = parse_source(
        """
        <app>
          <Item value="foo" />
        </app>

        <script>
        import collagraph
        try:
            # Import Item will fail, but is needed
            # in order to 'register' it as a component
            import Item
        except:
            pass

        class App(collagraph.Component):
            pass
        </script>
        """,
        namespace=namespace,
    )

    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    container = {"type": "root"}
    gui.render(App, container)

    app = container["children"][0]
    assert app["type"] == "app"
    item = app["children"][0]
    assert item["attrs"]["value"] == "foo"
    assert item["type"] == "item"
