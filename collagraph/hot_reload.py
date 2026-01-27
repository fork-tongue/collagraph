"""
Hot reload support for Collagraph.

Provides file watching and module reloading for .cgx single-file components.
"""

from __future__ import annotations

import importlib
import logging
import sys
import threading
import weakref
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

import colorlog
from observ import to_raw

if TYPE_CHECKING:
    from collagraph import Collagraph
    from collagraph.fragment import Fragment


def setup_logger():
    root = logging.getLogger()
    root_level = root.getEffectiveLevel()
    """Return a logger with a default ColoredFormatter."""
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)-8s%(reset)s [%(module)s] %(blue)s%(message)s",
        datefmt=None,
        reset=True,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
        secondary_log_colors={},
        style="%",
    )

    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(root_level)

    return logger


logger = setup_logger()


class SharedFileWatcher:
    """
    Singleton file watcher shared by multiple HotReloader instances.

    Avoids watchdog errors when multiple watchers try to observe the same directory.
    """

    _instance: SharedFileWatcher | None = None
    _lock = threading.Lock()

    def __new__(cls) -> SharedFileWatcher:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._observer = None
        self._handlers: dict[int, Callable[[Path], None]] = {}  # id -> callback
        self._watched_paths: dict[int, set[Path]] = {}  # id -> paths
        self._watched_dirs: set[Path] = set()
        self._handler_lock = threading.Lock()

    def register(
        self, handler_id: int, paths: set[Path], callback: Callable[[Path], None]
    ) -> None:
        """Register a callback for a set of paths."""
        with self._handler_lock:
            self._handlers[handler_id] = callback
            self._watched_paths[handler_id] = {p.resolve() for p in paths}
            self._update_observer()

    def unregister(self, handler_id: int) -> None:
        """Unregister a callback."""
        with self._handler_lock:
            self._handlers.pop(handler_id, None)
            self._watched_paths.pop(handler_id, None)
            if not self._handlers:
                self._stop_observer()
            else:
                self._update_observer()

    def update_paths(self, handler_id: int, paths: set[Path]) -> None:
        """Update the paths for a registered handler."""
        with self._handler_lock:
            if handler_id in self._handlers:
                self._watched_paths[handler_id] = {p.resolve() for p in paths}
                self._update_observer()

    def _update_observer(self) -> None:
        """Update the observer to watch all needed directories."""
        # Collect all paths from all handlers
        all_paths: set[Path] = set()
        for paths in self._watched_paths.values():
            all_paths.update(paths)

        # Get directories to watch
        new_dirs = {p.parent for p in all_paths}

        # Check if we need to restart
        if new_dirs != self._watched_dirs:
            self._stop_observer()
            self._watched_dirs = new_dirs
            if new_dirs:
                self._start_observer()

    def _start_observer(self) -> None:
        """Start the watchdog observer."""
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError as e:
            raise ImportError(
                "Hot reload requires the 'watchdog' package. "
                "Install it with: pip install watchdog"
            ) from e

        watcher = self  # Capture for nested class

        class Handler(FileSystemEventHandler):
            def _check_path(self, event_path: str) -> None:
                """Check if an event path matches any watched files."""
                try:
                    resolved = Path(event_path).resolve()
                except OSError:
                    return

                with watcher._handler_lock:
                    for handler_id, paths in watcher._watched_paths.items():
                        if resolved in paths:
                            callback = watcher._handlers.get(handler_id)
                            if callback:
                                logger.debug("Path matched: %s", resolved)
                                callback(resolved)

            def on_modified(self, event) -> None:
                if not event.is_directory:
                    self._check_path(event.src_path)

            def on_created(self, event) -> None:
                if not event.is_directory:
                    self._check_path(event.src_path)

            def on_moved(self, event) -> None:
                if not event.is_directory:
                    self._check_path(event.dest_path)

        self._observer = Observer()
        handler = Handler()
        for dir_path in self._watched_dirs:
            self._observer.schedule(handler, str(dir_path), recursive=False)
        self._observer.start()

    def _stop_observer(self) -> None:
        """Stop the watchdog observer."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None


class HotReloader:
    """
    Manages hot-reloading for a Collagraph application.

    Tracks imported .cgx modules and reloads them when files change.
    """

    def __init__(self, gui: Collagraph, use_watchdog: bool = True):
        self._gui_ref = weakref.ref(gui)
        self._watched_modules: dict[Path, str] = {}  # path -> module_name
        self._root_module_name: str | None = None
        self._target: Any = None
        self._state: dict | None = None
        self._watcher_id: int = id(self)  # Unique ID for SharedFileWatcher
        self._debounce_timer: threading.Timer | None = None
        self._debounce_lock = threading.Lock()
        self._pending_changed_paths: set[Path] = set()
        self._qt_signal_helper = None
        self._use_watchdog = use_watchdog

        # Set up Qt signal helper for thread-safe reloading
        try:
            from PySide6.QtCore import QObject, Signal

            class QtReloadSignal(QObject):
                reload_signal = Signal()

            self._qt_signal_helper = QtReloadSignal()
            self._qt_signal_helper.reload_signal.connect(self._reload)
        except ImportError:
            pass

    def start(
        self, root_module_name: str, target: Any, state: dict | None = None
    ) -> None:
        """Start watching for file changes."""
        self._root_module_name = root_module_name
        self._target = target
        self._state = state

        # Collect all imported .cgx modules
        self._collect_cgx_modules()

        # Register with shared file watcher (unless disabled for testing)
        if self._watched_modules and self._use_watchdog:
            SharedFileWatcher().register(
                self._watcher_id,
                set(self._watched_modules.keys()),
                self._on_file_changed,
            )
            for path in self._watched_modules.keys():
                logger.debug("Watching: %s", path)

    def stop(self) -> None:
        """Stop watching for file changes."""
        if self._use_watchdog:
            SharedFileWatcher().unregister(self._watcher_id)
        if self._debounce_timer:
            self._debounce_timer.cancel()
            self._debounce_timer = None
        # Disconnect Qt signal to avoid dangling references
        if self._qt_signal_helper is not None:
            try:
                self._qt_signal_helper.reload_signal.disconnect(self._reload)
            except (RuntimeError, TypeError):
                pass  # Already disconnected or no connections

    def reload(self, preserve_state: bool = True) -> bool:
        """
        Manually trigger a reload.

        Args:
            preserve_state: If True, component state is preserved across reload.

        Returns True if reload succeeded, False otherwise.
        This method is synchronous and should be called from the main thread.
        """
        gui = self._gui_ref()
        if gui is None or gui.fragment is None:
            logger.warning("Cannot reload: GUI or fragment is None")
            return False

        logger.info("Reloading%s...", " (preserving state)" if preserve_state else "")

        # Collect component state before unmounting
        preserved_state = None
        if preserve_state:
            preserved_state = self._collect_component_state(gui.fragment)
            logger.debug("Collected state from %d components", len(preserved_state))

        # Collect renderer-specific element state (e.g., window geometry)
        element_state = None
        root_element = self._find_root_element(gui.fragment)
        if root_element is not None:
            element_state = gui.renderer.save_element_state(root_element)

        # Phase 1: Try to reimport modules (validate before unmounting)
        try:
            self._invalidate_modules()
            module = importlib.import_module(self._root_module_name)
            importlib.reload(module)
            component_class = getattr(module, "__component_class")
        except Exception:
            logger.exception("Error during reload, keeping old UI")
            return False

        # Phase 2: Unmount and re-render (only if compile succeeded)
        try:
            target = self._target

            from collagraph.component import Component

            Component.__lookup_cache__.clear()

            gui.fragment.unmount(destroy=True)
            gui.fragment = None

            gui.render(component_class, target, self._state)

            # Restore component state after remount
            if preserve_state and preserved_state:
                restored = self._restore_component_state(gui.fragment, preserved_state)
                logger.debug("Restored state to %d components", restored)

            # Restore renderer-specific element state
            new_root_element = self._find_root_element(gui.fragment)
            if element_state and new_root_element is not None:
                gui.renderer.restore_element_state(new_root_element, element_state)

            self._collect_cgx_modules()

            if self._use_watchdog:
                SharedFileWatcher().update_paths(
                    self._watcher_id, set(self._watched_modules.keys())
                )

            logger.info("Reload complete")
            return True

        except Exception:
            logger.exception("Error during re-render")
            return False

    def _collect_cgx_modules(self) -> None:
        """Collect CGX modules that are actually used in this Collagraph's tree.

        This includes:
        1. Modules whose components are currently rendered in the fragment tree
        2. CGX modules imported by those modules (for dynamic :is="..." components)

        The second case handles scenarios like:
        - parent.cgx imports child_a.cgx and child_b.cgx
        - parent.cgx uses :is="type_map(obj_type)" to dynamically select which to render
        - Even if child_a is not currently rendered, it should still be watched
        """
        from collagraph.sfc.importer import get_loaded_cgx_modules

        gui = self._gui_ref()
        if gui is None or gui.fragment is None:
            return

        # Get all loaded CGX modules (name -> path)
        all_cgx = get_loaded_cgx_modules()

        # Find which modules are actually used in our fragment tree
        used_modules = self._collect_used_modules(gui.fragment)

        # Expand to include CGX modules imported by used modules
        # This catches dynamically loaded components (via :is directive)
        expanded_modules = self._expand_cgx_imports(used_modules, all_cgx)

        # Watch all expanded modules
        self._watched_modules = {
            path: name for name, path in all_cgx.items() if name in expanded_modules
        }

    def _expand_cgx_imports(
        self, used_modules: set[str], all_cgx: dict[str, Path]
    ) -> set[str]:
        """Expand the set of used modules to include any CGX modules they import.

        This recursively finds all CGX modules that are imported (directly or
        indirectly) by the currently used modules. This ensures that dynamically
        loaded components (via :is directive) are also watched for hot reload.

        Args:
            used_modules: Module names currently used in the fragment tree
            all_cgx: Dictionary mapping module names to file paths for all
                loaded CGX modules

        Returns:
            Expanded set of module names including imported CGX dependencies
        """
        from collagraph.component import Component

        expanded = set(used_modules)
        to_check = list(used_modules)
        checked: set[str] = set()

        while to_check:
            module_name = to_check.pop()
            if module_name in checked:
                continue
            checked.add(module_name)

            # Get the module from sys.modules
            module = sys.modules.get(module_name)
            if module is None:
                continue

            # Look through the module's namespace for Component subclasses
            # that come from CGX modules
            for attr_name in dir(module):
                try:
                    attr = getattr(module, attr_name)
                except Exception:
                    continue

                # Check if it's a Component subclass (but not Component itself)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, Component)
                    and attr is not Component
                ):
                    # Check if this component comes from a CGX module
                    component_module = attr.__module__
                    if component_module in all_cgx and component_module not in expanded:
                        expanded.add(component_module)
                        to_check.append(component_module)

        return expanded

    def _on_file_changed(self, path: Path) -> None:
        """Handle a file change event (called from watchdog thread)."""
        logger.debug("File changed callback: %s", path)
        with self._debounce_lock:
            # Track which files changed
            self._pending_changed_paths.add(path)

            # Cancel any pending reload
            if self._debounce_timer:
                self._debounce_timer.cancel()

            # Schedule reload with debounce delay
            self._debounce_timer = threading.Timer(0.1, self._trigger_reload)
            self._debounce_timer.start()
            logger.debug("Debounce timer started")

    def _trigger_reload(self) -> None:
        """Trigger reload on the main thread."""
        logger.debug("Trigger reload called")
        gui = self._gui_ref()
        if gui is None:
            logger.warning("GUI reference is None, cannot reload")
            return

        # Schedule the reload on the main event loop
        if self._qt_signal_helper is not None:
            # Use signal/slot for thread-safe Qt communication
            logger.debug("Emitting reload signal")
            self._qt_signal_helper.reload_signal.emit()
        else:
            # Fallback: try asyncio
            try:
                import asyncio

                loop = asyncio.get_event_loop()
                loop.call_soon_threadsafe(self._reload)
            except RuntimeError:
                # No event loop, call directly (might cause issues)
                self._reload()

    def _reload(self) -> None:
        """Internal callback for file watcher triggered reloads."""
        # Get and clear pending changed paths
        with self._debounce_lock:
            changed_paths = self._pending_changed_paths.copy()
            self._pending_changed_paths.clear()

        # Try fine-grained reload first
        if changed_paths:
            if self._reload_changed_files(changed_paths):
                return

        # Fall back to full reload
        self.reload()

    def _invalidate_modules(self) -> None:
        """Remove tracked CGX modules from sys.modules."""
        from collagraph.sfc.importer import clear_cgx_module

        for module_name in list(self._watched_modules.values()):
            # Remove from sys.modules to force reimport
            if module_name in sys.modules:
                del sys.modules[module_name]
            # Clear from CGX loader registry
            clear_cgx_module(module_name)

    def _reload_changed_files(
        self, changed_paths: set[Path], preserve_state: bool = True
    ) -> bool:
        """
        Attempt fine-grained reload of only the changed files.

        Returns True if fine-grained reload succeeded, False if full reload needed.
        """
        from collagraph.sfc.importer import clear_cgx_module

        gui = self._gui_ref()
        if gui is None or gui.fragment is None:
            return False

        # Map changed paths to module names
        changed_modules = set()
        for path in changed_paths:
            if path in self._watched_modules:
                changed_modules.add(self._watched_modules[path])

        if not changed_modules:
            return False

        # Check if root module changed - need full reload
        if self._root_module_name in changed_modules:
            logger.info("Root component changed, doing full reload")
            return False

        # Find all ComponentFragments that use components from changed modules
        affected = self._find_affected_fragments(gui.fragment, changed_modules)

        if not affected:
            logger.info("No affected components found, skipping reload")
            return True

        logger.info(
            "Fine-grained reload: %d component(s) from %s",
            len(affected),
            ", ".join(changed_modules),
        )

        # Phase 1: Try to reload the changed modules (validate before unmounting)
        try:
            for module_name in changed_modules:
                # Clear from sys.modules and CGX registry
                if module_name in sys.modules:
                    del sys.modules[module_name]
                clear_cgx_module(module_name)

                # Reimport to validate
                importlib.import_module(module_name)
        except Exception:
            logger.exception("Error reloading module, keeping old UI")
            return False

        # Clear lookup cache entries that reference changed modules
        self._clear_lookup_cache_for_modules(changed_modules)

        # Phase 2: Remount affected fragments
        try:
            for fragment in affected:
                self._remount_fragment(fragment, preserve_state)

            logger.info("Fine-grained reload complete")
            return True

        except Exception:
            logger.exception("Error during fine-grained reload, trying full reload")
            return False

    def _find_affected_fragments(
        self, fragment: Fragment, changed_modules: set[str]
    ) -> list[Fragment]:
        """
        Find all ComponentFragments using components from the changed modules.

        Returns fragments in order from deepest to shallowest (children before parents)
        so that remounting doesn't affect parent iteration.
        """
        affected: list[Fragment] = []
        self._find_affected_recursive(fragment, changed_modules, affected)
        return affected

    def _find_affected_recursive(
        self,
        fragment: Fragment,
        changed_modules: set[str],
        affected: list[Fragment],
    ) -> bool:
        """
        Recursively find affected fragments.

        Traverses the full fragment tree including:
        - Regular children (fragment.children)
        - DynamicFragment's active fragment (_active_fragment)
        - ComponentFragment's rendered content (fragment.fragment)
        - ComponentFragment's slot contents (slot_contents)

        Returns True if this fragment or any descendant is affected.
        """
        from collagraph.fragment import ComponentFragment, DynamicFragment

        # Recurse into regular children
        for child in fragment.children:
            self._find_affected_recursive(child, changed_modules, affected)

        # Handle DynamicFragment - it stores the actual rendered component
        # in _active_fragment, not in children
        if isinstance(fragment, DynamicFragment) and fragment._active_fragment:
            self._find_affected_recursive(
                fragment._active_fragment, changed_modules, affected
            )

        # Handle ComponentFragment - traverse its rendered content and slot contents
        if isinstance(fragment, ComponentFragment):
            # The component's rendered template
            if fragment.fragment:
                self._find_affected_recursive(
                    fragment.fragment, changed_modules, affected
                )
            # Slot contents (children passed to the component)
            for slot_child in fragment.slot_contents:
                self._find_affected_recursive(slot_child, changed_modules, affected)

        # Check if this fragment itself is affected
        if isinstance(fragment, ComponentFragment) and fragment.component:
            component_module = type(fragment.component).__module__
            if component_module in changed_modules:
                affected.append(fragment)
                return True

        return False

    def _remount_fragment(self, fragment: Fragment, preserve_state: bool) -> None:
        """Remount a single ComponentFragment with updated component class.

        Handles fragments in various locations:
        - Regular children (parent.children)
        - DynamicFragment's active fragment (parent._active_fragment)
        - ComponentFragment's rendered content (parent.fragment)
        """
        from collagraph.fragment import ComponentFragment

        if not isinstance(fragment, ComponentFragment) or not fragment.component:
            return

        component = fragment.component
        component_name = type(component).__name__
        module_name = type(component).__module__

        # Collect state before unmounting
        preserved_state = None
        if preserve_state:
            preserved_state = self._collect_component_state(fragment)

        # Preserve fragment configuration that would be lost during
        # unmount(destroy=True). These are set during template compilation
        # and need to be restored for remount.
        preserved_attributes: dict[str, str] = fragment._attributes.copy()
        preserved_binds: list[tuple] = fragment._binds.copy()
        preserved_events: dict[str, Callable] = fragment._events.copy()
        preserved_ref_name = fragment._ref_name
        preserved_ref_is_dynamic = fragment._ref_is_dynamic

        # Get the parent and target for remounting
        parent = fragment.parent
        target = fragment.target

        # Find anchor element (first element in next sibling) for correct positioning
        # Need to handle different parent types:
        # - DynamicFragment: fragment is in _active_fragment, not children
        # - ComponentFragment: fragment might be in .fragment attribute or slot_contents
        # - Regular Fragment: fragment is in children
        anchor = None
        if parent:
            # Check if fragment is in parent.children
            if fragment in parent.children:
                idx = parent.children.index(fragment)
                if idx + 1 < len(parent.children):
                    # Get the first element from the next sibling's subtree
                    anchor = self._find_root_element(parent.children[idx + 1])
            # Check if fragment is in parent.slot_contents (for ComponentFragment)
            elif (
                isinstance(parent, ComponentFragment)
                and hasattr(parent, "slot_contents")
                and fragment in parent.slot_contents
            ):
                idx = parent.slot_contents.index(fragment)
                if idx + 1 < len(parent.slot_contents):
                    # Get the first element from the next slot sibling's subtree
                    anchor = self._find_root_element(parent.slot_contents[idx + 1])
            # For DynamicFragment._active_fragment or ComponentFragment.fragment,
            # we use the fragment's own anchor() method after unmounting
            # (anchor will remain None, which is fine - it means append at end)

        # Unmount the old fragment
        fragment.unmount(destroy=True)

        # Get the new component class from the reloaded module
        module = sys.modules.get(module_name)
        if module is None:
            module = importlib.import_module(module_name)

        new_class = getattr(module, component_name, None)
        if new_class is None:
            raise RuntimeError(f"Component {component_name} not found in {module_name}")

        # Restore preserved fragment configuration before remount
        # This ensures static props, events, and refs work after hot reload
        fragment._attributes = preserved_attributes
        fragment._binds = preserved_binds
        fragment._events = preserved_events
        fragment._ref_name = preserved_ref_name
        fragment._ref_is_dynamic = preserved_ref_is_dynamic

        # Update the fragment's tag to the new class
        fragment.tag = new_class

        # Remount
        fragment.mount(target, anchor)

        # Restore state
        if preserve_state and preserved_state:
            self._restore_component_state(fragment, preserved_state)

    def _clear_lookup_cache_for_modules(self, module_names: set[str]) -> None:
        """Clear Component lookup cache entries that reference changed modules."""
        from collagraph.component import Component

        for parent_cls, cache in list(Component.__lookup_cache__.items()):
            # Check if the parent class itself is from a changed module
            if parent_cls.__module__ in module_names:
                del Component.__lookup_cache__[parent_cls]
                continue

            # Remove cache entries that reference classes from changed modules
            for name, child_cls in list(cache.items()):
                if child_cls.__module__ in module_names:
                    del cache[name]

    def _collect_used_modules(self, fragment: Fragment) -> set[str]:
        """Walk fragment tree and collect module names of all components."""
        from collagraph.fragment import ComponentFragment

        modules: set[str] = set()
        self._collect_used_modules_recursive(fragment, modules, ComponentFragment)
        return modules

    def _collect_used_modules_recursive(
        self, fragment: Fragment, modules: set[str], component_fragment_cls: type
    ) -> None:
        """Recursively collect module names from fragment tree.

        Traverses the full fragment tree including:
        - Regular children (fragment.children)
        - DynamicFragment's active fragment (_active_fragment)
        - ComponentFragment's rendered content (fragment.fragment)
        - ComponentFragment's slot contents (slot_contents)
        """
        from collagraph.fragment import DynamicFragment

        if isinstance(fragment, component_fragment_cls) and fragment.component:
            module_name = type(fragment.component).__module__
            modules.add(module_name)

        # Recurse into regular children
        for child in fragment.children:
            self._collect_used_modules_recursive(child, modules, component_fragment_cls)

        # Handle DynamicFragment - it stores the actual rendered component
        # in _active_fragment, not in children
        if isinstance(fragment, DynamicFragment) and fragment._active_fragment:
            self._collect_used_modules_recursive(
                fragment._active_fragment, modules, component_fragment_cls
            )

        # Handle ComponentFragment - traverse its rendered content and slot contents
        if isinstance(fragment, component_fragment_cls):
            # The component's rendered template
            if fragment.fragment:
                self._collect_used_modules_recursive(
                    fragment.fragment, modules, component_fragment_cls
                )
            # Slot contents (children passed to the component)
            for slot_child in fragment.slot_contents:
                self._collect_used_modules_recursive(
                    slot_child, modules, component_fragment_cls
                )

    def _find_root_element(self, fragment: Fragment) -> Any:
        """
        Find the root element in a fragment tree.

        The top-level fragment may be a transient fragment (tag=None) without
        an element. This walks the tree to find the first actual element,
        which for PySide would be the top-level window widget.
        """
        if fragment.element is not None:
            return fragment.element

        # Check children
        for child in fragment.children:
            element = self._find_root_element(child)
            if element is not None:
                return element

        return None

    def _collect_component_state(self, fragment: Fragment) -> dict:
        """
        Walk fragment tree and collect component state for preservation.

        Returns a nested dict structure:
        {
            (class_name, key): {
                "state": {...},
                "children": {
                    (child_class_name, child_key): {...},
                    ...
                }
            },
            ...
        }
        """
        from collagraph.fragment import ComponentFragment

        state_tree: dict = {}
        self._collect_state_recursive(fragment, state_tree, 0, ComponentFragment)
        return state_tree

    def _collect_state_recursive(
        self,
        fragment: Fragment,
        state_tree: dict,
        index: int,
        component_fragment_cls: type,
    ) -> None:
        """Recursively collect state from fragment tree."""
        if isinstance(fragment, component_fragment_cls) and fragment.component:
            component = fragment.component
            # Use 'key' prop if available, otherwise use position index
            key = component.props.get("key", index) if component.props else index
            identity = (type(component).__name__, key)

            # Convert state to raw (non-reactive) objects to avoid
            # issues with proxies during hot-reload
            state_copy = to_raw(component.state)

            state_tree[identity] = {
                "state": state_copy,
                "children": {},
            }

            # Collect children's state
            child_state = state_tree[identity]["children"]
            for i, child in enumerate(fragment.children):
                self._collect_state_recursive(
                    child, child_state, i, component_fragment_cls
                )
        else:
            # Non-component fragment, just recurse into children
            for i, child in enumerate(fragment.children):
                self._collect_state_recursive(
                    child, state_tree, i, component_fragment_cls
                )

    def _restore_component_state(self, fragment: Fragment, state_tree: dict) -> int:
        """
        Walk new fragment tree and restore preserved state.

        Returns the number of components that had state restored.
        """
        from collagraph.fragment import ComponentFragment

        return self._restore_state_recursive(fragment, state_tree, 0, ComponentFragment)

    def _restore_state_recursive(
        self,
        fragment: Fragment,
        state_tree: dict,
        index: int,
        component_fragment_cls: type,
    ) -> int:
        """Recursively restore state to fragment tree."""
        restored_count = 0

        if isinstance(fragment, component_fragment_cls) and fragment.component:
            component = fragment.component
            # Use 'key' prop if available, otherwise use position index
            key = component.props.get("key", index) if component.props else index
            identity = (type(component).__name__, key)

            if identity in state_tree:
                preserved = state_tree[identity]
                # Merge preserved state into component's current state
                for state_key, value in preserved["state"].items():
                    if state_key in component.state:
                        try:
                            component.state[state_key] = value
                            restored_count += 1
                        except Exception:
                            logger.debug(
                                "Failed to restore state key '%s' for %s",
                                state_key,
                                identity[0],
                            )

                logger.debug("Restored state for %s", identity[0])

                # Restore children's state
                child_state = preserved.get("children", {})
                for i, child in enumerate(fragment.children):
                    restored_count += self._restore_state_recursive(
                        child, child_state, i, component_fragment_cls
                    )
        else:
            # Non-component fragment, just recurse into children
            for i, child in enumerate(fragment.children):
                restored_count += self._restore_state_recursive(
                    child, state_tree, i, component_fragment_cls
                )

        return restored_count
