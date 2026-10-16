"""Activation targets borrow the widget's original effect and displayed cells."""
from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from textual._callback import invoke
from textual._event_broker import HandlerArguments, NoHandler, extract_handler_actions
from textual.geometry import Region
from textual.errors import NoWidget

if TYPE_CHECKING:
    from textual.strip import Strip
    from textual.widget import Widget


@dataclass(frozen=True)
class Activation:
    widget: Widget
    region: Region

    @classmethod
    def from_paint(cls, widget: Widget, region: Region, strips: list[Strip]):
        """Decode exposed click metadata and primary declarations once."""
        primary = next((owner for owner in widget.ancestors_with_self
                        if isinstance(owner, PrimaryActivation)), None)
        for y, strip in zip(region.line_range, strips):
            x = region.x
            for segment in strip:
                width = segment.cell_length
                if width:
                    exposed = Region(x, y, width, 1)
                    try:
                        handler = extract_handler_actions("click", segment.style.meta if segment.style else {})
                    except NoHandler:
                        if primary is not None:
                            yield PrimaryTarget(primary, exposed, primary.primary_activation)
                    else:
                        if handler.action is not None:
                            yield StyleTarget(widget, exposed, handler)
                x += width

    def available(self) -> bool:
        widget = self.widget
        if (
            not widget.is_attached
            or widget.is_disabled
            or not widget.visible
            or any(not node.display for node in widget.ancestors_with_self)
        ):
            return False
        screen = widget.screen
        if screen is not widget.app.screen:
            return False
        try:
            hit, _ = screen.get_widget_at(self.region.x, self.region.y)
        except NoWidget:
            return False
        return hit is widget or widget in hit.ancestors

    @property
    @abstractmethod
    def identity(self): ...

    @abstractmethod
    async def activate(self) -> None: ...


@dataclass(frozen=True)
class PrimaryTarget(Activation):
    callback: Callable

    @property
    def identity(self):
        return self.widget, self.callback

    async def activate(self) -> None:
        if self.available():
            await invoke(self.callback)


@dataclass(frozen=True)
class StyleTarget(Activation):
    handler: HandlerArguments

    @property
    def identity(self):
        return self.widget, self.handler.action

    def available(self) -> bool:
        if not super().available():
            return False
        style = self.widget.screen.get_style_at(self.region.x, self.region.y)
        try:
            current = extract_handler_actions("click", style.meta)
        except NoHandler:
            return False
        return current == self.handler

    async def activate(self) -> None:
        if self.available():
            await self.widget.app.dispatch_style_action(self.handler, None, self.widget)


class PrimaryActivation:
    """A widget declares its existing primary effect; discovery is shared."""

    @property
    @abstractmethod
    def primary_activation(self) -> Callable: ...
