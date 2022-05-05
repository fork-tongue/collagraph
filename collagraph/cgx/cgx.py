import ast
from html.parser import HTMLParser
import re
import textwrap

from collagraph import create_element
from collagraph.components import Component, ComponentMeta


SUFFIX = "cgx"
DIRECTIVE_PREFIX = "v-"
DIRECTIVE_BIND = f"{DIRECTIVE_PREFIX}bind"
DIRECTIVE_IF = f"{DIRECTIVE_PREFIX}if"
DIRECTIVE_ELSE_IF = f"{DIRECTIVE_PREFIX}else-if"
DIRECTIVE_ELSE = f"{DIRECTIVE_PREFIX}else"
CONTROL_FLOW_DIRECTIVES = (DIRECTIVE_IF, DIRECTIVE_ELSE_IF, DIRECTIVE_ELSE)
DIRECTIVE_FOR = f"{DIRECTIVE_PREFIX}for"
DIRECTIVE_ON = f"{DIRECTIVE_PREFIX}on"
FOR_LOOP_OUTPUT = "for_loop_output"

COMPONENT_CLASS_DEFINITION = re.compile(r"class\s*(.*?)\s*\(.*Component\s*\)\s*:")


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

    # NOTE: load_code is called multiple times, to people need
    # to be aware that module-level side-effects will be executed
    # multiple times. Please put any side-effects in your compontent.mounted()
    # and don't forget to clean-up in component.before_unmount() if needed.
    return load_code(script, render_function=render)


def load_code(script, render_function=None):
    """
    Exec the script with a custom (globals) dict to capture
    all the defined classes and methods.
    """
    context = {}
    ComponentMeta.RENDER_FUNCTION = render_function
    try:
        exec(script, context)
    finally:
        ComponentMeta.RENDER_FUNCTION = None

    results = re.search(COMPONENT_CLASS_DEFINITION, script)
    if not results:
        raise ValueError(f"Could not find a component class definition in:\n{script}")

    if len(results.groups()) > 1:
        raise ValueError(f"Found multiple component class definitions in:\n{script}")

    component_class_name = results.groups()[0]
    component_type = context.pop(component_class_name)

    # The regex search should take care of this most of the times, but let's
    # make sure that the Component superclass is *our* component class.
    if not issubclass(component_type, Component):
        raise ValueError(f"Invalid component class definition: {component_type}")

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


def compile_expression(template_expression, component, context, mode=None):
    if mode is None:
        mode = "eval"

    # First, parse the expression from the template to create an AST
    tree = ast.parse(template_expression)
    if mode == "eval":
        # Use an ast.Expression object to convert
        # the compiled statement into an actual expreesion
        tree = ast.Expression(body=tree.body[0].value)

    # Run some automated location fixer while
    # rewriting the Name nodes that should get attributes
    # from the given component
    ast.fix_missing_locations(
        RewriteName(component=component, context=context).visit(tree)
    )

    # Compile the expression tree into a code object
    # with the `eval` mode such that we can pass the
    # code object to the `eval` function and get some
    # results back.
    code = compile(tree, filename="<ast>", mode=mode)
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
            if attr in CONTROL_FLOW_DIRECTIVES:
                return attr

    def to_vnode(self, component, context):
        # First copy the static attributes
        attrs = self.attrs.copy()

        # Then compute all the expressions and add the results
        for key, code in self.expressions.items():
            # The parent has already processed these directives for
            # its children, and they don't need to end up in the
            # actual attributes, so we can skip them here
            if key in CONTROL_FLOW_DIRECTIVES:
                continue

            result = eval(code, {"component": component, **context})
            if key.startswith((DIRECTIVE_ON, "@")):
                split_char = "@" if key.startswith("@") else ":"
                key = key.split(split_char)[1]
                key = f"on_{key}"

            attrs[key] = result

        # Check all the children for if/else-if/else/for directives
        children = []
        control_flow = []
        for child in self.children:
            directive = None

            if for_expression := child.expressions.get(DIRECTIVE_FOR):
                output = []
                ctx = context.copy()
                ctx["component"] = component
                ctx[FOR_LOOP_OUTPUT] = output

                exec(for_expression, ctx)

                for result in output:
                    # Create custom node for each of the results
                    # from the v-for expression
                    for_child = PreCompiledNode()
                    for_child.tag = child.tag
                    for_child.attrs = child.attrs
                    for_child.children = child.children
                    # Filter out the "v-for" directive
                    for_child.expressions = {
                        k: v for k, v in child.expressions.items() if k != DIRECTIVE_FOR
                    }

                    # Create a special context for this custom node
                    for_ctx = context.copy()
                    for_ctx.update(result)

                    children.append((for_child, for_ctx))

                continue

            if directive := child.control_flow():
                control_flow.append((directive, child))

            if not directive:
                if control_flow:
                    if control_flow_result := evaluate_control_flow(
                        control_flow, component, context
                    ):
                        children.append((control_flow_result, context))
                    control_flow = []
                children.append((child, context))

        if control_flow:
            if control_flow_result := evaluate_control_flow(
                control_flow, component, context
            ):
                children.append((control_flow_result, context))
            control_flow = []

        return create_element(
            self.tag,
            attrs,
            *[child.to_vnode(component, ctx) for child, ctx in children],
        )


def evaluate_control_flow(nodes, component, context):
    # nodes is a list of tuples that consists of a directive
    # (one of 'v-if, v-else-if' or 'v-else') paired with the
    # compiled node
    for directive, node in nodes:
        if code := node.expressions[directive]:
            result = eval(code, {"component": component, **context})
            if result:
                return node

        if directive == DIRECTIVE_ELSE:
            return node

    return None


def is_directive(key):
    return key.startswith((DIRECTIVE_PREFIX, ":", "@"))


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
        node.tag = self.tag
        node.attrs = {
            key: val for key, val in self.attrs.items() if not is_directive(key)
        }

        for key, val in self.attrs.items():
            if not is_directive(key):
                continue

            if key.startswith((DIRECTIVE_BIND, ":")):
                key_parts = key.split(":")
                if len(key_parts) != 2:
                    raise ValueError(f"Invalid bind directive: {key}")
                key = key_parts[1]
                node.expressions[key] = compile_expression(val, component, context)
            elif key == DIRECTIVE_ELSE:
                node.expressions[key] = None
            elif key == DIRECTIVE_FOR:
                # Run the v-for loop and gather the results of the for-loop
                # into the 'output' variable as a list of dicts where the
                # key is the name of the loop variable.
                # The trick here is to use the diff of the locals right before
                # the for-loop and the locals right at the start of the for-loop
                # to figure out over which variables is being looped.
                expression = textwrap.dedent(
                    f"""
                    initial_locals = locals().copy()
                    for {val}:
                        for_locals = locals().copy()
                        for_locals.pop("initial_locals")
                        for_context = {{}}
                        for key in for_locals.keys() - initial_locals:
                            for_context[key] = for_locals[key]
                        {FOR_LOOP_OUTPUT}.append(for_context)"""
                )

                # Compile the for loop
                node.expressions[key] = compile_expression(
                    expression, component, context, mode="exec"
                )
            else:
                node.expressions[key] = compile_expression(val, component, context)

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
        node = Node(tag, dict(attrs))

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
