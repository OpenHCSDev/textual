"""The local clipboard payload, including editing semantics lost by plain text."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClipboardContent:
    text: str

    @classmethod
    def of(cls, value: str | ClipboardContent) -> ClipboardContent:
        return value if isinstance(value, ClipboardContent) else cls(value)

    def insertion(self, editor, before, count):
        return editor.navigator.get_location_column_offset(editor.cursor_location, 0 if before else 1), self.text * count

    def paste(self, editor, before, count):
        location, text = self.insertion(editor, before, count)
        editor.history.end_group()
        editor.replace(text, location, location, maintain_selection_offset=False)
        editor.move_cursor(location)


class LinewiseClipboard(ClipboardContent):
    def insertion(self, editor, before, count):
        row = editor.cursor_location[0] + (0 if before else 1)
        text = self.text * count
        if row < editor.document.line_count:
            return (row, 0), text
        return editor.document.end, editor.document.newline + text.removesuffix(editor.document.newline)
