from enum import Enum
from itertools import zip_longest
import shutil
from typing import Any, Dict, Iterable

from rich import print as console
from rich.traceback import install

terminal_width = shutil.get_terminal_size((80, 20)).columns - 2
install(width=terminal_width)


class Type(Enum):
    MOVE = "MOVE"
    DEL = "DEL"
    ADD = "ADD"


def create_ops(type, value: Any = None, idx: int = None, anchor: Any = None):
    result = {"op": type.value}
    if value is not None:
        result["value"] = value
    if idx is not None:
        result["idx"] = idx
    if anchor is not None:
        result["anchor"] = anchor
    return result


def apply_op(op: Dict, it: Iterable):
    if op["op"] == Type.MOVE.value:
        idx = it.index(op["value"])
        val = it.pop(idx)
        new_idx = it.index(op["anchor"])
        it.insert(new_idx, val)
    elif op["op"] == Type.DEL.value:
        it.pop(op["idx"])
    elif op["op"] == Type.ADD.value:
        idx = it.index(op["anchor"]) if "anchor" in op else len(it)
        it.insert(idx, op["value"])


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

        ops = []
        offsets = {}
        wip = before.copy()
        for idx, (old, new) in enumerate(zip_longest(before, after)):
            if new is not None and new not in before:
                anchor = wip[idx] if idx < len(wip) else None
                ops.append(create_ops(Type.ADD, value=new, anchor=anchor))
                apply_op(ops[-1], wip)

            if old is not None and old not in after:
                ops.append(create_ops(Type.DEL, value=old, idx=wip.index(old)))
                apply_op(ops[-1], wip)

            if old is not None and new is None:
                continue

            idx_before = wip.index(new)

            if idx_before != idx:
                # If an item is moved back, then the offset will be increased
                anchor = wip[idx] if idx < len(wip) else None
                ops.append(create_ops(Type.MOVE, value=new, anchor=anchor))
                apply_op(ops[-1], wip)

        console(ops)

        # Check that applying the operations works properly
        start = before.copy()
        for op in ops:
            apply_op(op, start)

        console(f"Success: {start == after} \n{start}")
        if start != after:
            console(f"{after}")

        console("")
