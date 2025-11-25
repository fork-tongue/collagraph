from __future__ import annotations

import sys
from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec, SourceFileLoader
from pathlib import Path
from types import ModuleType
from typing import Sequence

from collagraph.component import Component

from .compiler import SUFFIX, construct_ast


class CGXLoader(SourceFileLoader):
    """
    Loader for .cgx files. Subclassing SourceFileLoader provides .pyc caching support.
    """

    def source_to_code(self, data, path: str):
        """
        Convert cgx files to Python code, then compile it to bytecode.
        """
        # Convert custom cgx format to Python AST
        tree, _component_name = construct_ast(path, data.decode("utf-8"))

        # Compile Python source to bytecode
        return compile(tree, path, mode="exec")

    def exec_module(self, module):
        super().exec_module(module)
        # Check that the class definition is an actual subclass of Component
        namespace = module.__dict__
        if component_class := namespace.get("__component_class__"):
            if not issubclass(component_class, Component):
                raise ValueError(
                    f"The last class defined in {self.path} is not a subclass of "
                    f"Component: {component_class}"
                )


class CGXPathFinder(MetaPathFinder):
    """MetaPathFinder for CGX files"""

    def find_spec(
        self, name: str, path: Sequence[str] | None, target: ModuleType | None = None
    ) -> ModuleSpec | None:
        # """Look for a cgx file based on the given name and return a ModuleSpec"""
        if target is not None:
            # Target is set when module is being reloaded.
            # In our case we can just return the existing spec.
            return target.__spec__

        _package, _, module_name = name.rpartition(".")
        sfc_file_name = f"{module_name}.{SUFFIX}"
        directories = sys.path if path is None else path
        for directory in directories:
            sfc_path = Path(directory) / sfc_file_name
            if sfc_path.exists():
                loader = CGXLoader(name, str(sfc_path))
                spec = ModuleSpec(name, loader, origin=str(sfc_path))
                spec.has_location = True
                return spec


# Add cgx path finder at the end of the list of finders
sys.meta_path.append(CGXPathFinder())
