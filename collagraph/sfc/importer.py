from __future__ import annotations

import sys
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType
from typing import Sequence

from . import compiler, load

# Registry of loaded CGX modules: module_name -> file_path
# Used by hot-reload to track which files to watch
_loaded_cgx_modules: dict[str, Path] = {}


def get_loaded_cgx_modules() -> dict[str, Path]:
    """Return a copy of the loaded CGX modules registry."""
    return dict(_loaded_cgx_modules)


def clear_cgx_module(module_name: str) -> None:
    """Remove a module from the CGX registry."""
    _loaded_cgx_modules.pop(module_name, None)


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
        # Track the loaded module for hot-reload (use absolute path for matching)
        _loaded_cgx_modules[module.__name__] = self.sfc_path.resolve()


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
