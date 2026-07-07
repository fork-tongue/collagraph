from collagraph import Component

from .compiler import DEBUG, construct_ast, format_code


def load(path, namespace=None):
    """
    Loads and returns a component from a .cgx file.

    A subclass of Component will be created from the .cgx file
    where the contents of all tags in the root will be used as
    the `render` function, except for the contents of the <script>
    tag, which will be used to provide the body of the component.

    For example:

        <item foo="bar">
          <item baz="bla"/>
        </item>

        <script>
        import collagraph as cg

        class Foo(cg.Component):
            pass
        </script>

    """
    template = path.read_text(encoding="utf-8")

    return load_from_string(template, path, namespace=namespace)


def load_from_string(template, path=None, namespace=None):
    """
    Load template from a string.
    Returns tuple of class definition and module namespace.
    """
    if path is None:
        path = "<template>"

    # Construct the AST tree
    tree, name = construct_ast(path=path, template=template)

    # Compile the tree into a code object (module)
    # When CGX_DEBUG is set, write the AST to a temporary Python file
    # and reparse it so that debuggers can step through the generated
    # source with correct line numbers.
    filename = str(path)
    if DEBUG:
        debug_file, source = _write_debug_file(tree, path)
        if debug_file:
            import ast
            import logging

            try:
                debug_tree = ast.parse(source, filename=str(debug_file))
            except SyntaxError as e:
                logging.getLogger(__name__).warning(
                    "Could not parse debug source, falling back to original tree",
                    exc_info=e,
                )
            else:
                filename = str(debug_file)
                tree = debug_tree

    code = compile(tree, filename=filename, mode="exec")
    # Execute the code as module and pass a dictionary that will capture
    # the global and local scope of the module
    if namespace is None:
        namespace = {}
    exec(code, namespace)

    # Check that the class definition is an actual subclass of Component
    component_class = namespace[name]
    if not issubclass(component_class, Component):
        raise ValueError(
            f"The last class defined in {path} is not a subclass of "
            f"Component: {component_class}"
        )
    namespace["__component_class"] = component_class
    namespace["__component_name"] = name
    return component_class, namespace


def print_source(source, path, footer=None):
    """Pretty print (Python) source with rich, when available,
    falling back to plain print otherwise.
    """
    try:
        from rich.console import Console
        from rich.syntax import Syntax

        console = Console()
        console.print(f"#---{path}---")
        console.print(Syntax(source, "python", line_numbers=True))
        if footer:
            console.print(f"[dim]{footer}[/dim]")
    except ImportError:
        print(f"#---{path}---")  # noqa: T201
        print(source)  # noqa: T201
        if footer:
            print(footer)  # noqa: T201


def _write_debug_file(tree, path):
    """Write the compiled AST to a temporary Python file for debugging.

    Returns a tuple of (path, formatted_source), or (None, None) if writing fails.
    """
    import ast
    import logging
    import tempfile
    from pathlib import Path

    logger = logging.getLogger(__name__)

    try:
        formatted = format_code(ast.unparse(tree))

        # Create a meaningful filename based on the source .cgx file
        source_name = Path(path).stem if path else "template"
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=f"cgx_{source_name}_",
            suffix=".py",
            delete=False,
        ) as fh:
            fh.write(formatted)
        debug_file = Path(fh.name)
        logger.debug("CGX debug file written to: %s", debug_file)

        print_source(formatted, path, footer=f"Debug file: {debug_file}")

        return debug_file, formatted
    except Exception as e:
        logger.warning("Could not write AST debug file", exc_info=e)
        return None, None
