from __future__ import annotations

import ast
import logging
import sys
import textwrap
from collections import defaultdict
from os import environ
from pathlib import Path

from .parser import CGXParser, Comment, Element, TextElement

logger = logging.getLogger(__name__)

DIRECTIVE_PREFIX = "v-"
DIRECTIVE_BIND = f"{DIRECTIVE_PREFIX}bind"
DIRECTIVE_IF = f"{DIRECTIVE_PREFIX}if"
DIRECTIVE_ELSE_IF = f"{DIRECTIVE_PREFIX}else-if"
DIRECTIVE_ELSE = f"{DIRECTIVE_PREFIX}else"
DIRECTIVE_FOR = f"{DIRECTIVE_PREFIX}for"
DIRECTIVE_ON = f"{DIRECTIVE_PREFIX}on"
DIRECTIVE_SLOT = f"{DIRECTIVE_PREFIX}slot"
CONTROL_FLOW_DIRECTIVES = (DIRECTIVE_IF, DIRECTIVE_ELSE_IF, DIRECTIVE_ELSE)

SUFFIX = "cgx"

DEBUG = bool(environ.get("CGX_DEBUG", False))
# Adjust this setting to disable some runtime checks
# Defaults to True, except when it is part of an installed application
CGX_RUNTIME_WARNINGS = not getattr(sys, "frozen", False)


def construct_ast(path, template=None):
    """
    Returns a tuple of the constructed AST tree and name of (enhanced) component class.

    Construct an AST from the .cgx file by first creating an AST from the script tag,
    and then compile the contents of the template tag and insert that into the component
    class definition as `render` function.
    """
    if not template:
        template = Path(path).read_text()

    # Parse the file component into a tree of Elements
    parser = CGXParser()
    parser.feed(template)

    check_parsed_tree(parser.root)

    # Get the AST from the script tag
    script_tree = get_script_ast(parser, path)

    # Find a list of imported names (or aliases, if any)
    # Those names don't have to be wrapped by `_lookup`
    imported_names = ImportsCollector()
    imported_names.visit(script_tree)

    class_names = set(
        node.name for node in script_tree.body if isinstance(node, ast.ClassDef)
    )

    # Find the last ClassDef and assume that it is the
    # component that is defined in the SFC
    component_def: ast.ClassDef | None = None
    for node in reversed(script_tree.body):
        if isinstance(node, ast.ClassDef):
            component_def = node
            break
    if not component_def:
        raise RuntimeError(f"Could not find class definition in script: {path}")

    # Remove the script tag from the tree and process the rest
    script_node = parser.root.child_with_tag("script")
    parser.root.children.remove(script_node)

    # Create render function as AST and inject into the ClassDef
    # render_tree = create_ast_render_function(
    render_tree = create_collagraph_render_function(
        parser.root, names=imported_names.names | class_names
    )

    # Put location of render function outside of the script tag
    # This makes sure that the render function can be excluded
    # from linting.
    # Note that it's still possible to put code after the component
    # class at the end of the script node.
    line, _ = script_node.end
    RewriteDots().visit(render_tree)
    ast.fix_missing_locations(render_tree)
    ast.increment_lineno(render_tree, n=line)
    component_def.body.append(render_tree)

    # Because we modified the AST significantly we need to call an AST
    # method to fix any `lineno` and `col_offset` attributes of the nodes
    ast.fix_missing_locations(script_tree)

    if DEBUG:  # pragma: no cover
        try:
            _print_ast_tree_as_code(script_tree, path)
        except Exception as e:
            logger.warning("Could not unparse AST", exc_info=e)
    return script_tree, component_def.name


def get_script_ast(parser: CGXParser, path: Path) -> ast.Module:
    """
    Returns the AST created from the script tag in the .cgx file.
    """
    # Read the data from script block
    script_node = parser.root.child_with_tag("script")
    if not script_node.children:
        raise RuntimeError(f"Script tag has no content: {path}:{script_node.location}")
    # HTMLParser makes sure that there is only one child for script nodes
    assert isinstance(script_node.children[0], TextElement)
    script = script_node.children[0].content
    line, _ = script_node.location

    # Create an AST from the script
    script_tree = ast.parse(script, filename=str(path), mode="exec")
    # Make sure that the lineno's match up with the lines in the .cgx file
    ast.increment_lineno(script_tree, n=line - 1)
    return script_tree


