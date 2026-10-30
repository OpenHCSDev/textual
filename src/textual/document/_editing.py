"""TextArea editing capabilities. Engines own edits; the widget owns presentation."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from textual.binding import Binding, MethodBinding
from textual.cursor_shape import CellCursor, CursorShape, SteadyBlock
from textual.document._document import EditResult, Location, Selection
from textual.document._edit import Edit, InsertionPoint

if TYPE_CHECKING:
    from textual.events import Key
    from textual.keys import NavigationKey
    from textual.widgets import TextArea


class EditingFailure(RuntimeError):
    """The engine failed; preserve its displayed draft and never replay input."""


class EditingMode:
    """Native text entry, with overridable document and input ownership."""

    modal = False

    @classmethod
    def navigation_spellings(cls, key: type[NavigationKey]) -> tuple[str, ...]:
        return (key.key.value,)

    @property
    def accepts_text(self) -> bool:
        return True

    @property
    def cursor_shape(self) -> CursorShape:
        return CellCursor()

    @property
    def label(self) -> str:
        return ""

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

    async def finish(self, editor: TextArea) -> bool:
        return await self.flush(editor)

    async def flush(self, editor: TextArea) -> bool:
        """Acknowledge input, or explicitly refuse transfer while input is pending."""
        return True

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

    def insert(self, editor: TextArea, text: str, point: InsertionPoint, maintain_selection_offset: bool) -> EditResult | None:
        location = point.resolve(editor.cursor_location)
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


class NativeTextKeys:
    """A control whose printable keys are text, whatever its screen's keyboard profile."""

    @property
    def key_mode(self) -> type[EditingMode]:
        return EditingMode

    @property
    def allows_application_commands(self) -> bool:
        return self.key_mode().allows_application_commands


class VimMode(EditingMode, ABC):
    """Modal binding capability, not a second implementation of Vim."""

    modal = True

    @classmethod
    def navigation_spellings(cls, key: type[NavigationKey]) -> tuple[str, ...]:
        return (*super().navigation_spellings(key), key.modal)

    @property
    def cursor_shape(self) -> CursorShape:
        return SteadyBlock()

    @classmethod
    def fallback_bindings(cls, binding: Binding) -> tuple[Binding, ...]:
        return (binding,)

    @abstractmethod
    async def handle_key(self, editor: TextArea, event: Key) -> bool:
        raise NotImplementedError
