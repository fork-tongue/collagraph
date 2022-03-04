from enum import Enum
from itertools import zip_longest
import shutil
from typing import Any, Dict, Iterable

from rich import print as console
from rich.traceback import install

terminal_width = shutil.get_terminal_size((80, 20)).columns - 2
install(width=terminal_width)


class OpType(Enum):
    MOVE = "MOVE"
    DEL = "DEL"
    ADD = "ADD"


def apply_op(op: Dict, it: Iterable):
    if op["op"] is OpType.MOVE:
        idx = it.index(op["value"])
        val = it.pop(idx)
        new_idx = it.index(op["anchor"])
        it.insert(new_idx, val)
    elif op["op"] is OpType.DEL:
        it.remove(op["value"])
    elif op["op"] is OpType.ADD:
        idx = it.index(op["anchor"]) if "anchor" in op else len(it)
        it.insert(idx, op["value"])


def create_operation(type, value: Any = None, anchor: Any = None):
    """
    Returns:
        Operation as a simple dict with the following keys:
        - op: type of operation: ["DEL", "ADD", "MOVE"]
        - value: value of the item
        - anchor (optional): the element before which this element is
          to be inserted
    """
    result = {"op": type, "value": value}
    if anchor is not None:
        result["anchor"] = anchor
    assert type is not OpType.MOVE or "anchor" in result
    return result


def create_ops(current, future):
    """
    Args:
        current: list of keys as they are currently rendered in the dom
        future: list of keys as they should be rendered in the dom

    Returns:
        list of operations to apply (in order) to convert `current` to
        `future`. See `create_operation` for more details.
    """
    ops = []
    wip = current.copy()

    # First figure out all the deletions that need to take place
    for idx, old in enumerate(current):
        if old not in future:
            ops.append(create_operation(OpType.DEL, value=old))
            apply_op(ops[-1], wip)

    # Then figure out all the movements and deletions
    for idx, (old, new) in enumerate(zip_longest(current, future)):
        if new is not None and new not in current:
            anchor = wip[idx] if idx < len(wip) else None
            ops.append(create_operation(OpType.ADD, value=new, anchor=anchor))
            apply_op(ops[-1], wip)

        if old is not None and new is None:
            # The deletion ops have already been recorded
            continue

        idx_before = wip.index(new)

        if idx_before != idx:
            # If an item is moved back, then the offset will be increased
            anchor = wip[idx] if idx < len(wip) else None
            ops.append(create_operation(OpType.MOVE, value=new, anchor=anchor))
            apply_op(ops[-1], wip)

    return ops


if __name__ == "__main__":
    console("=============================")
    states = [
        (["a", "b", "c"], ["c", "a", "b"], "shift right"),
        (["a", "b", "c"], ["b", "c", "a"], "shift left"),
        (["a", "b", "c"], ["c", "b", "a"], "reverse order"),
        (["a", "b", "c"], ["a", "c"], "remove from middle"),
        (["a", "b", "c"], ["b", "c"], "remove first"),
        (["a", "b", "c"], ["a", "b"], "remove last"),
        (["a", "b", "c"], ["a", "b", "c", "d"], "add last"),
        (["a", "b", "c"], ["a", "b", "d", "c"], "add in middle"),
        (["a", "b", "c"], ["d", "a", "b", "c"], "add begin"),
        (["a", "b", "c", "d"], ["e", "f"], "replace completely"),
    ]

    for before, after, operation in states:
        console(f"--- {operation.capitalize()} ---")
        console(f"{before}")

        # Create operations by comparing before and after lists
        ops = create_ops(before, after)
        console(ops)

        # Check that applying the operations works properly
        target = before.copy()
        for op in ops:
            apply_op(op, target)

        console(f"Success: {target == after} \n{target}")
        if target != after:
            console(f"{after}")

        console("")
