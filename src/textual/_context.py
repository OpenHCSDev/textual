from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from textual.app import App
    from textual.message import Message
    from textual.message_pump import MessagePump


class NoActiveAppError(RuntimeError):
    """Runtime error raised if we try to retrieve the active app when there is none."""


active_app: ContextVar["App[Any]"] = ContextVar("active_app")
active_message_pump: ContextVar["MessagePump"] = ContextVar("active_message_pump")

prevent_message_types_stack: ContextVar[list[set[type[Message]]]] = ContextVar(
    "prevent_message_types_stack"
)
message_hook: ContextVar[Callable[[Message], None]] = ContextVar("message_hook")
"""A callable that accepts a message. Used by App.run_test."""
