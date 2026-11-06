from __future__ import annotations

import asyncio

from textual import events
from textual.driver import Driver, TerminalColours, TerminalGaveNoPalette
from textual.geometry import Size


class HeadlessDriver(Driver):
    """A do-nothing driver for testing."""

    @property
    def is_headless(self) -> bool:
        """Is the driver running in 'headless' mode?"""
        return True

    def _get_terminal_size(self) -> tuple[int, int]:
        if self._size is not None:
            return self._size
        width: int | None = 80
        height: int | None = 25
        import shutil

        try:
            width, height = shutil.get_terminal_size()
        except (AttributeError, ValueError, OSError):
            try:
                width, height = shutil.get_terminal_size()
            except (AttributeError, ValueError, OSError):
                pass
        width = width or 80
        height = height or 25
        return width, height

    def write(self, data: str) -> None:
        """Write data to the output device.

        Args:
            data: Raw data.
        """
        # Nothing to write as this is a headless driver.

    async def query_colours(self, *, timeout: float) -> TerminalColours:
        """There is no terminal to ask: the query goes nowhere, so no reply can come.

        The inherited query waited out its whole deadline for answers to writes that went
        nowhere, so every headless app that asked (each of Toad's app tests, at startup)
        sat idle for the full timeout before getting this same answer.
        """
        raise TerminalGaveNoPalette("a headless driver has no terminal to ask for a palette")

    def start_application_mode(self) -> None:
        """Start application mode."""
        loop = asyncio.get_running_loop()

        def send_size_event() -> None:
            """Send first resize event."""
            terminal_size = self._get_terminal_size()
            width, height = terminal_size
            textual_size = Size(width, height)
            event = events.Resize(textual_size, textual_size)
            asyncio.run_coroutine_threadsafe(
                self._app._post_message(event),
                loop=loop,
            )

        send_size_event()

    def disable_input(self) -> None:
        """Disable further input."""

    def stop_application_mode(self) -> None:
        """Stop application mode, restore state."""
        # Nothing to do
