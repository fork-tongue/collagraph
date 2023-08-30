import importlib
from pathlib import Path


for module in Path(__file__).parent.glob("*.py"):
    if module.name.startswith("_"):
        continue

    importlib.import_module(f".{module.stem}", "collagraph.renderers.pyside.objects")
