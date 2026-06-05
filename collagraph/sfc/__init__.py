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
    if DEBUG:  # pragma: no cover
        debug_file, source = _write_debug_file(tree, path)
        if debug_file:
            import ast

            filename = str(debug_file)
            tree = ast.parse(source, filename=filename)

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


def _write_debug_file(tree, path):  # pragma: no cover
    """Write the compiled AST to a temporary Python file for debugging.

    Returns a tuple of (path, formatted_source), or (None, None) if writing fails.
    """
    import ast
    import logging
    import tempfile
    from pathlib import Path

    logger = logging.getLogger(__name__)

    try:
        plain_result = ast.unparse(tree)
        formatted = format_code(plain_result)

        # Create a meaningful filename based on the source .cgx file
        source_name = Path(path).stem if path else "template"
        debug_file = Path(tempfile.mktemp(prefix=f"cgx_{source_name}_", suffix=".py"))
        debug_file.write_text(formatted, encoding="utf-8")
        logger.debug("CGX debug file written to: %s", debug_file)

        try:
            from rich.console import Console
            from rich.syntax import Syntax

            console = Console()
            syntax = Syntax(formatted, "python")
            console.print(f"#---{path}---")
            console.print(syntax)
            console.print(f"[dim]Debug file: {debug_file}[/dim]")
        except ImportError:
            print(f"#---{path}---")  # noqa: T201
            print(formatted)  # noqa: T201
            print(f"Debug file: {debug_file}")  # noqa: T201

        return debug_file, formatted
    except Exception as e:
        logger.warning("Could not write AST debug file", exc_info=e)
        return None, None
