import ast
import atexit
from pathlib import Path

from PyInstaller.lib.modulegraph.modulegraph import DependencyInfo, MissingModule

from collagraph.sfc.compiler import construct_ast, get_script_ast
from collagraph.sfc.parser import CGXParser

# Keep track of generated files so they can be cleaned up
_generated_files: list[Path] = []


def _cleanup_generated_files():
    for path in _generated_files:
        path.unlink(missing_ok=True)


atexit.register(_cleanup_generated_files)


def hook(hook_api):
    collagraph_uses = hook_api.analysis.graph.get_code_using("collagraph")

    hidden_imports = set()
    cgx_modules = set()

    for package, code in collagraph_uses.items():
        source_dir = Path(code.co_filename).parent

        # Collect CGX files and their imports from the source directory
        cgx_files = list(source_dir.glob("**/*.cgx"))
        hidden_imports |= collect_hidden_imports(cgx_files)

        # Pre-compile each CGX file to Python source so that
        # PyInstaller can bundle them as regular Python modules,
        # removing the need to bundle .cgx files and compile them
        # at runtime
        for cgx_path in cgx_files:
            module_name = cgx_path.stem
            tree, _name = construct_ast(cgx_path)
            python_source = ast.unparse(tree)

            # Write compiled module next to the CGX file so
            # PyInstaller can discover it on its existing search path
            py_path = cgx_path.with_suffix(".py")
            if not py_path.exists():
                py_path.write_text(python_source, encoding="utf-8")
                _generated_files.append(py_path)
            cgx_modules.add(module_name)

    # Filter out imports that correspond to CGX modules, since
    # they are now available as pre-compiled Python modules
    hidden_imports -= cgx_modules

    graph = hook_api.analysis.graph

    # Remove any MissingModule nodes for CGX modules that were
    # already marked as missing during initial analysis (before
    # the compiled .py files existed).
    # removeNode() calls hide_node() which moves the node to
    # hidden_nodes. Graph.add_node() silently ignores nodes in
    # hidden_nodes, so we must also delete from hidden_nodes to
    # allow import_hook to re-add the module as a SourceModule.
    for name in cgx_modules:
        node = graph.find_node(name)
        if isinstance(node, MissingModule):
            graph.removeNode(node)
            if name in graph.graph.hidden_nodes:
                del graph.graph.hidden_nodes[name]

    # Import CGX modules via the module graph and create edges
    # to the collagraph node so they are included in the bundle.
    collagraph_node = graph.find_node("collagraph")
    for name in cgx_modules:
        try:
            nodes = graph.import_hook(name, collagraph_node)
            for node in nodes:
                graph._updateReference(
                    collagraph_node,
                    node,
                    edge_data=DependencyInfo(
                        conditional=False,
                        fromlist=False,
                        function=False,
                        tryexcept=False,
                    ),
                )
        except ImportError:
            pass

    # Add remaining hidden imports (non-CGX Python modules)
    hook_api.add_imports(*hidden_imports)


def collect_hidden_imports(cgx_files):
    hidden_imports = set()
    for path in cgx_files:
        template = path.read_text(encoding="utf-8")
        # Parse the file component into a tree of Node instances
        parser = CGXParser()
        parser.feed(template)

        # Get the AST from the script tag
        script_tree = get_script_ast(parser, path)

        # Find a list of imported module names
        imported_names = ImportsCollector()
        imported_names.visit(script_tree)

        hidden_imports |= imported_names.names

    return hidden_imports


class ImportsCollector(ast.NodeVisitor):
    def __init__(self):
        self.names = set()

    def visit_ImportFrom(self, node):
        if node.module:
            self.names.add(node.module)

    def visit_Import(self, node):
        for alias in node.names:
            self.names.add(alias.name)