def ast_create_fragment(
    el: str,
    tag: str,
    is_component: bool,
    parent: str | None = None,
    node: Element | None = None,
) -> ast.Assign:
    """
    Return AST for creating an element with `tag` and
    assigning it to variable name: `el`
    """
    keywords = [
        ast.keyword(
            arg="tag",
            value=ast.Name(id=tag, ctx=ast.Load())
            if is_component
            else ast.Constant(value=tag),
        ),
    ]
    if parent is not None:
        keywords.append(
            ast.keyword(arg="parent", value=ast.Name(id=parent, ctx=ast.Load()))
        )
    fragment_type = "Fragment"
    if is_component:
        fragment_type = "ComponentFragment"
    if tag == "slot":
        # TODO: register this slot fragment with the parent component
        fragment_type = "SlotFragment"
        slot_name = (node and node.attrs.get("name", "default")) or "default"
        keywords.append(ast.keyword(arg="name", value=ast.Constant(value=slot_name)))

    return ast.Assign(
        targets=[ast.Name(id=el, ctx=ast.Store())],
        value=ast.Call(
            func=ast.Name(id=fragment_type, ctx=ast.Load()),
            args=[
                ast.Name(id="renderer", ctx=ast.Load()),
            ],
            keywords=keywords,
        ),
    )


def ast_set_attribute(
    el: str, key: str, value: str | int | float | tuple | None
) -> ast.Expr:
    return ast.Expr(
        value=ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=el, ctx=ast.Load()),
                attr="set_attribute",
                ctx=ast.Load(),
            ),
            args=[ast.Constant(value=key), ast.Constant(value=value)],
            keywords=[],
        )
    )


def ast_set_slot_name(el: str, name: str) -> ast.Assign:
    return ast.Assign(
        targets=[
            ast.Attribute(
                value=ast.Name(id=el, ctx=ast.Load()),
                attr="slot_name",
                ctx=ast.Store(),
            )
        ],
        value=ast.Constant(value=name),
    )


def ast_named_lambda(
    source: ast.Expression, names: set[str], list_names: list[dict[str, set[str]]]
) -> ast.Expr:
    lambda_names = LambdaNamesCollector()
    lambda_names.visit(source)
    return ast.Expr(
        value=(
            RewriteName(skip=lambda_names.names | names, list_names=list_names)
            .visit(source)
            .body
        )
    )


def ast_create_dynamic_fragment(
    el: str,
    expression: str,
    parent: str | None,
    names: set[str],
    list_names: list[dict[str, set[str]]],
) -> ast.Assign:
    """
    Create a DynamicFragment with the :is expression.
    Used for <component :is="expression" /> tags.
    """
    # Build the lambda for the expression and rewrite variable names
    lambda_source = ast.parse(f"lambda: {expression}", mode="eval")
    lambda_names = LambdaNamesCollector()
    lambda_names.visit(lambda_source)

    # Rewrite the lambda to use _lookup for variables
    rewritten_lambda = (
        RewriteName(
            skip=lambda_names.names | names | {"renderer"}, list_names=list_names
        )
        .visit(lambda_source)
        .body
    )

    keywords = [
        ast.keyword(arg="expression", value=rewritten_lambda),
    ]
    if parent:
        keywords.append(
            ast.keyword(arg="parent", value=ast.Name(id=parent, ctx=ast.Load()))
        )

    return ast.Assign(
        targets=[ast.Name(id=el, ctx=ast.Store())],
        value=ast.Call(
            func=ast.Name(id="DynamicFragment", ctx=ast.Load()),
            args=[ast.Name(id="renderer", ctx=ast.Load())],
            keywords=keywords,
        ),
    )


def ast_set_bind(
    el: str,
    key: str,
    value: str,
    names: set[str],
    list_names: list[dict[str, set[str]]],
) -> ast.Expr:
    _, key = key.split(":")
    source = ast.parse(f'{el}.set_bind("{key}", lambda: ({value}))', mode="eval")
    return ast_named_lambda(
        source, {"renderer", "new", el, "watch"} | names, list_names
    )


def ast_set_bind_dict(
    el: str, value: str, names: set[str], list_names: list[dict[str, set[str]]]
) -> ast.Expr:
    source = ast.parse(f"{el}.set_bind_dict('{value}', lambda: {value})", mode="eval")
    return ast_named_lambda(
        source, {"renderer", "new", el, "watch"} | names, list_names
    )


