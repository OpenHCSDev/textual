"""Native editor modes and commands, sharing TextArea's document and history.

Commands declare native bindings; modes own how their behavior participates
in an unfinished operation. Dispatch uses the application's remapped table.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding, ModeBinding
from textual.document._document import Location, Selection
from textual._clipboard import ClipboardContent, LinewiseClipboard
from textual.keys import KeyDeclaration
from textual.cursor_shape import BlinkingBar, CellCursor, CursorShape, SteadyBlock
from textual.document._document_navigator import WordBoundary, PreviousWordBoundary, EndWordBoundary

if TYPE_CHECKING:
    from textual.events import Key
    from textual.widgets import TextArea


class EditingMode:
    """Ordinary text entry; subclasses declare additional editing behavior."""

    modal = False
    accepts_text = True
    cursor_shape: ClassVar[CursorShape] = CellCursor()

    @property
    def label(self) -> str:
        return ""

    @property
    def allows_application_commands(self) -> bool:
        """Whether idle modal command entry permits application priority bindings."""
        return False

    @classmethod
    def fallback_bindings(cls, binding: Binding) -> tuple[Binding, ...]:
        """Ordinary editor keys do not escape their focused owner."""
        return ()

    def handle_key(self, editor: TextArea, event: Key) -> bool:
        return False

    def command_bindings(self) -> tuple[Binding, ...]:
        return ()

    @classmethod
    def editor_bindings(cls, command: type[EditorCommand]) -> tuple[Binding, ...]:
        """Ordinary entry has no modal editor commands."""
        return ()

    @property
    def binding_mode(self) -> type[EditingMode]:
        """The stable mode identity, independent of an application's profile subclass."""
        return EditingMode

    def apply_command(self, editor: TextArea, command: type[EditorCommand]) -> bool:
        return False

    def settled(self) -> EditingMode:
        return self

    def pasted(self) -> EditingMode:
        return self

    def document_changed(self) -> EditingMode:
        return self.settled()

    def resume(self, editor: TextArea) -> None:
        editor.history.checkpoint()

    def suspend(self, editor: TextArea) -> None:
        editor.history.end_group()

    def selection_range(self, editor: TextArea) -> Selection:
        return editor.selection


class VimMode(EditingMode, ABC):
    modal = True
    cursor_shape = SteadyBlock()

    @classmethod
    def fallback_bindings(cls, binding: Binding) -> tuple[Binding, ...]:
        """Modal navigation also belongs to its screen's selected resource."""
        return (binding,)

    def handle_key(self, editor: TextArea, event: Key) -> bool:
        editor.history.checkpoint()
        try:
            return self._handle_key(editor, event)
        finally:
            editor.history.checkpoint()

    @abstractmethod
    def _handle_key(self, editor: TextArea, event: Key) -> bool:
        raise NotImplementedError

    def pasted(self) -> EditingMode:
        return VimInsert()


class VimInsert(VimMode):
    label = "INSERT"
    cursor_shape = BlinkingBar()

    @property
    def binding_mode(self) -> type[VimInsert]:
        return VimInsert

    def resume(self, editor: TextArea) -> None:
        editor.history.begin_group()

    def _handle_key(self, editor: TextArea, event: Key) -> bool:
        if event.key != "escape":
            return False
        editor.editing_mode = VimNormal()
        return True


@dataclass(frozen=True)
class VimNormal(VimMode):
    count: int = 0
    accepts_text = False
    label = "NORMAL"

    @property
    def allows_application_commands(self) -> bool:
        """An idle command mode can yield to application-level priority bindings."""
        return self.count == 0

    def settled(self) -> EditingMode:
        return replace(self, count=0)

    @property
    def binding_mode(self) -> type[VimNormal]:
        return VimNormal

    def command_bindings(self) -> tuple[Binding, ...]:
        return tuple(binding for command in EditorCommand.declarations()
                     for binding in command.bindings_for(self.binding_mode))

    @classmethod
    def editor_bindings(cls, command: type[EditorCommand]) -> tuple[Binding, ...]:
        return command.native_bindings(cls)

    def _handle_key(self, editor: TextArea, event: Key) -> bool:
        if event.key.isdecimal() and (self.count or event.key != "0"):
            editor.editing_mode = replace(self, count=self.count * 10 + int(event.key))
            return True
        if editor.edit_key(event.key):
            return True
        # Unknown normal-mode text must never reach TextArea's insertion path.
        if event.is_printable or event.key == "enter":
            editor.editing_mode = self.settled()
            return True
        editor.editing_mode = self.settled()
        return False

    def apply_command(self, editor: TextArea, command: type[EditorCommand]) -> bool:
        editor.editing_mode = self.settled()
        command.apply(editor, self, self.count or 1)
        return True

    def move_to(self, editor: TextArea, location: Location) -> None:
        editor.move_cursor(location)

    def motion(self, editor: TextArea, motion: type[Motion], count: int) -> None:
        self.move_to(editor, motion.destination(editor, editor.cursor_location, count))

    def character_range(self, editor: TextArea, count: int) -> EditorRange:
        return EditorRange(editor.cursor_location,
                           Right.destination(editor, editor.cursor_location, count))

    def characters(self, editor: TextArea, operator: type[Operator], count: int) -> None:
        operator.replace(editor, self.character_range(editor, count))

    def visual(self, editor: TextArea) -> None:
        editor.editing_mode = VimVisual()

    def operate(self, editor: TextArea, operator: type[Operator], count: int) -> None:
        editor.editing_mode = VimOperator(operator=operator, operator_count=count)

    def escape(self, editor: TextArea) -> None:
        editor.leave_modal_editor()


