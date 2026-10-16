from __future__ import annotations

from typing import Any, NamedTuple
from textual import actions, log


class NoHandler(Exception):
    """Raised when handler isn't found in the meta."""


class HandlerArguments(NamedTuple):
    """Information for event handler."""

    modifiers: set[str]
    action: actions.ActionParseResult | None

    @classmethod
    def decode(cls, modifiers: set[str], value: Any) -> HandlerArguments:
        if isinstance(value, str):
            action = actions.parse(value)
        elif isinstance(value, tuple) and len(value) == 2:
            name, parameters = value
            namespace, parsed_name, _ = actions.parse(name)
            action = namespace, parsed_name, parameters
        else:
            action = None
        return cls(modifiers, action)

    async def run(self, app, default_namespace) -> bool:
        """Consumers use the action decoded once at the style boundary."""
        if self.action is None:
            if app.debug:
                log.warning("Can't parse action from style meta; check your console markup syntax")
            return False
        await app.run_action(self.action, default_namespace)
        return True


def extract_handler_actions(event_name: str, meta: dict[str, Any]) -> HandlerArguments:
    """Extract action from meta dict.

    Args:
        event_name: Event to check from.
        meta: Meta information (stored in Rich Style)

    Raises:
        NoHandler: If no handler is found.

    Returns:
        Action information.
    """
    event_path = event_name.split(".")
    for key, value in meta.items():
        if key.startswith("@"):
            name_args = key[1:].split(".")
            if name_args[: len(event_path)] == event_path:
                modifiers = name_args[len(event_path) :]
                return HandlerArguments.decode(set(modifiers), value)
    raise NoHandler(f"No handler for {event_name!r}")