def ast_set_event(
    el: str,
    key: str,
    value: str,
    names: set[str],
    list_names: list[dict[str, set[str]]],
) -> ast.Expr:
    split_char = "@" if key.startswith("@") else ":"
    _, key = key.split(split_char)

    # The event can be a method name, or a function
    # When it is not a function, then the args/kwargs will be passed
    # to the provided method.
    basic_source = ast.parse(value, mode="eval")
    if isinstance(basic_source.body, ast.Name):
        source = ast.parse(
            f"lambda *args, **kwargs: {value}(*args, **kwargs)", mode="eval"
        )
    else:
        source = ast.parse(value, mode="eval")

    # v-on directives allow for lambdas which define arguments
    # which need to be skipped by the RewriteName visitor
    lambda_source = ast_named_lambda(source, {"args", "kwargs"} | names, list_names)

    return ast.Expr(
        value=ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=el, ctx=ast.Load()),
                attr="set_event",
                ctx=ast.Load(),
            ),
            args=[ast.Constant(value=key), lambda_source.value],
            keywords=[],
        )
    )


def ast_set_condition(
    child: str, condition: str, names: set[str], list_names: list[dict[str, set[str]]]
) -> ast.Expr:
    condition_ast = ast.parse(f"lambda: bool({condition})", mode="eval")
    RewriteName(skip=names, list_names=list_names).visit(condition_ast)

    return ast.Expr(
        value=ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=child, ctx=ast.Load()),
                attr="set_condition",
                ctx=ast.Load(),
            ),
            args=[condition_ast.body],
            keywords=[],
        )
    )


def ast_create_control_flow(name: str, parent: str) -> ast.Assign:
    return ast.Assign(
        targets=[ast.Name(id=name, ctx=ast.Store())],
        value=ast.Call(
            func=ast.Name(id="ControlFlowFragment", ctx=ast.Load()),
            args=[
                ast.Name(id="renderer", ctx=ast.Load()),
            ],
            keywords=[
                ast.keyword(
                    arg="parent",
                    value=ast.Name(id=parent, ctx=ast.Load()),
                )
            ],
        ),
    )


def ast_create_list_fragment(name: str, parent: str | None) -> ast.Assign:
    return ast.Assign(
        targets=[ast.Name(id=name, ctx=ast.Store())],
        value=ast.Call(
            func=ast.Name(id="ListFragment", ctx=ast.Load()),
            args=[
                ast.Name(id="renderer", ctx=ast.Load()),
            ],
            keywords=[
                ast.keyword(
                    arg="parent",
                    value=ast.Name(id=parent, ctx=ast.Load()),
                )
            ],
        ),
    )


def safe_tag(tag):
    return tag.replace("-", "_").replace(".", "_")


