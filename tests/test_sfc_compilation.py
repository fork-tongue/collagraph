import pytest


def test_error_only_script_tag(parse_source):
    with pytest.raises(ValueError):
        parse_source("""
            <script>
            import collagraph as cg
            class Foo(cg.Component):pass
            </script>
        """)


def test_error_no_script_tag(parse_source):
    with pytest.raises(ValueError):
        parse_source("""
            <!-- widget -->
        """)


def test_error_multiple_script_tags(parse_source):
    with pytest.raises(ValueError) as e:
        parse_source("""
            <script />
            <script />
        """)
    assert "Expected exactly 1 script tag" in str(e)


def test_error_on_missing_script_content(parse_source):
    with pytest.raises(RuntimeError):
        parse_source("""
            <widget />
            <script>
            </script>
        """)


def test_error_on_invalid_script_content(parse_source):
    with pytest.raises(SyntaxError):
        parse_source("""
            <widget />
            <script>a<invalid />
            </script>
        """)


def test_error_on_missing_class(parse_source):
    with pytest.raises(RuntimeError):
        parse_source("""
            <widget />
            <script>
            import collagraph
            </script>
        """)


def test_error_on_unknown_directive(parse_source):
    with pytest.raises(NotImplementedError) as e:
        parse_source("""
            <widget v-foo />
            <script>
            import collagraph as cg
            class Foo(cg.Component): pass
            </script>
        """)
    assert "v-foo" in str(e)
