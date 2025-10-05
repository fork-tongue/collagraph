from __future__ import annotations

import sys
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType
from typing import Sequence

from . import compiler, load


class CGXLoader(Loader):
    """Loader for .cgx files"""

    def __init__(self, sfc_path):
        """Create loader and store the referenced file"""
        self.sfc_path = sfc_path

    def create_module(self, spec):
        # Return None to make use of the standard machinery for creating modules
        return None

    def exec_module(self, module):
        """Exec the compiled code, using the given module's __dict__ as namespace
        in order to instantiate the module"""
        load(self.sfc_path, namespace=module.__dict__)


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
        sfc_file_name = f"{module_name}.{compiler.SUFFIX}"
        directories = sys.path if path is None else path
        for directory in directories:
            sfc_path = Path(directory) / sfc_file_name
            if sfc_path.exists():
                spec = ModuleSpec(name, CGXLoader(sfc_path), origin=str(sfc_path))
                spec.has_location = True
                return spec


# Add cgx path finder at the end of the list of finders
sys.meta_path.append(CGXPathFinder())
