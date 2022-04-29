from html.parser import HTMLParser

from collagraph import create_element
from collagraph.components import Component, ComponentMeta


SUFFIX = "cgx"


def load(path):
    """
    Loads and returns a component from a CGX file.

    A subclass of Component will be created from the CGX file
    where the contents of the <template> tag will be used as
    the `render` function, while the contents of the <script>
    tag will be used to provide the rest of the functions of
    the component.

    For example:

        <template>
          <item foo="bar">
            <item baz="bla"/>
          </item>
        </template

        <script>
        import collagraph as cg

        class Foo(cg.Component):
            pass
        </script>

    """
    parser = CGXParser()
    parser.feed(path.read_text())

    # TODO: proper validation of parsed structure

    # Read the data from script block
    script = parser.root.child_with_tag("script").data
    # Construct a render function from the template
    template_root_node = parser.root.child_with_tag("template").children[0]

    def render(self):
        return convert_node(template_root_node, self)

    # Exec the script with a custom locals dict to capture
    # all the defined classes and methods
    local_attrs = {}
    ComponentMeta.RENDER_FUNCTION = render
    try:
        exec(script, globals(), local_attrs)
    finally:
        ComponentMeta.RENDER_FUNCTION = None

    component_type = None
    for value in local_attrs.values():
        try:
            if issubclass(value, Component) and value is not Component:
                component_type = value
                break
        except TypeError:
            pass

    return component_type


def convert_node(node, component, prev_node=None):
    """Converts a Node into a VNode, recursively."""
    attributes, directives = convert_attributes(node.attrs, component)

    if "v-if" in directives and not directives["v-if"]:
        return "v-if"

    if "v-else" in directives and prev_node:
        return "v-else"

    children = []
    prev_node = None
    for child in node.children:
        converted_child = convert_node(child, component, prev_node=prev_node)
        if converted_child in ["v-if", "v-else"]:
            prev_node = None
        elif converted_child:
            children.append(converted_child)
            prev_node = converted_child
    return create_element(node.tag, attributes, *children)


def query_component(component, attr):
    """Returns attr from state or prop of component.

    Values from the component's state have precedence over
    values from the component's props.
    """
    if attr in component.state:
        return component.state[attr]
    return component.props[attr]


def convert_attributes(attrs, component):
    attributes = {}
    directives = {}
    for key, val in attrs.items():
        # Don't perform conversion on non-directives
        if not (key.startswith("v-") or key.startswith(":")):
            attributes[key] = val

        # Check for bind directive
        if key.startswith("v-bind:") or key.startswith(":"):
            key_parts = key.split(":")
            attributes[key_parts[1]] = query_component(component, val)

        # Check for v-if directive
        if key == "v-if":
            directives[key] = query_component(component, val)
        elif key == "v-else":
            directives[key] = True

    return attributes, directives


class Node:
    """Node that represents an element from a CGX file."""

    def __init__(self, tag, attrs=None):
        self.tag = tag
        self.attrs = attrs or {}
        self.data = None
        self.children = []

    def child_with_tag(self, tag):
        for child in self.children:
            if child.tag == tag:
                return child


class CGXParser(HTMLParser):
    """Parser for CGX files.

    Creates a tree of Nodes with all encountered attributes and data.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = Node("root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {attr[0]: attr[1] for attr in attrs})

        # Add item as child to the last on the stack
        self.stack[-1].children.append(node)
        # Make the new node the last on the stack
        self.stack.append(node)

    def handle_endtag(self, tag):
        # Pop the stack
        self.stack.pop()

    def handle_data(self, data):
        if data.strip():
            self.stack[-1].data = data.strip()
