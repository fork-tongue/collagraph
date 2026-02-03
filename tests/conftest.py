import asyncio
import gc
import textwrap

import pytest
from observ import scheduler
from observ.proxy_db import proxy_db

from collagraph.renderers import Renderer
from collagraph.sfc import load_from_string


async def miniloop():
    await asyncio.sleep(0)


def load(source, namespace=None):
    source = textwrap.dedent(source)
    return load_from_string(source, namespace=namespace)


@pytest.fixture
def parse_source():
    yield load


@pytest.fixture(autouse=True)
def cleanup():
    """Cleanup steps copied over observ test suite"""
    gc.collect()
    proxy_db.db = {}

    yield

    scheduler.clear()


@pytest.fixture
def process_events():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def run():
        loop.run_until_complete(miniloop())

    yield run

    loop.close()


class CustomElement:
    """Custom element for testing that stores data in a dict."""

    def __init__(self, *args, type=None, **kwargs):
        super().__setattr__(
            "_data",
            {
                "type": type,
                "children": [],
                "event_listeners": {},
                **kwargs,
            },
        )

    def __getattr__(self, name):
        if name.startswith("_"):
            return super().__getattr__(name)
        return self._data[name]

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
        self._data[name] = value

    def add_event_listener(self, event_type, value):
        event_listeners = self._data["event_listeners"]
        listeners = event_listeners.setdefault(event_type, [])
        listeners.append(value)

    def remove_event_listener(self, event_type, value):
        event_listeners = self._data["event_listeners"]
        listeners = event_listeners.get(event_type)
        listeners.remove(value)
        if not listeners:
            del event_listeners[event_type]

    def trigger(self, event_type):
        event_listeners = self._data["event_listeners"]
        for listener in event_listeners.get(event_type, []):
            listener()

    def __repr__(self):
        attributes = ", ".join(
            [
                f"{attr}='{self._data[attr]}'"
                for attr in self._data
                if attr not in ["type", "children", "event_listeners"]
            ]
        )
        return f"<{self.type} {attributes}>"


class CustomElementRenderer(Renderer):
    """Renderer that creates CustomElement instances."""

    def create_element(self, type):
        return CustomElement(type=type)

    def insert(self, el, parent, anchor=None):
        idx = parent.children.index(anchor) if anchor else len(parent.children)
        parent.children.insert(idx, el)

    def remove(self, el, parent):
        parent.children.remove(el)

    def set_attribute(self, el, attr: str, value):
        setattr(el, attr, value)

    def remove_attribute(self, el, attr: str, value):
        delattr(el, attr)

    def add_event_listener(self, el, event_type, value):
        el.add_event_listener(event_type, value)

    def remove_event_listener(self, el, event_type, value):
        el.remove_event_listener(event_type, value)

    def create_text_element(self):
        raise NotImplementedError

    def set_element_text(self):
        raise NotImplementedError


class TrackingRenderer(CustomElementRenderer):
    """Renderer that tracks DOM operations for efficiency testing."""

    def __init__(self):
        super().__init__()
        self.insert_count = 0
        self.remove_count = 0
        self.create_count = 0
        self.operations = []

    def create_element(self, type):
        self.create_count += 1
        self.operations.append(("create", type))
        return super().create_element(type)

    def insert(self, el, parent, anchor=None):
        self.insert_count += 1
        anchor_label = anchor._data.get("content") if anchor else None
        anchor_desc = f"before {anchor_label}" if anchor_label else "end"
        el_label = el._data.get("content") or el.type
        self.operations.append(("insert", el_label, anchor_desc))
        super().insert(el, parent, anchor)

    def remove(self, el, parent):
        self.remove_count += 1
        el_label = el._data.get("content") or el.type
        self.operations.append(("remove", el_label))
        super().remove(el, parent)

    def reset_counters(self):
        """Reset operation counters."""
        self.insert_count = 0
        self.remove_count = 0
        self.create_count = 0
        self.operations = []
