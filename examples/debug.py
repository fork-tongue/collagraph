import collagraph as cg

from debug_example import DebugExample  # noqa: I100


if __name__ == "__main__":
    container = {"type": "root"}
    gui = cg.Collagraph(event_loop_type=cg.EventLoopType.SYNC)
    gui.render(cg.h(DebugExample), container)

    print(container)  # noqa: T001
