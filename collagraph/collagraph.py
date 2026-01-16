from __future__ import annotations

from collections.abc import Callable
from typing import Any

from observ import scheduler

from collagraph.component import Component
from collagraph.constants import EventLoopType
from collagraph.renderers import Renderer


class Collagraph:
    def __init__(
        self,
        renderer: Renderer,
        *,
        event_loop_type: EventLoopType | None = None,
        hot_reload: bool = False,
        hot_reload_watchdog: bool = True,
    ):
        if not isinstance(renderer, Renderer):
            raise TypeError(f"Expected a Renderer but got a {type(renderer)}")
        self.renderer = renderer
        self._hot_reload = hot_reload
        self._hot_reload_watchdog = hot_reload_watchdog
        self._hot_reloader = None
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
        component_class: Callable[[dict], Component],
        target: Any,
        state: dict | None = None,
    ):
        """
        target: DOM element/instance to render into.
        state: state that gets passed into the component as top-level props.
        """
        # Here is the 'root' component which will carry the state
        component = component_class(state or {})

        # component.render() returns a fragment which is then mounted
        # into the target (DOM) element
        self.fragment = component.render(renderer=self.renderer)
        self.fragment.component = component
        self.fragment.mount(target)

        # Start hot reloading if enabled (only on first render)
        if self._hot_reload and self._hot_reloader is None:
            from collagraph.hot_reload import HotReloader

            module_name = component_class.__module__
            self._hot_reloader = HotReloader(
                self, use_watchdog=self._hot_reload_watchdog
            )
            self._hot_reloader.start(module_name, target, state)

    def reload(self, preserve_state: bool = True) -> bool:
        """
        Manually trigger a hot reload.

        Args:
            preserve_state: If True, component state is preserved across reload.

        Returns True if reload succeeded, False if hot_reload is not enabled
        or if the reload failed.
        """
        if self._hot_reloader is None:
            return False
        return self._hot_reloader.reload(preserve_state=preserve_state)
