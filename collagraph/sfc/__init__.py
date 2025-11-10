from .compiler import construct_ast


def load_from_string(template, path=None, namespace=None):
    """
    Load template from a string.
    Returns tuple of class definition and module namespace.
    """
    if path is None:
        path = "<template>"

    # Convert .cgx to Python source code (includes validation)
    source, name = construct_ast(path=path, template=template)

    # Compile and execute the source
    code = compile(source, filename=str(path), mode="exec")
    if namespace is None:
        namespace = {}
    exec(code, namespace)

    component_class = namespace[name]
    return component_class, namespace
