from __future__ import annotations

from typing import Any, NamedTuple
from textual import actions


class NoHandler(Exception):
    """Raised when handler isn't found in the meta."""


class HandlerArguments(NamedTuple):
    """Information for event handler."""

    modifiers: set[str]
    action: actions.StyleAction

    @classmethod
    def decode(cls, modifiers: set[str], value: Any) -> HandlerArguments:
        """The one boundary where a style's handler meta becomes an action."""
        if isinstance(value, actions.StyleAction):
            action: actions.StyleAction = value
        elif isinstance(value, str):
            action = actions.ParsedAction(actions.parse(value))
        elif isinstance(value, tuple) and len(value) == 2:
            name, parameters = value
            namespace, parsed_name, _ = actions.parse(name)
            action = actions.ParsedAction((namespace, parsed_name, parameters))
        else:
            action = actions.NoStyleAction()
        return cls(modifiers, action)

    async def run(self, app, default_namespace) -> bool:
        """Consumers use the action decoded once at the style boundary."""
        return await self.action.run(app, default_namespace)


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
