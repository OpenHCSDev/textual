"""The line-formatting inputs shared by intrinsic measurement and paint."""

from __future__ import annotations

from dataclasses import dataclass, field

from textual.css.types import TextAlign, TextOverflow, TextWrap


class TextFormat:
    """Native line policy; Styles supplies the same inputs from its descriptors."""

    __slots__ = ()

    @property
    def line_align(self) -> TextAlign:
        return "start"

    @property
    def line_wrap(self) -> TextWrap:
        return "wrap"

    @property
    def line_overflow(self) -> TextOverflow:
        return "fold"

    @property
    def line_pad(self) -> int:
        return 0

    def snapshot(self) -> TextFormatSnapshot:
        """Capture these actual inputs for a detached or worker render."""
        return TextFormatSnapshot(
            self.line_align, self.line_wrap, self.line_overflow, self.line_pad
        )


@dataclass(frozen=True, slots=True)
class TextFormatSnapshot(TextFormat):
    """An immutable, picklable acquisition of one publication's line policy."""

    line_align: TextAlign = field()
    line_wrap: TextWrap = field()
    line_overflow: TextOverflow = field()
    line_pad: int = field()
