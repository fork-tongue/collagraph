from collagraph import Component

from .compiler import construct_ast


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
    template = path.read_text()

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
    code = compile(tree, filename=str(path), mode="exec")
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
