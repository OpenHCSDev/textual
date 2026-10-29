"""TextArea editing capabilities. Engines own edits; the widget owns presentation."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding, MethodBinding
from textual.cursor_shape import CellCursor, CursorShape, SteadyBlock
from textual.document._document import EditResult, Selection

if TYPE_CHECKING:
    from textual.document._edit import Edit
    from textual.events import Key
    from textual.widgets import TextArea


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

    def command_bindings(self) -> tuple[Binding, ...]:
        return ()

    @property
    def binding_mode(self) -> type[EditingMode]:
        return EditingMode

    def settled(self) -> EditingMode:
        return self

    def pasted(self) -> EditingMode:
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

    async def flush(self, editor: TextArea) -> None:
        """Finish admitted input before submission, transfer or retirement."""

    async def prepare_input(self, editor: TextArea) -> None:
        """Asynchronous engines may fence earlier widget input before binding lookup."""

    def selection_changed(self, editor: TextArea, selection: Selection) -> None:
        pass

    def selection_range(self, editor: TextArea) -> Selection:
        return editor.selection

    def load_text(self, editor: TextArea, text: str) -> None:
        editor._load_text(text)

    def edit(self, editor: TextArea, edit: Edit) -> EditResult | None:
        return editor._edit(edit)

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