@dataclass(frozen=True)
class VimVisual(VimNormal):
    label = "VISUAL"

    @property
    def binding_mode(self) -> type[VimVisual]:
        return VimVisual

    @property
    def allows_application_commands(self) -> bool:
        return False

    def document_changed(self) -> EditingMode:
        return VimNormal()

    def move_to(self, editor: TextArea, location: Location) -> None:
        editor.move_cursor(location, select=True)

    def character_range(self, editor: TextArea, count: int) -> EditorRange:
        return EditorRange(*self.selection_range(editor))

    def visual(self, editor: TextArea) -> None:
        self.escape(editor)

    def selection_range(self, editor: TextArea) -> Selection:
        start, end = sorted(editor.selection)
        return Selection(start, editor.navigator.get_location_right(end))

    def operate(self, editor: TextArea, operator: type[Operator], count: int) -> None:
        self.characters(editor, operator, count)

    def escape(self, editor: TextArea) -> None:
        editor.move_cursor(editor.cursor_location)
        editor.editing_mode = VimNormal()


@dataclass(frozen=True, kw_only=True)
class VimOperator(VimNormal):
    operator: type[Operator]
    operator_count: int = 1

    @property
    def allows_application_commands(self) -> bool:
        return False

    def settled(self) -> EditingMode:
        return VimNormal()

    def apply_command(self, editor: TextArea, command: type[EditorCommand]) -> bool:
        editor.editing_mode = VimNormal()
        command.pending(editor, self, self.operator_count * (self.count or 1))
        return True

    def escape(self, editor: TextArea) -> None:
        editor.editing_mode = VimNormal()


@dataclass(frozen=True)
class AwaitKey(VimMode):
    command: type[CharacterCommand]
    previous: VimNormal
    count: int
    accepts_text = False

    @property
    def label(self) -> str:
        return self.previous.label

    @property
    def binding_mode(self) -> type[EditingMode]:
        return self.previous.binding_mode

    def settled(self) -> EditingMode:
        return self.previous.settled()

    def document_changed(self) -> EditingMode:
        return self.previous.document_changed()

    def selection_range(self, editor: TextArea) -> Selection:
        return self.previous.selection_range(editor)

    def _handle_key(self, editor: TextArea, event: Key) -> bool:
        editor.editing_mode = self.settled()
        if event.key == "escape":
            return True
        if not event.is_printable:
            return False
        self.command.character(editor, self.previous, event.character, self.count)
        return True


class EditorBinding(ModeBinding):
    """The native synchronous command participates before text insertion."""

    def edit(self, editor: TextArea) -> bool:
        if not self.state(editor.app, editor):
            return False
        self.action(editor)
        return True


class EditorCommand(KeyDeclaration):
    keys: ClassVar[tuple[str, ...]] = ()
    _declared: ClassVar[list[type[EditorCommand]]] = []

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        # An explicit key declaration includes an intentionally unbound command.
        # Abstract intermediates inherit the empty root and declare no key set.
        if "keys" in cls.__dict__:
            EditorCommand._declared.append(cls)

    @classmethod
    def declarations(cls):
        return (member for member in EditorCommand._declared if issubclass(member, cls))

    @classmethod
    def bindings_for(cls, mode: type[EditingMode]) -> tuple[Binding, ...]:
        return mode.editor_bindings(cls)

    @classmethod
    def native_bindings(cls, mode: type[EditingMode]) -> tuple[Binding, ...]:
        return tuple(EditorBinding(key, cls.invoke, cls.title, mode=mode,
                                   id=cls.binding_id(mode), tooltip=cls.summary(), show=False,
                                   available=cls.available)
                     for key in cls.keys)

    @staticmethod
    def available(editor: TextArea) -> bool:
        return not editor.read_only

    @classmethod
    def invoke(cls, editor: TextArea) -> None:
        editor.editing_mode.apply_command(editor, cls)

    @classmethod
    def apply(cls, editor: TextArea, mode: VimNormal, count: int) -> None:
        raise NotImplementedError

    @classmethod
    def pending(cls, editor: TextArea, mode: VimOperator, count: int) -> None:
        """An unrelated command cancels the unfinished operator without editing."""


