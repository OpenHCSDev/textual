"""Accepted work has one lifetime, even when its wrapper never starts."""
import asyncio
import gc
import inspect
import sys
from threading import Event
from types import coroutine as iterable_coroutine
from collections.abc import Coroutine

import pytest

from textual.app import App
from textual.worker import WorkerCancelled, WorkerState


class ProtocolCoroutine(Coroutine[None, None, None]):
    """A non-native implementation of Python's public Coroutine contract."""

    def __init__(self, coroutine):
        self.coroutine = coroutine

    def __await__(self):
        return self.coroutine.__await__()

    def send(self, value):
        return self.coroutine.send(value)

    def throw(self, *args):
        return self.coroutine.throw(*args)

    def close(self):
        self.coroutine.close()


def native_coroutine(coroutine):
    return coroutine


@pytest.mark.filterwarnings("error::RuntimeWarning")
@pytest.mark.parametrize("factory", [native_coroutine, ProtocolCoroutine])
@pytest.mark.parametrize("thread", [False, True])
@pytest.mark.parametrize("start", [False, True])
@pytest.mark.parametrize("eager", [False, pytest.param(True, marks=pytest.mark.skipif(
    sys.version_info < (3, 12), reason="Eager tasks require Python 3.12"))])
async def test_cancel_before_start_disposes_accepted_coroutine(factory, thread, start, eager):
    called = False

    async def work():
        nonlocal called
        called = True

    app = App()
    async with app.run_test():
        loop = asyncio.get_running_loop()
        previous = loop.get_task_factory()
        try:
            loop.set_task_factory(asyncio.eager_task_factory if eager else None)
            coroutine = work()
            worker = app.run_worker(factory(coroutine), thread=thread, start=start)
            worker.cancel()
            with pytest.raises(WorkerCancelled):
                await worker.wait()
            assert worker.state is WorkerState.CANCELLED
            assert inspect.getcoroutinestate(coroutine) == inspect.CORO_CLOSED
            assert worker not in app.workers
            assert not called
            # start_all cannot revive already cancelled deferred work.
            app.workers.start_all()
            assert not called
            del worker, coroutine
        finally:
            loop.set_task_factory(previous)
    gc.collect()


@pytest.mark.parametrize("thread", [False, True])
@pytest.mark.parametrize("start", [False, True])
async def test_cancel_before_start_closes_iterable_coroutine(thread, start):
    @iterable_coroutine
    def work():
        yield

    app = App()
    async with app.run_test():
        coroutine = work()
        worker = app.run_worker(coroutine, thread=thread, start=start)
        worker.cancel()
        with pytest.raises(WorkerCancelled):
            await worker.wait()
        assert inspect.getgeneratorstate(coroutine) == inspect.GEN_CLOSED


@pytest.mark.parametrize("thread", [False, True])
async def test_cancel_before_start_cancels_accepted_future(thread):
    app = App()
    async with app.run_test():
        future = asyncio.get_running_loop().create_future()
        worker = app.run_worker(future, thread=thread)
        worker.cancel()
        with pytest.raises(WorkerCancelled):
            await worker.wait()
        assert future.cancelled()
        assert worker not in app.workers


async def test_cancel_all_removes_deferred_workers():
    async def work():
        raise AssertionError("Cancelled deferred work must not run")

    app = App()
    async with app.run_test():
        workers = [app.run_worker(work(), start=False) for _ in range(3)]
        app.workers.cancel_all()
        assert not app.workers
        assert all(worker.state is WorkerState.CANCELLED for worker in workers)


async def test_cancel_does_not_close_work_adopted_by_a_running_thread():
    started, release, finished = Event(), Event(), Event()

    async def work():
        started.set()
        assert release.wait(5)
        finished.set()

    app = App()
    async with app.run_test():
        coroutine = work()
        worker = app.run_worker(coroutine, thread=True)
        try:
            assert await asyncio.to_thread(started.wait, 5)
            worker.cancel()
            with pytest.raises(WorkerCancelled):
                await worker.wait()
            assert inspect.getcoroutinestate(coroutine) == inspect.CORO_RUNNING
        finally:
            release.set()
        assert await asyncio.to_thread(finished.wait, 5)
        deadline = asyncio.get_running_loop().time() + 5
        while (inspect.getcoroutinestate(coroutine) != inspect.CORO_CLOSED
               and asyncio.get_running_loop().time() < deadline):
            await asyncio.sleep(0.001)
        assert inspect.getcoroutinestate(coroutine) == inspect.CORO_CLOSED
