import asyncio
import gc
import textwrap

import pytest
from observ import scheduler
from observ.proxy_db import proxy_db

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
