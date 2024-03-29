import textwrap

from collagraph.cgx import cgx


def test_comment_at_root_level():
    # This next call should not fail based
    # on the existence of comments anywhere
    # between the elements
    cgx.construct_ast(
        "template",
        textwrap.dedent(
            """
            <!-- comment -->
            <template>
              <!-- comment -->
              <item />
              <!-- comment -->
            </template>
            <!-- comment -->
            <script>
            import collagraph as cg
            class Comp(cg.Component):
                pass
            </script>
            <!-- comment -->
            """
        ),
    )
