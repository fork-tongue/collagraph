import asyncio

import pytest

# If there is no current event loop, then get_event_loop()
# will emit a deprecation warning since Python 3.12, which
# will be turned into an error for future versions of Python.
# https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.get_event_loop
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


async def miniloop():
    await asyncio.sleep(0)


@pytest.fixture
def process_events():
    loop = asyncio.get_event_loop_policy().get_event_loop()

    def run():
        loop.run_until_complete(miniloop())

    yield run
