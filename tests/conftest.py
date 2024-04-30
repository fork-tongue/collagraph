import gc
import textwrap

import pytest
from observ import scheduler
from observ.proxy_db import proxy_db

from collagraph import sfc


def load(source, namespace=None):
    source = textwrap.dedent(source)
    return sfc.compiler.load_from_string(source, namespace=namespace)


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