def create_collagraph_render_function(
    node: Element, names: set[str]
) -> ast.FunctionDef:
    body: list[ast.stmt] = []
    body.append(
        ast.ImportFrom(
            module="observ",
            names=[ast.alias(name="watch"), ast.alias(name="computed")],
            level=0,
        )
    )
    body.append(
        ast.ImportFrom(
            module="collagraph",
            names=[ast.alias(name="Component")],
            level=0,
        )
    )
    body.append(
        ast.ImportFrom(
            module="collagraph.fragment",
            names=[
                # TODO: import only the needed items
                ast.alias(name="ControlFlowFragment"),
                ast.alias(name="ComponentFragment"),
                ast.alias(name="DynamicFragment"),
                ast.alias(name="ListFragment"),
                ast.alias(name="Fragment"),
                ast.alias(name="SlotFragment"),
            ],
            level=0,
        )
    )

    if CGX_RUNTIME_WARNINGS:
        names_str = ", ".join([f"'{name}'" for name in names])
        code = textwrap.dedent(
            f"""
            from warnings import warn as _warn

            for name in {{{names_str}}}:
                if name in self.state:
                    _warn(
                        f"Found imported name '{{name}}' "
                        f"as key in self.state: {{self}}.\\n"
                        "If the value from self.state is intended, please resolve by "
                        f"replacing '{{name}}' with 'state['{{name}}']'"
                    )
                if name in self.props:
                    _warn(
                        f"Found imported name '{{name}}' "
                        f"as key in self.props: {{self}}.\\n"
                        "If the value from self.props is intended, please resolve by "
                        f"replacing '{{name}}' with 'props['{{name}}']'"
                    )
                if hasattr(self, name):
                    _warn(
                        f"Found imported name '{{name}}' "
                        f"as attribute on self: {{self}}.\\n"
                        "If the attribute from self is intended, please resolve by "
                        f"replacing '{{name}}' with 'self.{{name}}'"
                    )
            """
        )
        check_names = ast.parse(code)
        body.extend(check_names.body)

    body.append(
        ast.Assign(
            targets=[ast.Name(id="component", ctx=ast.Store())],
            value=ast.Call(
                func=ast.Name(id="ComponentFragment", ctx=ast.Load()),
                args=[ast.Name(id="renderer", ctx=ast.Load())],
                keywords=[],
            ),
        )
    )

    counter: dict[str, int] = defaultdict(int)

    def create_fragments_function(
        node: Element,
        targets: ast.Name | ast.Tuple,
        names: set,
        list_names: list[dict[str, set[str]]],
    ):
        tag = safe_tag(node.tag)
        fragment_name = f"{tag}{counter[tag]}"
        function_name = f"create_{fragment_name}"
        return_stmt = ast.Return(value=ast.Name(id=fragment_name, ctx=ast.Load()))

        # First define a computed method that unpacks the context into
        # a dictionary

        # We'll also need to rewrite each nested expression to
        # get the right value from the right place...

        # TODO: maybe I could instead hijack the _lookup function with an extra argument
        # that can tell in which extra scope to check! So I keep the scope on the 'root'
        # component (self) (as tuple of dicts n stuff) and then pass in the right scope
        # name or level or identifier or whatever...

        unpacked_name = f"unpacked{counter['unpacked']}"
        counter["unpacked"] += 1
        all_target_names = targets_for_list_expression(targets)

        computed_unpacked_dict = ast.FunctionDef(
            name=unpacked_name,
            args=ast.arguments(
                posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]
            ),
            body=[
                ast.Assign(
                    targets=[targets],
                    value=ast.Call(
                        func=ast.Name(id="context", ctx=ast.Load()),
                        args=[],
                        keywords=[],
                    ),
                ),
                ast.Return(
                    value=ast.Dict(
                        keys=[ast.Constant(value=name) for name in all_target_names],
                        values=[
                            ast.Name(id=name, ctx=ast.Load())
                            for name in all_target_names
                        ],
                    )
                ),
            ],
            decorator_list=[ast.Name(id="computed", ctx=ast.Load())],
        )

        names_collector = StoredNameCollector()
        names_collector.visit(targets)
        unpacked_names = names_collector.names

        function = ast.FunctionDef(
            name=function_name,
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg("context")],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=[
                computed_unpacked_dict,
                *create_children(
                    [node],
                    None,
                    names=names | unpacked_names,
                    list_names=[{unpacked_name: all_target_names}, *list_names],
                    within_for_loop=True,
                ),
                return_stmt,
            ],
            decorator_list=[],
            returns=None,
        )

        return function_name, function

    # Create and add children
    def create_children(
        nodes: list[Element | Comment | TextElement],
        target: str | None,
        names: set,
        list_names: list[dict[str, set[str]]],
        within_for_loop=False,
    ):
        result: list[ast.stmt] = []
        control_flow_parent = None
        for child in nodes:
            if isinstance(child, Comment):
                # Ignore comments
                continue
            if isinstance(child, TextElement):
                # children_args.extend(args_for_text_element(child, names=names))
                # continue
                raise NotImplementedError()

            # Create element name
            tag = safe_tag(child.tag)
            el = f"{tag}{counter[tag]}"
            counter[tag] += 1
            parent = target
            if any(
                True
                for key in child.attrs
                if key.startswith((DIRECTIVE_IF, DIRECTIVE_ELSE, DIRECTIVE_ELSE_IF))
            ):
                parent = None

            # Set static attributes and dynamic (bind) attributes
            attributes: list[ast.stmt] = []
            binds: list[ast.stmt] = []
            events: list[ast.stmt] = []
            condition = None

            node_with_list_expression = False
            if not within_for_loop:
                for key in filter(
                    lambda item: item.startswith(DIRECTIVE_FOR), child.attrs
                ):
                    node_with_list_expression = True
                    # Special v-for node!
                    expression = child.attrs[key]
                    name = f"list{counter['list']}"
                    counter["list"] += 1
                    # Reset any control flow that came before
                    control_flow_parent = None
                    result.append(ast_create_list_fragment(name, parent))
                    expr = f"[None for {expression}]"
                    expression_ast = ast.parse(expr).body[0].value
                    targets: ast.Name | ast.Tuple = expression_ast.generators[0].target
                    # Set the `target` to None so that the targets don't get
                    # rewritten by the RewriteName NodeTransformer
                    # The NodeTransformer doesn't transform the root node, so
                    # we need to pass in the parent node of the node that we
                    # want to transform which is also the parent node of `target`
                    expression_ast.generators[0].target = None

                    RewriteName(names, list_names=list_names).visit(
                        expression_ast.generators[0]
                    )
                    iterator = expression_ast.generators[0].iter

                    (
                        create_frag_func_name,
                        create_frag_function,
                    ) = create_fragments_function(child, targets, names, list_names)
                    is_keyed = ":key" in child.attrs
                    result.append(create_frag_function)

                    # Create key extractor function if this is a keyed list
                    key_extractor = None
                    if is_keyed:
                        key_expr = child.attrs[":key"]
                        # Parse the key expression
                        key_ast = ast.parse(key_expr, mode="eval").body

                        # Create a function that takes context and returns the key
                        # def key_fn(context):
                        #     item, i = context()
                        #     return <key_expr>
                        key_fn_name = f"key_fn{counter['key_fn']}"
                        counter["key_fn"] = counter.get("key_fn", 0) + 1

                        # Create the unpacking assignment
                        unpacking = ast.Assign(
                            targets=[targets],
                            value=ast.Call(
                                func=ast.Name(id="context", ctx=ast.Load()),
                                args=[],
                                keywords=[],
                            ),
                        )

                        # Rewrite variable names in the key expression
                        # We need to rewrite references to loop variables
                        key_fn = ast.FunctionDef(
                            name=key_fn_name,
                            args=ast.arguments(
                                posonlyargs=[],
                                args=[ast.arg("context")],
                                kwonlyargs=[],
                                kw_defaults=[],
                                defaults=[],
                            ),
                            body=[
                                unpacking,
                                ast.Return(value=key_ast),
                            ],
                            decorator_list=[],
                            returns=None,
                        )
                        result.append(key_fn)
                        key_extractor = ast.Name(id=key_fn_name, ctx=ast.Load())

                    result.append(
                        ast.Expr(
                            value=ast.Call(
                                func=ast.Attribute(
                                    value=ast.Name(id=name, ctx=ast.Load()),
                                    attr="set_create_fragment",
                                    ctx=ast.Load(),
                                ),
                                args=[
                                    ast.Name(id=create_frag_func_name, ctx=ast.Load())
                                ],
                                keywords=[
                                    ast.keyword(
                                        "is_keyed", ast.Constant(value=is_keyed)
                                    ),
                                    ast.keyword(
                                        "key_extractor",
                                        key_extractor
                                        if key_extractor
                                        else ast.Constant(value=None),
                                    ),
                                ],
                            )
                        )
                    )

                    iterator_fn = ast.Lambda(
                        args=ast.arguments(
                            posonlyargs=[],
                            args=[],
                            kwonlyargs=[],
                            kw_defaults=[],
                            defaults=[],
                        ),
                        body=iterator,
                    )

                    result.append(
                        ast.Expr(
                            value=ast.Call(
                                func=ast.Attribute(
                                    value=ast.Name(id=name, ctx=ast.Load()),
                                    attr="set_expression",
                                    ctx=ast.Load(),
                                ),
                                args=[iterator_fn],
                                keywords=[],
                            )
                        )
                    )
                    break

            if node_with_list_expression:
                continue

            if control_flow_directive := control_flow(child):
                if control_flow_directive == DIRECTIVE_IF:
                    control_flow_parent = f"control_flow{counter['control_flow']}"
                    counter["control_flow"] += 1
            else:
                # Reset the control flow parent
                control_flow_parent = None

            # Check if this is a dynamic component tag (<component :is="...">)
            is_dynamic_component = child.tag == "component" and ":is" in child.attrs
            is_expression = child.attrs.get(":is") if is_dynamic_component else None

            added_slot_name = False
            for key, value in child.attrs.items():
                if not is_directive(key):
                    attributes.append(ast_set_attribute(el, key, value))
                elif key.startswith((DIRECTIVE_BIND, ":")):
                    if key == DIRECTIVE_BIND:
                        binds.append(ast_set_bind_dict(el, value, names, list_names))
                    elif key == ":is" and is_dynamic_component:
                        # Skip :is for dynamic components - handled in fragment creation
                        pass
                    else:
                        binds.append(ast_set_bind(el, key, value, names, list_names))
                elif key.startswith((DIRECTIVE_ON, "@")):
                    events.append(ast_set_event(el, key, value, names, list_names))
                elif key == DIRECTIVE_IF:
                    assert control_flow_parent is not None
                    assert target is not None
                    result.append(ast_create_control_flow(control_flow_parent, target))
                    condition = ast_set_condition(el, value, names, list_names)
                elif key == DIRECTIVE_ELSE_IF:
                    condition = ast_set_condition(el, value, names, list_names)
                elif key == DIRECTIVE_ELSE:
                    pass
                elif key.startswith((DIRECTIVE_SLOT, "#")):
                    # TODO: how about top-level items that don't have 'slot' defined?
                    if key == DIRECTIVE_SLOT:
                        slot_name = "default"
                    elif key.startswith(DIRECTIVE_SLOT):
                        _, slot_name = key.split(":")
                    elif key.startswith("#"):
                        _, slot_name = key.split("#")
                    attributes.append(ast_set_slot_name(el, slot_name))
                    added_slot_name = True
                elif key == DIRECTIVE_FOR:
                    pass
                else:
                    raise NotImplementedError(key)

            # Check if we need to mark the item as content for the default slot
            if not added_slot_name:
                if parent_node := (child.parent and child.parent()):
                    # This assumes that the parent_node is a component if it starts
                    # with an uppercase character
                    # TODO: come up with a more solid solution for figuring out
                    # whether the parent is a component
                    if parent_node.tag and parent_node.tag[0].isupper():
                        attributes.append(ast_set_slot_name(el, "default"))

            # Create the appropriate fragment type
            if is_dynamic_component:
                # Create DynamicFragment for <component :is="...">
                result.append(
                    ast_create_dynamic_fragment(
                        el,
                        is_expression,
                        parent=control_flow_parent or parent,
                        names=names,
                        list_names=list_names,
                    )
                )
            else:
                # Check if this tag is a loop variable (from v-for)
                # Loop variables should not be treated as components
                is_loop_variable = any(
                    child.tag in loop_vars
                    for loop_dict in list_names
                    for loop_vars in loop_dict.values()
                )

                # Create regular Fragment or ComponentFragment
                is_component = (
                    (child.tag in names and not is_loop_variable)
                    or child.tag[0].isupper()
                    or "." in child.tag
                )
                result.append(
                    ast_create_fragment(
                        el,
                        child.tag,
                        is_component=is_component,
                        parent=control_flow_parent or parent,
                        node=child,
                    )
                )
            if condition:
                result.append(condition)
            result.extend(attributes)
            result.extend(binds)
            result.extend(events)

            # Process the children
            result.extend(create_children(child.children, el, names, list_names))

        return result

    body.extend(create_children(node.children, "component", names, []))

    body.append(ast.Return(value=ast.Name(id="component", ctx=ast.Load())))
    return ast.FunctionDef(
        name="render",
        args=ast.arguments(
            posonlyargs=[],
            args=[ast.arg("self"), ast.arg("renderer")],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[],
        ),
        body=body,
        decorator_list=[],
    )


