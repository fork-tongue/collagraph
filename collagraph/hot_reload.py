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

if TYPE_CHECKING:
    from collagraph import Collagraph

logger = logging.getLogger(__name__)


class FileWatcher:
    """File watcher using watchdog library."""

    def __init__(self, paths: set[Path], callback: Callable[[Path], None]):
        self._callback = callback
        self._paths = paths
        self._observer = None

    def start(self) -> None:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        # Resolve all paths to absolute for consistent matching
        watched_paths = {str(p.resolve()) for p in self._paths}
        # Also track by filename for editors that do atomic saves
        watched_filenames = {Path(p).name for p in watched_paths}
        callback = self._callback
        log = logger  # Capture logger for nested class

        class Handler(FileSystemEventHandler):
            def _check_path(self, event_path: str) -> bool:
                """Check if an event path matches our watched files."""
                try:
                    resolved = str(Path(event_path).resolve())
                except OSError:
                    resolved = event_path

                if resolved in watched_paths:
                    log.debug("Path matched: %s", resolved)
                    callback(Path(resolved))
                    return True

                # Also check by filename (for atomic saves that create new files)
                if Path(event_path).name in watched_filenames:
                    # Verify it's actually our file by checking full path
                    try:
                        resolved = str(Path(event_path).resolve())
                        if resolved in watched_paths:
                            log.debug("Path matched (by name): %s", resolved)
                            callback(Path(resolved))
                            return True
                    except OSError:
                        pass
                return False

            def on_any_event(self, event) -> None:
                if not event.is_directory:
                    log.debug("Event: %s %s", event.event_type, event.src_path)

            def on_modified(self, event) -> None:
                if not event.is_directory:
                    self._check_path(event.src_path)

            def on_created(self, event) -> None:
                # Some editors create a new file instead of modifying
                if not event.is_directory:
                    self._check_path(event.src_path)

            def on_moved(self, event) -> None:
                # Some editors write to temp file then rename (atomic save)
                if not event.is_directory:
                    self._check_path(event.dest_path)

        # Watch directories containing our files (resolved)
        dirs = {p.resolve().parent for p in self._paths}

        self._observer = Observer()
        handler = Handler()
        for dir_path in dirs:
            self._observer.schedule(handler, str(dir_path), recursive=False)
        self._observer.start()

    def stop(self) -> None:
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None

    def update_paths(self, paths: set[Path]) -> None:
        """Update the set of watched paths."""
        # For simplicity, restart the observer with new paths
        self.stop()
        self._paths = paths
        self.start()


class HotReloader:
    """
    Manages hot-reloading for a Collagraph application.

    Tracks imported .cgx modules and reloads them when files change.
    """

    def __init__(self, gui: Collagraph):
        self._gui_ref = weakref.ref(gui)
        self._watched_modules: dict[Path, str] = {}  # path -> module_name
        self._root_module_name: str | None = None
        self._target: Any = None
        self._state: dict | None = None
        self._watcher: FileWatcher | None = None
        self._debounce_timer: threading.Timer | None = None
        self._debounce_lock = threading.Lock()
        self._reload_pending = False
        self._qt_signal_helper = None

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

        # Start file watcher
        if self._watched_modules:
            self._watcher = FileWatcher(
                set(self._watched_modules.keys()), self._on_file_changed
            )
            self._watcher.start()
            for path in self._watched_modules.keys():
                logger.info("Watching: %s", path)

    def stop(self) -> None:
        """Stop watching for file changes."""
        if self._watcher:
            self._watcher.stop()
            self._watcher = None
        if self._debounce_timer:
            self._debounce_timer.cancel()
            self._debounce_timer = None

    def _collect_cgx_modules(self) -> None:
        """Collect all .cgx modules that should be watched."""
        from collagraph.sfc.importer import get_loaded_cgx_modules

        # Get all loaded CGX modules
        all_cgx = get_loaded_cgx_modules()

        # For now, watch all loaded CGX modules
        # A more sophisticated approach would walk the import tree
        # starting from root_module_name
        self._watched_modules = {path: name for name, path in all_cgx.items()}

    def _on_file_changed(self, path: Path) -> None:
        """Handle a file change event (called from watchdog thread)."""
        logger.debug("File changed callback: %s", path)
        with self._debounce_lock:
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
        """Perform the actual reload."""
        gui = self._gui_ref()
        if gui is None or gui.fragment is None:
            return

        logger.info("Reloading...")

        # Phase 1: Try to reimport modules (validate before unmounting)
        try:
            self._invalidate_modules()
            module = importlib.import_module(self._root_module_name)
            importlib.reload(module)
            # Use getattr to avoid Python name mangling of __component_class
            component_class = getattr(module, "__component_class")
        except Exception:
            logger.exception("Error during reload, keeping old UI")
            return

        # Phase 2: Unmount and re-render (only if compile succeeded)
        try:
            # Store target reference before unmounting
            target = self._target

            # Clear Component lookup cache to prevent stale lookups
            from collagraph.component import Component

            Component.__lookup_cache__.clear()

            # Unmount current fragment tree
            gui.fragment.unmount(destroy=True)
            gui.fragment = None

            # Re-render with fresh component class
            gui.render(component_class, target, self._state)

            # Re-collect modules (dependencies may have changed)
            self._collect_cgx_modules()

            # Update watcher with new file list
            if self._watcher:
                self._watcher.update_paths(set(self._watched_modules.keys()))

            logger.info("Reload complete")

        except Exception:
            logger.exception("Error during re-render")

    def _invalidate_modules(self) -> None:
        """Remove tracked CGX modules from sys.modules."""
        from collagraph.sfc.importer import clear_cgx_module

        for module_name in list(self._watched_modules.values()):
            # Remove from sys.modules to force reimport
            if module_name in sys.modules:
                del sys.modules[module_name]
            # Clear from CGX loader registry
            clear_cgx_module(module_name)
