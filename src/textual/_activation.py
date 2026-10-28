"""Activation targets borrow the widget's original effect and displayed cells."""
from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from itertools import islice
from typing import TYPE_CHECKING, Callable

from textual import events
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
    def from_paint(cls, widget: Widget, region: Region, strips: list[Strip], button=1):
        """Decode the selected click intent from exposed published cells."""
        for y, strip in zip(region.line_range, strips):
            x = region.x
            for segment in strip:
                width = segment.cell_length
                if width:
                    exposed = Region(x, y, width, 1)
                    meta = segment.style.meta if segment.style else {}
                    try:
                        handler = extract_handler_actions("click", meta)
                    except NoHandler:
                        # The nearest declaring ancestor owns this exposed cell.
                        yield from islice((target
                            for owner in widget.ancestors_with_self
                            for target in owner.activation_targets(exposed, meta, button)), 1)
                    else:
                        if handler.action is not None:
                            yield StyleTarget(widget, exposed, handler, button=button)
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
class CallbackTarget(Activation):
    callback: Callable
    arguments: tuple[object, ...] = field(default=(), kw_only=True)

    @property
    def identity(self):
        return self.widget, self.callback

    async def activate(self) -> None:
        if self.available():
            await invoke(self.callback, *self.arguments)


@dataclass(frozen=True)
class StyleTarget(Activation):
    handler: HandlerArguments
    button: int = field(default=1, kw_only=True)

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
            widget = self.widget
            screen = widget.screen
            published_region, _ = screen._compositor.published_widgets[widget]
            event = events.Click(
                widget,
                x=self.region.x - published_region.x,
                y=self.region.y - published_region.y,
                delta_x=0,
                delta_y=0,
                button=self.button,
                shift=False,
                meta=False,
                ctrl=False,
                screen_x=self.region.x,
                screen_y=self.region.y,
                style=screen.get_style_at(self.region.x, self.region.y),
            )
            await widget.app.dispatch_style_action(self.handler, event, widget)


class PrimaryActivation:
    """A widget declares its existing primary effect; discovery is shared."""

    def primary_activation_targets(self, region):
        return (CallbackTarget(self, region, self.primary_activation),)

    @property
    @abstractmethod
    def primary_activation(self) -> Callable: ...


class ContextActivation:
    """A widget declares its contextual effect at the published click offset."""

    def context_activation_targets(self, region):
        return (CallbackTarget(self, region, self.context_activation,
                               arguments=(region.offset,)),)

    @abstractmethod
    def context_activation(self, offset) -> None: ...


class FocusActivation(PrimaryActivation):
    """Text entry is reached by focus, never by submitting or editing its value."""

    @property
    def primary_activation(self) -> Callable:
        return self.focus
