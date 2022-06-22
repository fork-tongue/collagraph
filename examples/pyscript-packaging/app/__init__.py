import collagraph as cg

from .app import App  # noqa: I202


def start(container):
    gui = cg.Collagraph(renderer=cg.DomRenderer())
    gui.render(cg.h(App), container)