def is_directive(key):
    return key.startswith((DIRECTIVE_PREFIX, ":", "@", "#"))


def targets_for_list_expression(targets: ast.Name | ast.Tuple) -> set[str]:
    def get_names(value, names):
        if isinstance(value, ast.Name):
            names.add(value.id)
            return
        for val in value.elts:
            get_names(val, names)

    names: set[str] = set()
    get_names(targets, names)
    return names


class StoredNameCollector(ast.NodeVisitor):
    """AST node visitor that will create a set of the ids of every Name node
    it encounters."""

    def __init__(self):
        self.names: set[str] = set()

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.names.add(node.id)


class LambdaNamesCollector(ast.NodeVisitor):
    def __init__(self):
        self.names: set[str] = set()

    def visit_Lambda(self, node):
        # For some reason the body of a lambda is not visited
        # so we need to do it manually.
        # From the docs of ast.NodeVisitor:
        # > Note that child nodes of nodes that have a custom visitor method
        # > won't be visited unless the visitor calls generic_visit() or visits
        # > them itself.
        # So here we visit the children of the Lambda manually
        visitor = LambdaNamesCollector()
        visitor.visit(node.body)
        self.names.update(visitor.names)

        for arg in node.args.posonlyargs + node.args.args + node.args.kwonlyargs:
            self.names.add(arg.arg)


