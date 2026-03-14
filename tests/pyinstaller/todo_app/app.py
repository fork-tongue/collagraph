import json

import collagraph as cg

from todo_list import TodoList

container = {"type": "root"}
gui = cg.Collagraph(
    renderer=cg.DictRenderer(),
    event_loop_type=cg.EventLoopType.SYNC,
)
gui.render(TodoList, container)


def serialize(obj):
    """Serialize the rendered dict tree to a JSON-compatible structure."""
    if isinstance(obj, dict):
        return {k: serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize(v) for v in obj]
    return obj


result = serialize(container)
print(json.dumps(result, indent=2))
