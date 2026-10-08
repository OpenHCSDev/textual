from __future__ import annotations

from asyncio import Future, gather
from typing import TYPE_CHECKING, Any, Awaitable, Generator

import rich.repr
from typing_extensions import Self

from textual._debug import get_caller_file_and_line
from textual.message_pump import MessagePump

if TYPE_CHECKING:
    from textual.types import CallbackType


@rich.repr.auto(angular=True)
class AwaitComplete:
    """An 'optionally-awaitable' object which runs one or more coroutines (or other awaitables) concurrently."""

    def __init__(
        self, *awaitables: Awaitable, pre_await: CallbackType | None = None
    ) -> None:
        """Create an AwaitComplete.

        Args:
            awaitables: One or more awaitables to run concurrently.
        """
        self._awaitables = awaitables
        self._future: Future[Any] = gather(*awaitables)
        self._pre_await: CallbackType | None = pre_await
        self._caller = get_caller_file_and_line()
        self._scheduled = False

    def __rich_repr__(self) -> rich.repr.Result:
        yield self._awaitables
        yield "pre_await", self._pre_await, None
        yield "caller", self._caller, None

    def set_pre_await_callback(self, pre_await: CallbackType | None) -> None:
        """Set a callback to run prior to awaiting.

        This is used by Textual, mainly to check for possible deadlocks.
        You are unlikely to need to call this method in an app.

        Args:
            pre_await: A callback.
        """
        self._pre_await = pre_await

    def call_next(self, node: MessagePump) -> Self:
        """Await after the next message.

        Args:
            node: The node which created the object.
        """
        node.call_next(self)
        return self

    def _start(self) -> Future[Any]:
        """The completion owned by this optional awaitable."""
        return self._future

    def call_when_ready(self, node: MessagePump) -> None:
        """Deliver completion without occupying the receiver's message pump.

        Mount and removal retain their own completion lifetimes. The original
        callback path observes their result only when awaiting it cannot block
        input or other messages behind another widget's startup / teardown.
        """
        if self._scheduled:
            return
        self._scheduled = True

        def completed(future: Future[Any]) -> None:
            if node._closing or node._closed:
                if not future.cancelled():
                    future.exception()
                return
            node.call_next(self)

        self._start().add_done_callback(completed)

    async def __call__(self) -> Any:
        return await self

    def __await__(self) -> Generator[Any, None, Any]:
        _rich_traceback_omit = True
        if self._pre_await is not None:
            self._pre_await()
        return self._future.__await__()

    @property
    def is_done(self) -> bool:
        """`True` if the task has completed."""
        return self._future.done()

    @property
    def exception(self) -> BaseException | None:
        """An exception if the awaitables failed."""
        if self._future.done():
            return self._future.exception()
        return None

    @classmethod
    def nothing(cls):
        """Returns an already completed instance of AwaitComplete."""
        instance = cls()
        instance._future = Future()
        instance._future.set_result(None)  # Mark it as completed with no result
        return instance