class RewriteName(ast.NodeTransformer):
    """AST node transformer that will try to replace static Name nodes with
    a call to `_lookup` with the name of the node."""

    def __init__(self, skip, list_names):
        self.skip: set[str] = skip
        self.list_names: list[dict[str, set[str]]] = list_names

    def visit_Name(self, node):
        # Don't try and replace any item from the __builtins__
        if node.id in __builtins__:
            return node

        for item in self.list_names:
            for key, value in item.items():
                if node.id in value:
                    return ast.Subscript(
                        value=ast.Call(
                            func=ast.Name(id=key, ctx=ast.Load()), args=[], keywords=[]
                        ),
                        slice=ast.Constant(value=node.id),
                        ctx=ast.Load(),
                    )

        # Don't replace any name that should be explicitely skipped
        if node.id in self.skip:
            return node

        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id="self", ctx=ast.Load()),
                attr="_lookup",
                ctx=ast.Load(),
            ),
            args=[
                ast.Constant(value=node.id),
                ast.Call(
                    func=ast.Name(id="globals", ctx=ast.Load()),
                    args=[],
                    keywords=[],
                ),
            ],
            keywords=[],
        )


class RewriteDots(ast.NodeTransformer):
    def visit_Name(self, node):
        parts = node.id.split(".")
        if len(parts) == 1:
            return node

        first, *parts = parts
        value = ast.Name(id=first, ctx=ast.Load())
        for part in parts:
            value = ast.Attribute(
                value=value,
                attr=part,
                ctx=ast.Load(),
            )
        return value


