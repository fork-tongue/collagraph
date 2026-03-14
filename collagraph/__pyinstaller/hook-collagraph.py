import ast
import logging
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

from collagraph.sfc.compiler import get_script_ast
from collagraph.sfc.parser import CGXParser

logger = logging.getLogger(__name__)


def hook(hook_api):
    collagraph_uses = hook_api.analysis.graph.get_code_using("collagraph")

    hidden_imports = set()
    datas = []
    cgx_modules = set()
    for package, code in collagraph_uses.items():
        source_dir = Path(code.co_filename).parent

        # Collect CGX files and their imports from the source directory
        cgx_files = list(source_dir.glob("**/*.cgx"))
        hidden_imports |= collect_hidden_imports(cgx_files)
        cgx_modules |= {path.stem for path in cgx_files}

        # Try package-based collection for installed packages
        package_datas = collect_data_files(package, includes=["**/*.cgx"])
        if package_datas:
            datas += package_datas
        else:
            # For standalone scripts, collect CGX files directly
            for cgx_path in cgx_files:
                relative = cgx_path.relative_to(source_dir)
                dest_dir = str(relative.parent)
                if dest_dir == ".":
                    dest_dir = ""
                datas.append((str(cgx_path), dest_dir or "."))

    # Filter out imports that correspond to CGX modules, since those
    # are loaded at runtime by the CGX import hook, not by PyInstaller
    hidden_imports -= cgx_modules

    hook_api.add_imports(*hidden_imports)
    hook_api.add_datas(datas)


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
