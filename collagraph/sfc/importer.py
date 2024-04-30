import pathlib
import sys
from importlib.machinery import ModuleSpec

from . import compiler


class CGXImporter:
    def __init__(self, sfc_path):
        """Store path to cgx file"""
        self.sfc_path = sfc_path

    @classmethod
    def find_spec(cls, name, path, target=None):
        """Look for cgx files"""
        if target is not None:
            # Target is set when module is being reloaded.
            # In our case we can just return the existing spec.
            return target.__spec__

        package, _, module_name = name.rpartition(".")
        sfc_file_name = f"{module_name}.{compiler.SUFFIX}"
        directories = sys.path if path is None else path
        for directory in directories:
            sfc_path = pathlib.Path(directory) / sfc_file_name
            if sfc_path.exists():
                spec = ModuleSpec(name, cls(sfc_path), origin=str(sfc_path))
                spec.has_location = True
                return spec

    def create_module(self, spec):
        """Returning None uses the standard machinery for creating modules"""
        return

    def exec_module(self, module):
        """Executing the module means reading the cgx file"""
        component, context = compiler.load(self.sfc_path)
        # Add the default module keys to the context such that
        # __file__, __name__ and such are available to the loaded module
        context.update(module.__dict__)

        module.__dict__.update(context)
        module.__dict__[component.__name__] = component


# Add the Cgx importer at the end of the list of finders
sys.meta_path.append(CGXImporter)
