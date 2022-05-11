import ast
from html.parser import HTMLParser
import re
import textwrap

from collagraph import Component


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
AST_GEN_VARIABLE_PREFIX = "_ast_"

COMPONENT_CLASS_DEFINITION = re.compile(r"class\s*(.*?)\s*\(.*?\)\s*:")
AST_LOOKUP_FUNCTION = ast.parse(
    textwrap.dedent(
        """
        def _lookup(self, name, cache={}):
            # Note that the default value of cache is using the fact
            # that defaults are created at function definition, so
            # the cache is actually a 'global' object that is shared
            # between method calls and thus is suited to serve as
            # a cache for storing the method used for looking up the
            # value.
            if method := cache.get(name):
                return method(self, name)

            def props_lookup(self, name):
                return self.props[name]

            def state_lookup(self, name):
                return self.state[name]

            def self_lookup(self, name):
                return getattr(self, name)

            def global_lookup(self, name):
                return globals()[name]

            if name in self.props:
                cache[name] = props_lookup
            elif name in self.state:
                cache[name] = state_lookup
            elif hasattr(self, name):
                cache[name] = self_lookup
            elif name in globals():
                cache[name] = global_lookup
            else:
                raise NameError(f"name '{name}' is not defined")
            return _lookup(self, name)
        """
    ),
    mode="exec",
)


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

    # Create an AST from the script
    script_tree = ast.parse(script, filename=str(path), mode="exec")

    # Inject 'create_element' into imports so that the (generated) render
    # method can call this function
    script_tree.body.insert(
        0,
        ast.ImportFrom(
            module="collagraph",
            names=[ast.alias(name="create_element", asname="_create_element")],
        ),
    )

    # Inject a method into the script for looking up variables that are mentioned
    # in the template. This provides some syntactic sugar so that people can leave
    # out `self`.
    script_tree.body.insert(1, AST_LOOKUP_FUNCTION.body[0])

    # Find the last ClassDef and assume that it is the
    # component that is defined in the SFC
    component_def = None
    for node in reversed(script_tree.body):
        if isinstance(node, ast.ClassDef):
            component_def = node
            break

    # Create render function as AST and inject into the ClassDef
    render_tree = create_ast_render_function(
        parser.root.child_with_tag("template").children[0]
    )
    component_def.body.append(render_tree)

    # Because we modified the AST significantly we need to call an AST
    # method to fix any `lineno` and `col_offset` attributes of the nodes
    ast.fix_missing_locations(script_tree)

    # Compile the tree into a code object (module)
    code = compile(script_tree, filename="<ast>", mode="exec")
    # Execute the code as module and pass a dictionary that will capture
    # the global and local scope of the module
    module_namespace = {}
    exec(code, module_namespace)

    # Check that the class definition is an actual subclass of Component
    component_class = module_namespace[component_def.name]
    if not issubclass(component_class, Component):
        raise ValueError(
            f"The last class defined in {path} is not a subclass of "
            f"Component: {component_class}"
        )
    return component_class, module_namespace


def create_ast_render_function(node):
    """
    Create render function as AST.
    """
    return ast.FunctionDef(
        name="render",
        args=ast.arguments(
            posonlyargs=[],
            args=[ast.arg("self")],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[],
        ),
        body=[ast.Return(value=call_create_element(node))],
        decorator_list=[],
    )


def call_create_element(node, names=None):
    """
    Returns an ast.Call of `collagraph.create_element()` with the right args
    for the given node.

    Names is a set of variable names that should not be wrapped in
    the _lookup method.
    """
    if names is None:
        names = set()
    return ast.Call(
        func=ast.Name(id="_create_element", ctx=ast.Load()),
        args=convert_node_to_args(node, names),
        keywords=[],
    )


