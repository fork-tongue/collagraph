from textwrap import dedent

import pytest

from collagraph import Collagraph, EventLoopType
from collagraph.renderers import DictRenderer
from collagraph.sfc.parser import CGXParser


def test_parser_unclosed_element(parse_source):
    App, _ = parse_source(
        """
        <app>
          <unclosed>
        </app>

        <script>
        import collagraph as cg

        class App(cg.Component):
            pass
        </script>
        """
    )

    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    container = {"type": "root"}
    gui.render(App, container)

    assert container["children"][0] == {
        "type": "app",
        "children": [
            {"type": "unclosed"},
        ],
    }


def test_parser_unclosed_root_element(parse_source):
    with pytest.raises(ValueError):
        _ = parse_source(
            """
            <app>

            <script>
            import collagraph as cg

            class App(cg.Component):
                pass
            </script>
            """
        )


def test_parser_element_start_end(parse_source):
    parser = CGXParser()
    parser.feed(
        dedent("""\
            <long-item
              @with-many="toet"
              :attrs="blaat"
              :that-take="foo"
              a-lot-of="space"
            />

            <other />
        """)
    )

    assert parser.root
    long_item = parser.root.children[0]
    assert long_item.location == (1, 0)
    assert long_item.end == (6, 0)

    short_item = parser.root.children[1]
    assert short_item.location == (8, 0)
    assert short_item.end == (8, 7)