class Motion(EditorCommand):
    inclusive = False

    @classmethod
    def destination(cls, editor: TextArea, origin: Location, count: int) -> Location:
        raise NotImplementedError

    @classmethod
    def apply(cls, editor: TextArea, mode: VimNormal, count: int) -> None:
        mode.motion(editor, cls, count)

    @classmethod
    def pending(cls, editor: TextArea, mode: VimOperator, count: int) -> None:
        start = editor.cursor_location
        end = cls.destination(editor, start, count)
        start, end = sorted((start, end))
        if cls.inclusive:
            end = editor.navigator.get_location_right(end)
        mode.operator.replace(editor, EditorRange(start, end))


class Left(Motion):
    keys = ("h",)

    @classmethod
    def destination(cls, editor, origin, count):
        return editor.navigator.get_location_column_offset(origin, -count)


class Right(Motion):
    keys = ("l",)

    @classmethod
    def destination(cls, editor, origin, count):
        return editor.navigator.get_location_column_offset(origin, count)


class LineMotion(Motion):
    direction: ClassVar[int]

    @classmethod
    def destination(cls, editor, origin, count):
        return editor.navigator.get_location_line_offset(origin, cls.direction * count)

    @classmethod
    def pending(cls, editor, mode, count):
        top, bottom = sorted((editor.cursor_location[0], cls.destination(editor, editor.cursor_location, count)[0]))
        mode.operator.lines(editor, top, bottom - top + 1)


class Down(LineMotion):
    keys = ("j",)
    direction = 1


class Up(LineMotion):
    keys = ("k",)
    direction = -1


class LineStart(Motion):
    keys = ("0",)

    @classmethod
    def destination(cls, editor, origin, count):
        return origin[0], 0


class FirstNonblank(Motion):
    keys = ("circumflex",)

    @classmethod
    def destination(cls, editor, origin, count):
        return editor.navigator.get_location_first_nonblank(origin)


class LineEnd(Motion):
    keys = ("dollar",)

    @classmethod
    def destination(cls, editor, origin, count):
        return editor.navigator.get_location_document_line_end(origin, count)


class Word(Motion):
    keys = ("w",)
    boundary = WordBoundary()

    @classmethod
    def destination(cls, editor, origin, count):
        return editor.navigator.get_location_word_boundary(origin, count, cls.boundary)


class BackWord(Word):
    keys = ("b",)
    boundary = PreviousWordBoundary()


class EndWord(Word):
    keys = ("e",)
    boundary = EndWordBoundary()
    inclusive = True


class DocumentEnd(Motion):
    keys = ("G",)

    @classmethod
    def destination(cls, editor, origin, count):
        return editor.document.end


@dataclass(frozen=True)
class EditorRange:
    start: Location
    end: Location

    def text(self, editor: TextArea) -> str:
        return editor.document.get_text_range(self.start, self.end)

    def clipboard_content(self, editor: TextArea) -> ClipboardContent:
        return ClipboardContent(self.text(editor))

    def replace_characters(self, editor: TextArea, character: str) -> None:
        text = "".join(symbol if symbol in "\r\n" else character for symbol in self.text(editor))
        editor.replace(text, self.start, self.end, maintain_selection_offset=False)
        editor.move_cursor(self.start)

    def deletion_start(self, editor: TextArea) -> Location:
        return self.start

    def change_text(self, editor: TextArea) -> str:
        return ""


class LineRange(EditorRange):
    def clipboard_content(self, editor: TextArea) -> ClipboardContent:
        return LinewiseClipboard(self.text(editor))

    def change_text(self, editor: TextArea) -> str:
        return editor.document.newline

    def text(self, editor: TextArea) -> str:
        text = super().text(editor)
        return text if text.endswith(editor.document.newline) else text + editor.document.newline


class FinalLineRange(LineRange):
    def change_text(self, editor: TextArea) -> str:
        return ""

    def deletion_start(self, editor: TextArea) -> Location:
        if self.start[0]:
            row = self.start[0] - 1
            return row, len(editor.document[row])
        return self.start


