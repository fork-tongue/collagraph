from observ import reactive

from collagraph import Collagraph, EventLoopType
from collagraph.renderers import DictRenderer


def test_ref_basic(parse_source):
    """Test basic ref functionality - accessing element via refs dict"""
    App, _ = parse_source(
        """
        <app>
          <button ref="myButton" text="Click me" />
        </app>

        <script>
        import collagraph as cg

        class App(cg.Component):
            instance = None

            def init(self):
                self.button_element = None

            def mounted(self):
                App.instance = self
                # Store the button element for testing
                self.button_element = self.refs['myButton']
        </script>
        """
    )

    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container)
    component = App.instance

    # Check that the ref was registered
    assert "myButton" in component.refs
    # Check that it points to the actual button element
    button = container["children"][0]["children"][0]
    assert button["type"] == "button"
    assert button["attrs"]["text"] == "Click me"
    assert component.refs["myButton"] == button
    assert component.button_element == button


def test_ref_multiple_elements(parse_source):
    """Test multiple refs on different elements"""
    App, _ = parse_source(
        """
        <app>
          <button ref="btn1" text="Button 1" />
          <input ref="input1" value="test" />
          <label ref="label1" text="Label" />
        </app>

        <script>
        import collagraph as cg

        class App(cg.Component):
            instance = None

            def mounted(self):
                App.instance = self
        </script>
        """
    )

    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container)
    component = App.instance

    # Check all refs are registered
    assert "btn1" in component.refs
    assert "input1" in component.refs
    assert "label1" in component.refs

    # Check they point to correct elements
    app = container["children"][0]
    button = app["children"][0]
    input_el = app["children"][1]
    label = app["children"][2]

    assert component.refs["btn1"] == button
    assert component.refs["input1"] == input_el
    assert component.refs["label1"] == label


def test_ref_component(parse_source):
    """Test ref on a child component - should store component instance"""
    Child, namespace = parse_source(
        """
        <child text="child content" />

        <script>
        import collagraph as cg

        class Child(cg.Component):
            def get_text(self):
                return self.props['text']
        </script>
        """
    )

    Parent, namespace = parse_source(
        """
        <parent>
          <Child ref="childComponent" text="Hello" />
        </parent>

        <script>
        import collagraph as cg
        try:
            import Child
        except ImportError:
            pass

        class Parent(cg.Component):
            instance = None

            def mounted(self):
                Parent.instance = self
        </script>
        """,
        namespace=namespace,
    )

    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(Parent, container)
    component = Parent.instance

    # Check that ref points to component instance, not element
    assert "childComponent" in component.refs
    child_instance = component.refs["childComponent"]
    assert isinstance(child_instance, Child)
    assert child_instance.get_text() == "Hello"


def test_ref_with_conditional_rendering(parse_source):
    """Test that refs are added/removed when elements appear/disappear with v-if"""
    App, _ = parse_source(
        """
        <app>
          <button v-if="show" ref="conditionalButton" text="Show me" />
        </app>

        <script>
        import collagraph as cg

        class App(cg.Component):
            instance = None

            def mounted(self):
                App.instance = self
        </script>
        """
    )

    state = reactive({"show": False})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)
    component = App.instance

    # Initially, button is not shown, so ref should not exist
    assert "conditionalButton" not in component.refs

    # Show the button
    state["show"] = True

    # Now ref should exist
    assert "conditionalButton" in component.refs
    app = container["children"][0]
    button = app["children"][0]
    assert component.refs["conditionalButton"] == button

    # Hide the button again
    state["show"] = False

    # Ref should be removed
    assert "conditionalButton" not in component.refs


def test_ref_with_dynamic_attributes(parse_source):
    """Test that refs work with elements that have dynamic attributes"""
    App, _ = parse_source(
        """
        <app>
          <button ref="dynamicButton" :text="buttonText" />
        </app>

        <script>
        import collagraph as cg

        class App(cg.Component):
            instance = None

            def mounted(self):
                App.instance = self
        </script>
        """
    )

    state = reactive({"buttonText": "Initial"})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)
    component = App.instance

    # Ref should be registered
    assert "dynamicButton" in component.refs
    button = component.refs["dynamicButton"]
    assert button["attrs"]["text"] == "Initial"

    # Change dynamic attribute
    state["buttonText"] = "Updated"

    # Ref should still point to the same element
    assert component.refs["dynamicButton"] == button
    assert button["attrs"]["text"] == "Updated"


