from html.parser import HTMLParser

from collagraph import create_element
from collagraph.components import Component, set_render_function


SUFFIX = "cgx"


def load(path):
    """
    Loads and returns a component from a CGX file.

    A subclass of Component will be created from the CGX file
    where the contents of the <template> tag will be used as
    the `render` function, while the contents of the <script>
    tag will be used to provide the rest of the functions of
    the component.

    The <style> tag is currently unsupported.
    """
    parser = CGXParser()
    parser.feed(path.read_text())

    # TODO: proper validation of parsed structure

    # Read the data from code block
    code = parser.root.children[1].data
    # Construct a render function
    render = node_to_render_function(parser.root.children[0].children[0])
    local_attrs = {}
    # Exec the code with a custom locals dict to capture
    # all the defined class methods
    # TODO: look into 'compile' to create code objects from text
    set_render_function(render)
    exec(code, globals(), local_attrs)
    set_render_function(None)

    wrapped_type = None
    for value in local_attrs.values():
        try:
            if issubclass(value, Component) and value is not Component:
                wrapped_type = value
                break
        except TypeError:
            pass

    return wrapped_type


def convert_node(node, context=None):
    return create_element(
        node.tag, node.attrs, *[convert_node(node) for node in node.children]
    )


def node_to_render_function(node):
    def render(self):
        return convert_node(node)

    return render


class Node:
    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = attrs
        self.data = None
        self.children = []


class CGXParser(HTMLParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = Node("root", {})
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