class Operator(EditorCommand):
    @classmethod
    def apply(cls, editor, mode, count):
        mode.operate(editor, cls, count)

    @classmethod
    def pending(cls, editor, mode, count):
        if cls is mode.operator:
            cls.lines(editor, editor.cursor_location[0], count)

    @classmethod
    def lines(cls, editor, row, count):
        end_row = min(editor.document.line_count, row + count)
        if end_row < editor.document.line_count:
            selection = LineRange((row, 0), (end_row, 0))
        else:
            selection = FinalLineRange((row, 0), editor.document.end)
        cls.replace(editor, selection)

    @classmethod
    def replace(cls, editor, selection: EditorRange):
        raise NotImplementedError


class Yank(Operator):
    keys = ("y",)

    @classmethod
    def replace(cls, editor, selection: EditorRange):
        editor.app.copy_to_clipboard(selection.clipboard_content(editor))
        editor.move_cursor(selection.start)
        editor.editing_mode = VimNormal()


class Delete(Yank):
    keys = ("d",)
    following_mode: ClassVar[type[EditingMode]] = VimNormal

    @classmethod
    def deletion_start(cls, editor, selection):
        return selection.deletion_start(editor)

    @classmethod
    def inserted_text(cls, editor, selection):
        return ""

    @classmethod
    def replace(cls, editor, selection: EditorRange):
        super().replace(editor, selection)
        editor.editing_mode = cls.following_mode()
        editor.replace(cls.inserted_text(editor, selection), cls.deletion_start(editor, selection),
                       selection.end, maintain_selection_offset=False)


class Change(Delete):
    keys = ("c",)
    following_mode = VimInsert

    @classmethod
    def deletion_start(cls, editor, selection):
        return selection.start

    @classmethod
    def inserted_text(cls, editor, selection):
        return selection.change_text(editor)


class Insert(EditorCommand):
    keys = ("i",)

    @classmethod
    def apply(cls, editor, mode, count):
        editor.editing_mode = VimInsert()


class Append(Insert):
    keys = ("a",)

    @classmethod
    def apply(cls, editor, mode, count):
        editor.move_cursor(Right.destination(editor, editor.cursor_location, 1))
        super().apply(editor, mode, count)


class Visual(EditorCommand):
    keys = ("v",)

    @classmethod
    def apply(cls, editor, mode, count):
        mode.visual(editor)


class Escape(EditorCommand):
    keys = ("escape",)

    @classmethod
    def apply(cls, editor, mode, count):
        mode.escape(editor)


class DeleteCharacter(EditorCommand):
    keys = ("x",)

    @classmethod
    def apply(cls, editor, mode, count):
        mode.characters(editor, Delete, count)


class Undo(EditorCommand):
    keys = ("u",)

    @classmethod
    def apply(cls, editor, mode, count):
        for _ in range(min(count, len(editor.history.undo_stack))):
            editor.undo()


class Redo(Undo):
    keys = ("ctrl+r",)

    @classmethod
    def apply(cls, editor, mode, count):
        for _ in range(min(count, len(editor.history.redo_stack))):
            editor.redo()


class Paste(EditorCommand):
    keys = ("p",)
    before = False

    @classmethod
    def apply(cls, editor, mode, count):
        editor.paste_editor_text(before=cls.before, count=count)


class PasteBefore(Paste):
    keys = ("P",)
    before = True


class CharacterCommand(EditorCommand):
    @classmethod
    def apply(cls, editor, mode, count):
        editor.editing_mode = AwaitKey(cls, mode, count)

    @classmethod
    def character(cls, editor, mode, character, count):
        raise NotImplementedError


class GoToStart(CharacterCommand):
    keys = ("g",)

    @classmethod
    def character(cls, editor, mode, character, count):
        if character == "g":
            mode.move_to(editor, (min(count - 1, editor.document.line_count - 1), 0))


class FindCharacter(CharacterCommand):
    keys = ("f",)

    @classmethod
    def character(cls, editor, mode, character, count):
        if character is None:
            return
        origin = editor.cursor_location
        line = editor.document[origin[0]]
        column = origin[1]
        for _ in range(count):
            column = line.find(character, column + 1)
            if column < 0:
                return
        mode.move_to(editor, (origin[0], column))


class ReplaceCharacter(CharacterCommand):
    keys = ("r",)

    @classmethod
    def character(cls, editor, mode, character, count):
        if character is not None and character.isprintable():
            mode.character_range(editor, count).replace_characters(editor, character)
            editor.editing_mode = VimNormal()
