"""Operations that either preserve native ANSI or require a known RGB palette."""

from abc import ABC, abstractmethod
from collections.abc import Iterable

from rich.segment import Segment
from rich.style import Style as RichStyle
from rich.terminal_theme import TerminalTheme

from textual.color import Color
from textual.driver import TerminalGaveNoPalette
from textual.filter import ANSIToTruecolor, LineFilter
from textual.renderables.text_opacity import TextOpacity
from textual.renderables.tint import Tint
from textual.style import Style


class AnsiPalette(LineFilter, ABC):
    @abstractmethod
    def rich_style(self, style: RichStyle) -> Style: ...

    @abstractmethod
    def tint(
        self, segments: Iterable[Segment], colour: Color, background: Color
    ) -> Iterable[Segment]: ...

    @abstractmethod
    def opacity(
        self, segments: Iterable[Segment], amount: float, native: bool
    ) -> Iterable[Segment]: ...

    @abstractmethod
    def export_theme(self) -> TerminalTheme: ...


class NativeAnsiPalette(AnsiPalette):
    def apply(self, segments: list[Segment], background: Color) -> list[Segment]:
        return segments

    def rich_style(self, style: RichStyle) -> Style:
        return Style.from_rich_style(style)

    def tint(
        self, segments: Iterable[Segment], colour: Color, background: Color
    ) -> Iterable[Segment]:
        return segments

    def opacity(
        self, segments: Iterable[Segment], amount: float, native: bool
    ) -> Iterable[Segment]:
        return Segment.apply_style(
            segments, post_style=RichStyle(dim=amount < 0.5, conceal=amount == 0)
        )

    def export_theme(self) -> TerminalTheme:
        raise TerminalGaveNoPalette(
            "SVG export needs RGB colours; the terminal gave no palette"
        )


class MappedAnsiPalette(AnsiPalette, ANSIToTruecolor):
    def rich_style(self, style: RichStyle) -> Style:
        return Style.from_rich_style(style, self._terminal_theme)

    def tint(
        self, segments: Iterable[Segment], colour: Color, background: Color
    ) -> Iterable[Segment]:
        return Tint.process_segments(segments, colour, self._terminal_theme, background)

    def opacity(
        self, segments: Iterable[Segment], amount: float, native: bool
    ) -> Iterable[Segment]:
        return TextOpacity.process_segments(
            segments, amount, self._terminal_theme, native
        )

    def export_theme(self) -> TerminalTheme:
        return self._terminal_theme