class ImportsCollector(ast.NodeVisitor):
    def __init__(self):
        self.names = set()

    def visit_ImportFrom(self, node):
        for alias in node.names:
            self.names.add(alias.asname or alias.name)

    def visit_Import(self, node):
        for alias in node.names:
            self.names.add(alias.asname or alias.name)


def control_flow(element):
    """Returns the control flow string (if/else-if/else), if present in the
    attrs of the node."""
    for attr in element.attrs:
        if attr in CONTROL_FLOW_DIRECTIVES:
            return attr


def check_parsed_tree(node: Element):
    # Only check whole trees starting at the root
    assert node.tag == "root"
    children = [child for child in node.children if isinstance(child, Element)]
    if len(children) == 0:
        raise ValueError("Expected at least 2 closed tags, found nothing")
    if len(children) == 1:
        child = children[0]
        if child.tag != "script":
            raise ValueError(f"Only one tag found: {child.tag}. Missing 'script' tag.")
        else:
            raise ValueError("Only script tag found. Missing other tags")

    number_of_script_tags_in_root = len(
        [
            child
            for child in node.children
            if isinstance(child, Element) and child.tag == "script"
        ]
    )
    if number_of_script_tags_in_root != 1:
        raise ValueError(
            f"Expected exactly 1 script tag, found: {number_of_script_tags_in_root}"
        )


def _print_ast_tree_as_code(tree, path):  # pragma: no cover
    """Handy function for debugging an ast tree"""
    from rich.console import Console
    from rich.syntax import Syntax

    plain_result = ast.unparse(tree)
    formatted = format_code(plain_result)
    console = Console()
    syntax = Syntax(formatted, "python")
    console.print(f"#---{path}---")
    console.print(syntax)


def format_code(code):  # pragma: no cover
    """
    Format the given code string with ruff
    """
    from subprocess import run

    result = run(
        ["ruff", "format", "-"],
        input=code,
        encoding="utf-8",
        capture_output=True,
    )
    return result.stdout
