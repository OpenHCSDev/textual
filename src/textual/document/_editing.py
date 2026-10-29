"""TextArea editing capabilities. Engines own edits; the widget owns presentation."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding, MethodBinding
from textual.cursor_shape import CellCursor, CursorShape, SteadyBlock
from textual.document._document import EditResult, Location, Selection

if TYPE_CHECKING:
    from textual.document._edit import Edit
    from textual.events import Key
    from textual.widgets import TextArea


class EditingFailure(RuntimeError):
    """The engine failed; preserve its displayed draft and never replay input."""


class EditingMode:
    """Native text entry, with overridable document and input ownership."""

    modal = False
    accepts_text = True
    cursor_shape: ClassVar[CursorShape] = CellCursor()
    label = ""

    @property
    def allows_application_commands(self) -> bool:
        return False

    @property
    def allows_history_navigation(self) -> bool:
        return self.accepts_text

    @classmethod
    def fallback_bindings(cls, binding: Binding) -> tuple[Binding, ...]:
        return ()

    async def handle_key(self, editor: TextArea, event: Key) -> bool:
        return editor.edit_key(event)

    def apply_native_binding(self, editor: TextArea, binding: MethodBinding, event: Key) -> bool:
        binding.call(editor)
        return True

    @property
    def binding_mode(self) -> type[EditingMode]:
        return EditingMode

    def enter_text(self, editor: TextArea) -> None:
        """An application may focus an existing editor in text-entry mode."""

    def settled(self) -> EditingMode:
        return self

    def document_changed(self) -> EditingMode:
        return self.settled()

    def attach(self, editor: TextArea) -> None:
        self.resume(editor)

    def resume(self, editor: TextArea) -> None:
        editor.history.checkpoint()

    def suspend(self, editor: TextArea) -> None:
        editor.history.end_group()

    def capture(self, editor: TextArea) -> EditingMode:
        return self.settled()

    async def unmount(self, editor: TextArea) -> None:
        await self.close()

    async def close(self) -> None:
        pass

    async def finish(self, editor: TextArea) -> None:
        await self.flush(editor)

    async def flush(self, editor: TextArea) -> None:
        """Finish admitted input before submission, transfer or retirement."""

    async def acknowledge(self, editor: TextArea) -> None:
        """Read actual engine state without waiting for a modal command to finish."""

    async def prepare_input(self, editor: TextArea) -> bool:
        """Asynchronous engines may fence earlier widget input before binding lookup."""
        return True

    def resize(self, editor: TextArea) -> None:
        pass

    def request_selection(self, editor: TextArea, selection: Selection) -> Selection:
        return selection

    def selection_range(self, editor: TextArea) -> Selection:
        return editor.selection

    def selection_for_line(self, editor: TextArea, row: int) -> Selection:
        return self.selection_range(editor)

    def selected_text(self, editor: TextArea) -> str:
        return editor.get_text_range(*self.selection_range(editor))

    def load_text(self, editor: TextArea, text: str) -> None:
        editor._load_text(text)

    def edit(self, editor: TextArea, edit: Edit) -> EditResult | None:
        return editor._edit(edit)

    def insert(self, editor: TextArea, text: str, location: Location | None, maintain_selection_offset: bool) -> EditResult | None:
        from textual.document._edit import Edit
        location = editor.cursor_location if location is None else location
        return self.edit(editor, Edit(text, location, location, maintain_selection_offset))

    def clear(self, editor: TextArea) -> EditResult | None:
        return editor.delete((0, 0), editor.document.end, maintain_selection_offset=False)

    def move_to_end(self, editor: TextArea) -> None:
        editor.move_cursor(editor.document.end)

    def undo(self, editor: TextArea) -> None:
        editor._undo()

    def redo(self, editor: TextArea) -> None:
        editor._redo()

    def paste(self, editor: TextArea, text: str) -> None:
        if result := editor._replace_via_keyboard(text, *editor.selection):
            editor.move_cursor(result.end_location)


class VimMode(EditingMode, ABC):
    """Modal binding capability, not a second implementation of Vim."""

    modal = True
    cursor_shape = SteadyBlock()

    @classmethod
    def fallback_bindings(cls, binding: Binding) -> tuple[Binding, ...]:
        return (binding,)

    @abstractmethod
    async def handle_key(self, editor: TextArea, event: Key) -> bool:
        raise NotImplementedError
