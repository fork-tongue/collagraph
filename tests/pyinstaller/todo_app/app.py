import json

import collagraph as cg

from todo_list import TodoList

container = {"type": "root"}
gui = cg.Collagraph(
    renderer=cg.DictRenderer(),
    event_loop_type=cg.EventLoopType.SYNC,
)
gui.render(TodoList, container)

print(json.dumps(container, indent=2))
