"""
An *optionally* awaitable object returned by methods that remove widgets.
"""

from __future__ import annotations

import asyncio
from asyncio import Future, Task, gather
from typing import TYPE_CHECKING, Generator

import rich.repr

from textual._callback import invoke
from textual._debug import get_caller_file_and_line
from textual._types import CallbackType

if TYPE_CHECKING:
    from textual.message_pump import MessagePump


@rich.repr.auto
class AwaitRemove:
    """An awaitable that waits for nodes to be removed."""

    def __init__(
        self, tasks: list[Task], post_remove: CallbackType | None = None
    ) -> None:
        self._tasks = list(tasks)
        self._post_remove = post_remove
        self._caller = get_caller_file_and_line()
        self._completion: Future[None] | None = None
        self._finisher: Task[None] | None = None
        self._scheduled = False

    def __rich_repr__(self) -> rich.repr.Result:
        yield "tasks", self._tasks
        yield "post_remove", self._post_remove
        yield "caller", self._caller, None

    async def __call__(self) -> None:
        await self

    def _start(self) -> Future[None]:
        """One independently-owned teardown completion for all optional waiters."""
        if self._completion is None:
            self._completion = asyncio.get_running_loop().create_future()
            self._finisher = asyncio.create_task(self._finish(), name="complete removal")
        return self._completion

    async def _finish(self) -> None:
        assert self._completion is not None
        try:
            await gather(*self._tasks)
            if self._post_remove is not None:
                await invoke(self._post_remove)
        except asyncio.CancelledError:
            self._completion.cancel()
        except BaseException as error:
            self._completion.set_exception(error)
        else:
            self._completion.set_result(None)
        finally:
            # A retained receipt is data about completion, not an owner of the
            # pruned tree, its callbacks or task contexts.
            self._tasks.clear()
            self._post_remove = None
            self._finisher = None

    def call_when_ready(self, node: MessagePump) -> None:
        """Deliver the completed receipt without blocking the receiver's queue.

        The application's message pump must remain available while another
        widget runs an asynchronous unmount handler. Observe errors through the
        ordinary callback path only after this transaction has actually ended.
        """
        if self._scheduled:
            return
        self._scheduled = True

        def completed(future: Future[None]) -> None:
            if node._closing or node._closed:
                if not future.cancelled():
                    future.exception()
                return
            node.call_next(self)

        self._start().add_done_callback(completed)

    def __await__(self) -> Generator[None, None, None]:
        current_task = asyncio.current_task()
        self_removal = current_task in self._tasks
        other_tasks = [task for task in self._tasks if task is not current_task]

        async def await_prune() -> None:
            completion = self._start()
            if self_removal:
                # A widget's handler has to return before its own message pump
                # can process Prune. The independent completion still waits for
                # that real exit before publishing the removal.
                await gather(*(asyncio.shield(task) for task in other_tasks))
                return
            await asyncio.shield(completion)

        return await_prune().__await__()
