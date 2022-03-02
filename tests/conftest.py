import asyncio

import pytest


async def miniloop():
    for i in range(2):
        await asyncio.sleep(0.001)


@pytest.fixture
def process_events():
    loop = asyncio.get_event_loop()

    def process_events():
        loop.run_until_complete(miniloop())

    yield process_events