def test_ref_lookup_in_template(parse_source):
    """Test that refs can be accessed in template expressions via _lookup"""
    App, _ = parse_source(
        """
        <app>
          <input v-if="input_enabled" ref="myInput" value="test" />
          <button :disabled="not myInput" text="Submit" />
        </app>

        <script>
        import collagraph as cg

        class App(cg.Component):
            instance = None

            def init(self):
                App.instance = self
        </script>
        """
    )

    state = reactive({"input_enabled": True})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)
    component = App.instance

    # Ref should be registered
    assert "myInput" in component.refs
    assert len(container["children"][0]["children"]) == 2, container["children"][0][
        "children"
    ]

    # Check that refs were registered
    assert "myInput" in component.refs
    # Check that the disabled state is what we expect it to be
    assert container["children"][0]["children"][1]["attrs"]["disabled"] is False


def test_ref_reactive_in_template(parse_source):
    """Test that refs can be accessed in template expressions via _lookup"""
    App, _ = parse_source(
        """
        <app>
          <input v-if="input_enabled" ref="myInput" value="test" />
          <button :disabled="not refs.get('myInput')" text="Submit" />
        </app>

        <script>
        import collagraph as cg

        class App(cg.Component):
            instance = None

            def init(self):
                App.instance = self
        </script>
        """
    )

    state = reactive({"input_enabled": False})
    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container, state=state)
    component = App.instance

    # Ref should not be registered yet because input_enabled is False
    assert "myInput" not in component.refs
    assert len(container["children"][0]["children"]) == 1, container["children"][0][
        "children"
    ]
    assert container["children"][0]["children"][0]["attrs"]["disabled"] is True

    state["input_enabled"] = True

    # Check that myInput ref is now registered
    assert "myInput" in component.refs
    # Check that the disabled state is what we expect it to be
    assert container["children"][0]["children"][1]["attrs"]["disabled"] is False

    # Switch it back one more time
    state["input_enabled"] = False

    assert "myInput" not in component.refs
    assert len(container["children"][0]["children"]) == 1, container["children"][0][
        "children"
    ]
    assert container["children"][0]["children"][0]["attrs"]["disabled"] is True


def test_ref_nested_components(parse_source):
    """Test refs in nested component hierarchy"""
    GrandChild, namespace = parse_source(  # noqa: RUF059
        """
        <grandchild>
          <label ref="label" text="I am grandchild" />
        </grandchild>

        <script>
        import collagraph as cg

        class GrandChild(cg.Component):
            instance = None

            def mounted(self):
                GrandChild.instance = self
        </script>
        """
    )

    Child, namespace = parse_source(  # noqa: RUF059
        """
        <child>
          <button ref="button" text="I am child" />
          <GrandChild ref="grandchild" />
        </child>

        <script>
        import collagraph as cg
        try:
            import GrandChild
        except ImportError:
            pass

        class Child(cg.Component):
            instance = None

            def mounted(self):
                Child.instance = self
        </script>
        """,
        namespace=namespace,
    )

    Parent, namespace = parse_source(
        """
        <parent>
          <input ref="input" value="I am parent" />
          <Child ref="child" />
        </parent>

        <script>
        import collagraph as cg
        try:
            import Child
        except ImportError:
            pass

        class Parent(cg.Component):
            instance = None

            def mounted(self):
                Parent.instance = self
        </script>
        """,
        namespace=namespace,
    )

    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(Parent, container)
    parent_component = Parent.instance

    # Parent should have refs to its direct children only
    assert "input" in parent_component.refs
    assert "child" in parent_component.refs
    assert "button" not in parent_component.refs
    assert "grandchild" not in parent_component.refs
    assert "label" not in parent_component.refs

    # Child component should have its own refs
    child_component = parent_component.refs["child"]
    assert "button" in child_component.refs
    assert "grandchild" in child_component.refs
    assert "input" not in child_component.refs

    # GrandChild component should have its own refs
    grandchild_component = child_component.refs["grandchild"]
    assert "label" in grandchild_component.refs
    assert "button" not in grandchild_component.refs


def test_ref_property_protected(parse_source):
    """Test that the refs property cannot be overwritten"""
    App, _ = parse_source(
        """
        <app />

        <script>
        import collagraph as cg

        class App(cg.Component):
            instance = None

            def init(self):
                App.instance = self
                try:
                    self.refs = {}
                except RuntimeError:
                    self.caught_error = True
        </script>
        """
    )

    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container)
    component = App.instance

    assert component.caught_error is True


def test_ref_empty_name(parse_source):
    """Test ref with empty string as name"""
    App, _ = parse_source(
        """
        <app>
          <button ref="" text="Button" />
        </app>

        <script>
        import collagraph as cg

        class App(cg.Component):
            instance = None

            def mounted(self):
                App.instance = self
        </script>
        """
    )

    container = {"type": "root"}
    gui = Collagraph(
        renderer=DictRenderer(),
        event_loop_type=EventLoopType.SYNC,
    )
    gui.render(App, container)
    component = App.instance

    assert "" not in component.refs and len(component.refs) == 0
