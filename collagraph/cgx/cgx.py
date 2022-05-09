import ast
from html.parser import HTMLParser
import re
import textwrap


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


def call(node, names=None):
    """
    Call cg.create_element() with the right args for the given node.
    Recursive.
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
    Converts the node to args that can be passed to create_element
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
            key_parts = key.split(":")
            if len(key_parts) != 2:
                raise ValueError(f"Invalid bind directive: {key}")
            key = key_parts[1]
            props_keys.append(ast.Constant(value=key))
            props_values.append(
                RewriteName(skip=names).visit(ast.parse(val, mode="eval")).body
            )
            continue

        # breakpoint()
        if key.startswith((DIRECTIVE_ON, "@")):
            split_char = "@" if key.startswith("@") else ":"
            key = key.split(split_char)[1]
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

            for_tree.elt = call(child, local_names)

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
            children_args.append(call(child))

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
    (if_directive, if_node), *if_else_statements = control_flow
    else_statement = (
        if_else_statements.pop()
        if if_else_statements and if_else_statements[-1][0] == "v-else"
        else None
    )

    rewrite_if_expr = RewriteIfExpr(skip=names)

    current_statement = ast.IfExp(
        test=if_node.attrs[if_directive],
        body=call(if_node),
        orelse=ast.Constant(value=None),
    )
    rewrite_if_expr.visit(current_statement)
    root_statement = current_statement

    for directive, node in if_else_statements:
        if_else_tree = ast.IfExp(
            test=node.attrs[directive],
            body=call(node),
            orelse=ast.Constant(value=None),
        )
        current_statement.orelse = if_else_tree
        current_statement = if_else_tree
        rewrite_if_expr.visit(current_statement)

    if else_statement:
        current_statement.orelse = call(else_statement[1])

    return root_statement


def create_ast_tree(node):
    render = ast.FunctionDef(
        name="render",
        args=ast.arguments(
            posonlyargs=[],
            args=[ast.arg("self")],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[],
        ),
        body=[ast.Return(value=call(node))],
        decorator_list=[],
    )
    # Create module with the render function
    return ast.Module(body=[render], type_ignores=[])


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

    script_tree = ast.parse(script, filename=str(path), mode="exec")

    # Inject 'import collagraph' into imports
    script_tree.body.insert(
        0,
        ast.ImportFrom(
            module="collagraph",
            names=[
                ast.alias(
                    name="create_element",
                    asname="_create_element",
                )
            ],
        ),
    )

    script_tree.body.insert(
        1,
        ast.parse(
            # TODO: add self.state and self.props as searchable namespaces
            # TODO: caching of lookup source
            textwrap.dedent(
                """
                def _lookup(self, name, cache={}):
                    # Note that the default value of cache is using the fact
                    # that defaults are created at function definition, so
                    # the cache is actually a 'global' object that is shared
                    # between method calls and thus is suited to serve as
                    # a cache for storing the method used for looking up the
                    # value
                    if method := cache.get(name):
                        return method(self, name)

                    def self_lookup(self, name):
                        return getattr(self, name)

                    def global_lookup(self, name):
                        return globals()[name]

                    if hasattr(self, name):
                        cache[name] = self_lookup
                        return _lookup(self, name)
                    if name in globals():
                        cache[name] = global_lookup
                        return _lookup(self, name)
                    raise NameError(f"name '{name}' is not defined")
                """
            ),
            mode="exec",
        ).body[0],
    )

    # Find ClassDef
    component_def = None
    for node in script_tree.body:
        if isinstance(node, ast.ClassDef):
            component_def = node
            break

    # Inject render function into ClassDef
    render_tree = create_ast_tree(parser.root.child_with_tag("template").children[0])

    component_def.body.append(render_tree.body[0])

    ast.fix_missing_locations(script_tree)

    # TODO: figure out which ClassDef is subclass of Component

    code = compile(script_tree, filename="<ast>", mode="exec")
    return load_module(code, component_def.name)


def load_module(code, name):
    module_namespace = {}
    exec(code, module_namespace)
    return module_namespace[name], module_namespace


class RewriteIfExpr(ast.NodeTransformer):
    def __init__(self, skip):
        self.skip = skip

    def visit_IfExp(self, node):
        tree = ast.parse(node.test, mode="eval")
        RewriteName(skip=self.skip).visit(tree)
        node.test = tree.body
        return node


class NameCollector(ast.NodeVisitor):
    def __init__(self):
        self.names = set()

    def visit_Name(self, node):
        self.names.add(node.id)


class RewriteName(ast.NodeTransformer):
    def __init__(self, skip):
        self.skip = skip

    def visit_Name(self, node):
        if node.id in __builtins__:
            return node

        if node.id in self.skip:
            return node

        if node.id.startswith(AST_GEN_VARIABLE_PREFIX):
            return node

        return ast.Call(
            func=ast.Name(id="_lookup", ctx=ast.Load()),
            args=[
                ast.Name(id="self", ctx=ast.Load()),
                ast.Constant(value=node.id),
            ],
            keywords=[],
        )


def is_directive(key):
    return key.startswith((DIRECTIVE_PREFIX, ":", "@"))


class Node:
    """Node that represents an element from a CGX file."""

    def __init__(self, tag, attrs=None):
        self.tag = tag
        self.attrs = attrs or {}
        self.data = None
        self.children = []

    def control_flow(self):
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
