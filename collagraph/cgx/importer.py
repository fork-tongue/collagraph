from importlib.machinery import ModuleSpec
import pathlib
import re
import sys

from . import cgx


class CgxImporter:
    def __init__(self, cgx_path):
        """Store path to cgx file"""
        self.cgx_path = cgx_path

    @classmethod
    def find_spec(cls, name, path, target=None):
        """Look for cgx files"""

        package, _, module_name = name.rpartition(".")
        cgx_file_name = f"{module_name}.{cgx.SUFFIX}"
        directories = sys.path if path is None else path
        for directory in directories:
            cgx_path = pathlib.Path(directory) / cgx_file_name
            if cgx_path.exists():
                return ModuleSpec(name, cls(cgx_path))

    def create_module(self, spec):
        """Returning None uses the standard machinery for creating modules"""
        return None

    def exec_module(self, module):
        """Executing the module means reading the cgx file"""
        component = cgx.load(self.cgx_path)

        # Add the data to the module
        module.__dict__[component.__name__] = component
        module.__file__ = str(self.cgx_path)

    def __repr__(self):
        """Nice representation of the class"""
        return f"{self.__class__.__name__}({str(self.cgx_path)!r})"


def _identifier(var_str):
    """Create a valid identifier from a string

    See https://stackoverflow.com/a/3305731
    """
    return re.sub(r"\W|^(?=\d)", "_", var_str)


# Add the Cgx importer at the end of the list of finders
sys.meta_path.append(CgxImporter)
