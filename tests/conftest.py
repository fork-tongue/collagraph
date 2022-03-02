import asyncio

import pytest


async def miniloop():
    await asyncio.sleep(0)


@pytest.fixture
def process_events():
    loop = asyncio.get_event_loop()

    def run():
        loop.run_until_complete(miniloop())

    yield run
