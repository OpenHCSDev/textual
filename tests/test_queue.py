import asyncio

import pytest

from textual.message_pump import OWING, SETTLED, Queue


async def test_peek_leaves_the_head_for_a_waiting_consumer():
    queue = Queue()
    waiting = asyncio.create_task(queue.get())
    try:
        await asyncio.sleep(0)
        with pytest.raises(asyncio.QueueEmpty):
            queue.peek_nowait()
        queue.put_nowait("head")
        assert queue.peek_nowait() == "head"
        assert await asyncio.wait_for(waiting, 1) == "head"
        assert queue.empty()
    finally:
        waiting.cancel()
        await asyncio.gather(waiting, return_exceptions=True)


async def test_owing_from_a_put_until_a_get_finds_none_left():
    queue = Queue()
    assert queue.activity is SETTLED
    queue.put_nowait("message")
    assert queue.activity is OWING
    assert await queue.get() == "message"
    assert queue.activity is OWING
    waiting = asyncio.create_task(queue.get())
    try:
        await asyncio.sleep(0)
        assert queue.activity is SETTLED
    finally:
        waiting.cancel()
        await asyncio.gather(waiting, return_exceptions=True)
