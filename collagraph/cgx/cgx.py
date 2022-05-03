import ast
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
    # Parse the file component into a tree of Node instances
    parser = CGXParser()
    parser.feed(path.read_text())

    # Read the data from script block
    script = parser.root.child_with_tag("script").data
    # Compile for the first time to get a handle on the
    # context that is defined in the components' script
    preliminary_component_type, context = load_code(script)

    # Construct a render function from the template block
    template_root_node = parser.root.child_with_tag("template").children[0]
    compiled_tree = template_root_node.compile(preliminary_component_type, context)

    def render(self):
        return compiled_tree.to_vnode(self, context)

    return load_code(script, render_function=render)


def load_code(script, render_function=None):
    """
    Exec the script with a custom (globals) dict to capture
    all the defined classes and methods.
    """
    context = {}
    attrs = {}
    ComponentMeta.RENDER_FUNCTION = render_function
    try:
        exec(script, attrs)
    finally:
        ComponentMeta.RENDER_FUNCTION = None

    component_type = None
    for key, value in attrs.items():
        if key in ["__builtins__"]:
            continue

        try:
            if issubclass(value, Component) and value is not Component:
                component_type = value
                continue
        except TypeError:
            pass

        context[key] = value
    return component_type, context


# https://docs.python.org/3/library/ast.html#ast.NodeTransformer
class RewriteName(ast.NodeTransformer):
    def __init__(self, component, context):
        self.component = component
        self.context = context

    def visit_Name(self, node):
        if node.id in dir(self.component):
            return ast.Attribute(
                value=ast.Name(id="component", ctx=ast.Load()),
                attr=node.id,
                ctx=node.ctx,
            )
        return node


def compile_expression(template_expression, component, context):
    # First, parse the expression from the template to create an AST
    tree = ast.parse(template_expression)
    # Use an ast.Expression object to convert
    # the compiled statement into an actual expreesion
    expr = ast.Expression(body=tree.body[0].value)

    # Run some automated location fixer
    ast.fix_missing_locations(
        RewriteName(component=component, context=context).visit(expr)
    )

    # Compile the expression tree into a code object
    # with the `eval` mode such that we can pass the
    # code object to the `eval` function and get some
    # results back.
    code = compile(expr, filename="<ast>", mode="eval")
    return code


class PreCompiledNode:
    """
    Pre-Compiled Node that has pre-compiled all its expressions.
    """

    def __init__(self):
        # Type of the VNode. Can be a function (component) as well!
        # Example for tag as function can be the result from a v-if
        # or v-for directive
        self.tag = None
        # Plain attributes that don't have any directives / expressions
        self.attrs = {}
        # Non-standard attributes as expressions from directives
        self.expressions = {}
        # List of children for this node
        self.children = []

    def control_flow(self):
        for attr in self.expressions:
            if attr in ["v-if", "v-else-if", "v-else"]:
                return attr

    def to_vnode(self, component, context):
        # First copy the static attributes
        attrs = self.attrs.copy()

        # Then compute all the expressions and add the results
        for key, code in self.expressions.items():
            # The parent has already processed these directives for
            # its children, and they don't need to end up in the
            # actual attributes, so we can skip them here
            if key in ["v-if", "v-else-if", "v-else"]:
                continue
            try:
                result = eval(code, {}, {"component": component, **context})
                attrs[key] = result
            except NameError:
                raise

        # Check all the children for v-if/else-if/else directives
        children = []
        control_flow = []
        for child in self.children:
            directive = None

            if directive := child.control_flow():
                control_flow.append((directive, child))

            if not directive:
                if control_flow:
                    if control_flow_result := evaluate_control_flow(
                        control_flow, component, context
                    ):
                        children.append(control_flow_result)
                    control_flow = []
                children.append(child)

        if control_flow:
            if control_flow_result := evaluate_control_flow(
                control_flow, component, context
            ):
                children.append(control_flow_result)
            control_flow = []

        return create_element(
            self.tag,
            attrs,
            *[child.to_vnode(component, context) for child in children],
        )


def evaluate_control_flow(nodes, component, context):
    for directive, node in nodes:
        if code := node.expressions[directive]:
            result = eval(code, {}, {"component": component, **context})
            if result:
                return node

        if directive == "v-else":
            return node

    return None


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

    def compile(self, component, context):
        node = PreCompiledNode()
        node.attrs = {
            key: val
            for key, val in self.attrs.items()
            if "v-" not in key and ":" not in key
        }

        for key, val in self.attrs.items():
            if "v-" not in key and ":" not in key:
                continue

            if key.startswith("v-bind:") or key.startswith(":"):
                attr = key.split(":")[1]
                node.expressions[attr] = compile_expression(val, component, context)
            elif key == "v-else":
                node.expressions[key] = None
            else:
                node.expressions[key] = compile_expression(val, component, context)

        node.tag = self.tag

        node.children = [child.compile(component, context) for child in self.children]
        return node


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
