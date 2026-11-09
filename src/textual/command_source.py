"""What a screen or app may list in its COMMANDS: the command palette's providers.

Its own module, below both `textual.screen` and `textual.command`: a screen names the
providers it offers and a provider names the screen it serves, so neither module could
type the other at runtime while the provider family lived beside the palette screen.
"""

from abc import ABC


class CommandSource(ABC):
    """A source of command palette commands; `textual.command.Provider` is its base member."""
