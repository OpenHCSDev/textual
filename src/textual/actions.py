from __future__ import annotations

import ast
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from typing_extensions import TypeAlias

ActionParseResult: TypeAlias = "tuple[str, str, tuple[object, ...]]"
"""An action is its name and the arbitrary tuple of its arguments."""


if TYPE_CHECKING:
    from textual.app import App
    from textual.dom import DOMNode


class StyleAction(ABC):
    """What a style's handler meta carries: an object that runs on the widget that drew it.

    A widget that owns the operation puts the operation itself in the meta; only the string
    form below goes back through the app's action names.
    """

    @abstractmethod
    async def run(self, app: App, namespace: DOMNode) -> None: ...


@dataclass(frozen=True)
class ParsedAction(StyleAction):
    """An action written as a name, as console markup and older widgets still write it."""

    parsed: ActionParseResult

    async def run(self, app: App, namespace: DOMNode) -> None:
        await app.run_action(self.parsed, namespace)


class SkipAction(Exception):
    """Raise in an action to skip the action (and allow any parent bindings to run)."""


class ActionError(Exception):
    pass


re_action_args = re.compile(r"([\w\.]+)\((.*)\)")


@lru_cache(maxsize=1024)
def parse(action: str) -> ActionParseResult:
    """Parses an action string.

    Args:
        action: String containing action.

    Raises:
        ActionError: If the action has invalid syntax.

    Returns:
        Action name and arguments.
    """
    args_match = re_action_args.match(action)
    if args_match is not None:
        action_name, action_args_str = args_match.groups()
        if action_args_str:
            try:
                # We wrap `action_args_str` to be able to disambiguate the cases where
                # the list of arguments is a comma-separated list of values from the
                # case where the argument is a single tuple.
                action_args: tuple[Any, ...] = ast.literal_eval(f"({action_args_str},)")
            except Exception:
                raise ActionError(
                    f"unable to parse {action_args_str!r} in action {action!r}"
                )
        else:
            action_args = ()
    else:
        action_name = action
        action_args = ()

    namespace, _, action_name = action_name.rpartition(".")

    return namespace, action_name, action_args