def convert_node_to_args(node, names=None):
    """
    Converts the node to args that can be passed to `collagraph.create_element()`.
    """
    # Construct the first argument: type of node
    type_arg = ast.Constant(value=node.tag)

    # Construct the second argument: the props (dict) for the node
    props_keys = []
    props_values = []

    for key, val in node.attrs.items():
        # All non-directive attributes can be constructed easily
        if not is_directive(key):
            props_keys.append(ast.Constant(value=key))
            props_values.append(ast.Constant(value=val))
            continue

        if key.startswith((DIRECTIVE_BIND, ":")):
            _, key = key.split(":")
            props_keys.append(ast.Constant(value=key))
            props_values.append(
                RewriteName(skip=names).visit(ast.parse(val, mode="eval")).body
            )
            continue

        # breakpoint()
        if key.startswith((DIRECTIVE_ON, "@")):
            split_char = "@" if key.startswith("@") else ":"
            _, key = key.split(split_char)
            key = f"on_{key}"
            props_keys.append(ast.Constant(value=key))
            props_values.append(
                RewriteName(skip=names).visit(ast.parse(val, mode="eval")).body
            )
            continue

        if key.startswith((DIRECTIVE_FOR)):
            # Skip right away, parent should've already handled this
            continue

    # Construct the other arguments: the children of the node
    children_args = []

    control_flow = []
    for child in node.children:
        directive = None

        # Handle for-directives
        if for_expression := child.attrs.get(DIRECTIVE_FOR):
            for_expression = f"[None for {for_expression}]"
            for_tree = ast.parse(for_expression, mode="eval").body

            # Find the names that are defined as part of the comprehension(s)
            # E.g: 'i, (a, b) in enumerate(some_collection)' defines the names
            # i, a and b, so we don't want to wrap those names with `_lookup()`
            name_collector = NameCollector()
            for generator in for_tree.generators:
                name_collector.generic_visit(generator.target)

            local_names = names.union(name_collector.names)
            RewriteName(skip=local_names).visit(for_tree)

            for_tree.elt = call_create_element(child, local_names)

            result = ast.Starred(value=for_tree, ctx=ast.Load())
            children_args.append(result)
            continue

        # Handle control flow directives
        if directive := child.control_flow():
            control_flow.append((directive, child))

        if not directive:
            if control_flow:
                children_args.append(create_control_flow_ast(control_flow, names))
                control_flow = []
            children_args.append(call_create_element(child))

    if control_flow:
        children_args.append(create_control_flow_ast(control_flow, names))
        control_flow = []

    # Create a starred list comprehension that when called, will generate
    # all child elements
    starred_expr = ast.Starred(
        value=ast.ListComp(
            elt=ast.Name(
                id=f"{AST_GEN_VARIABLE_PREFIX}child",
                ctx=ast.Load(),
            ),
            generators=[
                ast.comprehension(
                    target=ast.Name(
                        id=f"{AST_GEN_VARIABLE_PREFIX}child",
                        ctx=ast.Store(),
                    ),
                    iter=ast.List(
                        elts=children_args,
                        ctx=ast.Load(),
                    ),
                    ifs=[
                        ast.Compare(
                            left=ast.Name(
                                id=f"{AST_GEN_VARIABLE_PREFIX}child",
                                ctx=ast.Load(),
                            ),
                            ops=[ast.IsNot()],
                            comparators=[ast.Constant(value=None)],
                        )
                    ],
                    is_async=0,
                )
            ],
        ),
        ctx=ast.Load(),
    )
    # Return all the arguments
    return [type_arg, ast.Dict(keys=props_keys, values=props_values), starred_expr]


def create_control_flow_ast(control_flow, names):
    """
    Create an AST of control flow nodes (if/else-if/else)
    """
    (if_directive, if_node), *if_else_statements = control_flow
    else_statement = (
        if_else_statements.pop()
        if if_else_statements and if_else_statements[-1][0] == "v-else"
        else None
    )

    rewrite_name = RewriteName(skip=names)

    current_statement = ast.IfExp(
        test=ast.parse(if_node.attrs[if_directive], mode="eval").body,
        body=call_create_element(if_node),
        orelse=ast.Constant(value=None),
    )
    rewrite_name.visit(current_statement.test)
    root_statement = current_statement

    for directive, node in if_else_statements:
        if_else_tree = ast.IfExp(
            test=ast.parse(node.attrs[directive], mode="eval").body,
            body=call_create_element(node),
            orelse=ast.Constant(value=None),
        )
        rewrite_name.visit(if_else_tree.test)
        current_statement.orelse = if_else_tree
        current_statement = if_else_tree

    if else_statement:
        current_statement.orelse = call_create_element(else_statement[1])

    return root_statement


def is_directive(key):
    return key.startswith((DIRECTIVE_PREFIX, ":", "@"))


class NameCollector(ast.NodeVisitor):
    """AST node visitor that will create a set of the ids of every Name node
    it encounters."""

    def __init__(self):
        self.names = set()

    def visit_Name(self, node):
        self.names.add(node.id)


class RewriteName(ast.NodeTransformer):
    """AST node transformer that will try to replace static Name nodes with
    a call to `_lookup` with the name of the node."""

    def __init__(self, skip):
        self.skip = skip

    def visit_Name(self, node):
        # Don't try and replace any item from the __builtins__
        if node.id in __builtins__:
            return node

        # Don't replace any name that should be explicitely skipped
        if node.id in self.skip:
            return node

        return ast.Call(
            func=ast.Name(id="_lookup", ctx=ast.Load()),
            args=[
                ast.Name(id="self", ctx=ast.Load()),
                ast.Constant(value=node.id),
            ],
            keywords=[],
        )


class Node:
    """Node that represents an element from a CGX file."""

    def __init__(self, tag, attrs=None):
        self.tag = tag
        self.attrs = attrs or {}
        self.data = None
        self.children = []

    def control_flow(self):
        """Returns the control flow string (if/else-if/else), if present in the
        attrs of the node."""
        for attr in self.attrs:
            if attr in CONTROL_FLOW_DIRECTIVES:
                return attr

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
