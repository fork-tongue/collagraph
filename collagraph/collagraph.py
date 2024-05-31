from collections.abc import Callable
from typing import Any

from observ import scheduler

from collagraph.component import Component
from collagraph.renderers import Renderer
from collagraph.types import EventLoopType


class Collagraph:
    def __init__(self, renderer: Renderer, *, event_loop_type: EventLoopType = None):
        if not isinstance(renderer, Renderer):
            raise TypeError(f"Expected a Renderer but got a {type(renderer)}")
        self.renderer = renderer
        if not event_loop_type:
            event_loop_type = (
                renderer.preferred_event_loop_type() or EventLoopType.DEFAULT
            )
        self.event_loop_type = event_loop_type
        if self.event_loop_type is EventLoopType.DEFAULT:
            scheduler.register_asyncio()
            renderer.register_asyncio()
        else:
            scheduler.register_request_flush(scheduler.flush)

    def render(
        self,
        component_class: Callable[[dict], type[Component]],
        target: Any,
        state=None,
    ):
        """
        target: DOM element/instance to render into.
        state: state that gets passed into the component as top-level props.
        """
        # Here is the 'root' component which will carry the state
        component = component_class(state or {})

        # component.render() returns a fragment which is then mounted
        # into the target (DOM) element
        self.fragment = component.render(self.renderer)
        self.fragment.component = component
        self.fragment.mount(target)
