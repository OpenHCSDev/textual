from __future__ import annotations

import unicodedata
import inspect
import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable, ClassVar, Generic, Iterator, Mapping, TypeVar
from enum import Enum
from dataclasses import dataclass
from functools import lru_cache

if TYPE_CHECKING:
    from textual.binding import Binding
    from textual.document._editing import EditingMode
    from textual.dom import DOMNode
    from textual.events import Key

NodeT = TypeVar("NodeT", bound="DOMNode", contravariant=True)


class KeyInvocation(ABC):
    """The concrete command a binding invokes, independent of its active mode."""

    @staticmethod
    def qualified(declaration: type | Callable[..., object]) -> str:
        return f"{declaration.__module__}.{declaration.__qualname__}"

    @abstractmethod
    def key_identity(self) -> str: ...

    @abstractmethod
    def key_title(self) -> str: ...

    @abstractmethod
    def key_summary(self) -> str: ...

    @abstractmethod
    def key_system(self) -> bool: ...

    def binding_identity(self, mode: type[EditingMode]) -> str:
        return self.in_mode(self.key_identity(), mode)

    @staticmethod
    def in_mode(identity: str, mode: type) -> str:
        return f"{identity}:{KeyInvocation.qualified(mode)}"

    def visible_for_focus(self, mode: type[EditingMode], focused: frozenset[str]) -> bool:
        """Local commands follow the enabled invocation IDs of the previous focus."""
        return self.binding_identity(mode) in focused

    def permits_invocation_overlap(self, other: KeyInvocation) -> bool:
        return False

    def overlaps_declaration(self, other: type[KeyDeclaration]) -> bool:
        return False


class KeyTitle:
    """Human text derived from the declaration rather than a second title roster."""

    def __get__(self, instance: object, owner: type[KeyDeclaration]) -> str:
        return owner.default_title()


class KeyDeclaration(KeyInvocation, Generic[NodeT]):
    """Shared metadata for application actions and native editor commands.

    Each provider retains its existing family registry. This view discovers the
    provider declarations through inheritance; no menu supplies their names.
    """

    title = KeyTitle()
    system: ClassVar[bool] = False
    _declared: ClassVar[list[type[KeyDeclaration]]] = []

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if "keys" in cls.__dict__:
            KeyDeclaration._declared.append(cls)

    @classmethod
    def default_title(cls) -> str:
        return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", cls.__name__).capitalize()

    @classmethod
    def identity(cls) -> str:
        return cls.qualified(cls)

    @classmethod
    def binding_id(cls, mode: type) -> str:
        return cls.binding_id_for(cls, mode)

    @staticmethod
    def binding_id_for(declaration: type | Callable[..., object], mode: type) -> str:
        """Class and native callable declarations use the same mode-qualified identity."""
        return KeyInvocation.in_mode(KeyInvocation.qualified(declaration), mode)

    def key_identity(self) -> str:
        return type(self).identity()

    def key_title(self) -> str:
        return self.title

    def key_summary(self) -> str:
        return self.summary()

    def key_system(self) -> bool:
        return self.system

    def permits_invocation_overlap(self, other: KeyInvocation) -> bool:
        return other.overlaps_declaration(type(self))

    def overlaps_declaration(self, other: type[KeyDeclaration]) -> bool:
        return type(self).permits_key_overlap(other)

    @abstractmethod
    def __call__(self, node: NodeT) -> object: ...

    @classmethod
    @abstractmethod
    def bindings_for(cls, mode: type[EditingMode]) -> tuple[Binding, ...]:
        """The declaration's defaults in one active editing mode."""
        raise NotImplementedError

    @classmethod
    def summary(cls) -> str:
        return inspect.cleandoc(cls.__doc__ or "")

    @classmethod
    def permits_key_overlap(cls, other: type[KeyDeclaration]) -> bool:
        """An explicitly declared alternative may share a key with another declaration."""
        return False

    @classmethod
    def declarations(cls) -> Iterator[type[KeyDeclaration]]:
        """Project each key family from the declaration owner's registry."""
        return (member for member in KeyDeclaration._declared
                if issubclass(member, cls))


# Adapted from prompt toolkit https://github.com/prompt-toolkit/python-prompt-toolkit/blob/master/prompt_toolkit/keys.py
class Keys(str, Enum):  # type: ignore[no-redef]
    """
    List of keys for use in key bindings.

    Note that this is an "StrEnum", all values can be compared against
    strings.
    """

    @property
    def value(self) -> str:
        return super().value

    Escape = "escape"  # Also Control-[
    ShiftEscape = "shift+escape"
    Return = "return"

    ControlAt = "ctrl+@"  # Also Control-Space.

    ControlA = "ctrl+a"
    ControlB = "ctrl+b"
    ControlC = "ctrl+c"
    ControlD = "ctrl+d"
    ControlE = "ctrl+e"
    ControlF = "ctrl+f"
    ControlG = "ctrl+g"
    ControlH = "ctrl+h"
    ControlI = "ctrl+i"  # Tab
    ControlJ = "ctrl+j"  # Newline
    ControlK = "ctrl+k"
    ControlL = "ctrl+l"
    ControlM = "ctrl+m"  # Carriage return
    ControlN = "ctrl+n"
    ControlO = "ctrl+o"
    ControlP = "ctrl+p"
    ControlQ = "ctrl+q"
    ControlR = "ctrl+r"
    ControlS = "ctrl+s"
    ControlT = "ctrl+t"
    ControlU = "ctrl+u"
    ControlV = "ctrl+v"
    ControlW = "ctrl+w"
    ControlX = "ctrl+x"
    ControlY = "ctrl+y"
    ControlZ = "ctrl+z"

    Control1 = "ctrl+1"
    Control2 = "ctrl+2"
    Control3 = "ctrl+3"
    Control4 = "ctrl+4"
    Control5 = "ctrl+5"
    Control6 = "ctrl+6"
    Control7 = "ctrl+7"
    Control8 = "ctrl+8"
    Control9 = "ctrl+9"
    Control0 = "ctrl+0"

    ControlShift1 = "ctrl+shift+1"
    ControlShift2 = "ctrl+shift+2"
    ControlShift3 = "ctrl+shift+3"
    ControlShift4 = "ctrl+shift+4"
    ControlShift5 = "ctrl+shift+5"
    ControlShift6 = "ctrl+shift+6"
    ControlShift7 = "ctrl+shift+7"
    ControlShift8 = "ctrl+shift+8"
    ControlShift9 = "ctrl+shift+9"
    ControlShift0 = "ctrl+shift+0"

    ControlBackslash = "ctrl+backslash"
    ControlSquareClose = "ctrl+right_square_bracket"
    ControlCircumflex = "ctrl+circumflex_accent"
    ControlUnderscore = "ctrl+underscore"

    Left = "left"
    Right = "right"
    Up = "up"
    Down = "down"
    Home = "home"
    End = "end"
    Insert = "insert"
    Delete = "delete"
    PageUp = "pageup"
    PageDown = "pagedown"

    ControlLeft = "ctrl+left"
    ControlRight = "ctrl+right"
    ControlUp = "ctrl+up"
    ControlDown = "ctrl+down"
    ControlHome = "ctrl+home"
    ControlEnd = "ctrl+end"
    ControlInsert = "ctrl+insert"
    ControlDelete = "ctrl+delete"
    ControlPageUp = "ctrl+pageup"
    ControlPageDown = "ctrl+pagedown"

    ShiftLeft = "shift+left"
    ShiftRight = "shift+right"
    ShiftUp = "shift+up"
    ShiftDown = "shift+down"
    ShiftHome = "shift+home"
    ShiftEnd = "shift+end"
    ShiftInsert = "shift+insert"
    ShiftDelete = "shift+delete"
    ShiftPageUp = "shift+pageup"
    ShiftPageDown = "shift+pagedown"

    ControlShiftLeft = "ctrl+shift+left"
    ControlShiftRight = "ctrl+shift+right"
    ControlShiftUp = "ctrl+shift+up"
    ControlShiftDown = "ctrl+shift+down"
    ControlShiftHome = "ctrl+shift+home"
    ControlShiftEnd = "ctrl+shift+end"
    ControlShiftInsert = "ctrl+shift+insert"
    ControlShiftDelete = "ctrl+shift+delete"
    ControlShiftPageUp = "ctrl+shift+pageup"
    ControlShiftPageDown = "ctrl+shift+pagedown"

    BackTab = "shift+tab"  # shift + tab

    F1 = "f1"
    F2 = "f2"
    F3 = "f3"
    F4 = "f4"
    F5 = "f5"
    F6 = "f6"
    F7 = "f7"
    F8 = "f8"
    F9 = "f9"
    F10 = "f10"
    F11 = "f11"
    F12 = "f12"
    F13 = "f13"
    F14 = "f14"
    F15 = "f15"
    F16 = "f16"
    F17 = "f17"
    F18 = "f18"
    F19 = "f19"
    F20 = "f20"
    F21 = "f21"
    F22 = "f22"
    F23 = "f23"
    F24 = "f24"

    ControlF1 = "ctrl+f1"
    ControlF2 = "ctrl+f2"
    ControlF3 = "ctrl+f3"
    ControlF4 = "ctrl+f4"
    ControlF5 = "ctrl+f5"
    ControlF6 = "ctrl+f6"
    ControlF7 = "ctrl+f7"
    ControlF8 = "ctrl+f8"
    ControlF9 = "ctrl+f9"
    ControlF10 = "ctrl+f10"
    ControlF11 = "ctrl+f11"
    ControlF12 = "ctrl+f12"
    ControlF13 = "ctrl+f13"
    ControlF14 = "ctrl+f14"
    ControlF15 = "ctrl+f15"
    ControlF16 = "ctrl+f16"
    ControlF17 = "ctrl+f17"
    ControlF18 = "ctrl+f18"
    ControlF19 = "ctrl+f19"
    ControlF20 = "ctrl+f20"
    ControlF21 = "ctrl+f21"
    ControlF22 = "ctrl+f22"
    ControlF23 = "ctrl+f23"
    ControlF24 = "ctrl+f24"

    # Matches any key.
    Any = "<any>"

    # Special.
    ScrollUp = "<scroll-up>"
    ScrollDown = "<scroll-down>"

    # For internal use: key which is ignored.
    # (The key binding for this key should not do anything.)
    Ignore = "<ignore>"

    # Some 'Key' aliases (for backwardshift+compatibility).
    ControlSpace = "ctrl-at"
    Tab = "tab"
    Space = "space"
    Enter = "enter"
    Backspace = "backspace"

    # ShiftControl was renamed to ControlShift in
    # 888fcb6fa4efea0de8333177e1bbc792f3ff3c24 (20 Feb 2020).
    ShiftControlLeft = ControlShiftLeft
    ShiftControlRight = ControlShiftRight
    ShiftControlHome = ControlShiftHome
    ShiftControlEnd = ControlShiftEnd


@dataclass(frozen=True)
class DeclaredKey:
    """A decoded native input identity, distinct from its configured spelling."""

    def decoded(self, key: str) -> DeclaredKey:
        return self

    def invocations(self, defaults: tuple[KeyInvocation, ...]) -> tuple[KeyInvocation, ...]:
        return defaults

    def preempts(self, binding: Binding, event: Key, keymap: Mapping[str, str]) -> bool:
        return False

    def input_bindings(self, spelling: str) -> tuple[tuple[str, str], ...]:
        """Native input aliases for an external editing engine."""
        return ()


class UndecodedKey(DeclaredKey):
    """Only Binding.make_bindings sees an external declaration's key spelling."""

    def decoded(self, key: str) -> DeclaredKey:
        return NavigationKey.from_key(key)


class NavigationKey(DeclaredKey, KeyInvocation):
    """One preference for an arrow, independent of the focused control's effect.

    Bindings keep their native callable, availability and order. Only the saved
    input identity is shared: configuring Up must not mean configuring TextArea,
    a table, a tree and every future arrow control separately.
    """

    key: ClassVar[Keys]
    _by_key: ClassVar[dict[str, type[NavigationKey]]] = {}

    def __init_subclass__(cls, *, key: Keys, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        cls.key = key
        cls._by_key[key.value] = cls

    @classmethod
    def from_key(cls, key: str) -> DeclaredKey:
        """Decode a declared native key once, before any preference changes it."""
        try:
            declaration = cls._by_key[key]
        except KeyError:
            return DeclaredKey()
        return declaration()

    def invocations(self, defaults: tuple[KeyInvocation, ...]) -> tuple[KeyInvocation, ...]:
        return (self,)

    def preempts(self, binding: Binding, event: Key, keymap: Mapping[str, str]) -> bool:
        """Explicit printable aliases precede a list's type-to-search behavior."""
        return event.is_printable and binding.id in keymap

    def key_identity(self) -> str:
        return self.qualified(type(self))

    def input_bindings(self, spelling: str) -> tuple[tuple[str, str], ...]:
        return ((spelling, self.key.value),)

    def key_title(self) -> str:
        return f"Cursor {self.key.value}"

    def key_summary(self) -> str:
        return f"Use these keys wherever the focused control handles {self.key.value}."

    def key_system(self) -> bool:
        return False

    def visible_for_focus(self, mode: type[EditingMode], focused: frozenset[str]) -> bool:
        """Global arrow preferences remain editable even from a non-arrow focus."""
        return True


class UpKey(NavigationKey, key=Keys.Up):
    pass


class DownKey(NavigationKey, key=Keys.Down):
    pass


class LeftKey(NavigationKey, key=Keys.Left):
    pass


class RightKey(NavigationKey, key=Keys.Right):
    pass


# Unicode db contains some obscure names
# This mapping replaces them with more common terms
KEY_NAME_REPLACEMENTS = {
    "solidus": "slash",
    "reverse_solidus": "backslash",
    "commercial_at": "at",
    "hyphen_minus": "minus",
    "plus_sign": "plus",
    "low_line": "underscore",
}
REPLACED_KEYS = {value: key for key, value in KEY_NAME_REPLACEMENTS.items()}

# Convert the friendly versions of character key Unicode names
# back to their original names.
# This is because we go from Unicode to friendly by replacing spaces and dashes
# with underscores, which cannot be undone by replacing underscores with spaces/dashes.
KEY_TO_UNICODE_NAME = {
    "exclamation_mark": "EXCLAMATION MARK",
    "quotation_mark": "QUOTATION MARK",
    "number_sign": "NUMBER SIGN",
    "dollar_sign": "DOLLAR SIGN",
    "percent_sign": "PERCENT SIGN",
    "left_parenthesis": "LEFT PARENTHESIS",
    "right_parenthesis": "RIGHT PARENTHESIS",
    "plus_sign": "PLUS SIGN",
    "hyphen_minus": "HYPHEN-MINUS",
    "full_stop": "FULL STOP",
    "less_than_sign": "LESS-THAN SIGN",
    "equals_sign": "EQUALS SIGN",
    "greater_than_sign": "GREATER-THAN SIGN",
    "question_mark": "QUESTION MARK",
    "commercial_at": "COMMERCIAL AT",
    "left_square_bracket": "LEFT SQUARE BRACKET",
    "reverse_solidus": "REVERSE SOLIDUS",
    "right_square_bracket": "RIGHT SQUARE BRACKET",
    "circumflex_accent": "CIRCUMFLEX ACCENT",
    "low_line": "LOW LINE",
    "grave_accent": "GRAVE ACCENT",
    "left_curly_bracket": "LEFT CURLY BRACKET",
    "vertical_line": "VERTICAL LINE",
    "right_curly_bracket": "RIGHT CURLY BRACKET",
}

# Some keys have aliases. For example, if you press `ctrl+m` on your keyboard,
# it's treated the same way as if you press `enter`. Key handlers `key_ctrl_m` and
# `key_enter` are both valid in this case.
KEY_ALIASES = {
    "tab": ["ctrl+i"],
    "enter": ["ctrl+m"],
    "escape": ["ctrl+left_square_brace"],
    "ctrl+at": ["ctrl+space"],
    "ctrl+j": ["newline"],
}

KEY_DISPLAY_ALIASES = {
    "up": "↑",
    "down": "↓",
    "left": "←",
    "right": "→",
    "backspace": "⌫",
    "escape": "esc",
    "enter": "⏎",
    "minus": "-",
    "space": "space",
    "pagedown": "pgdn",
    "pageup": "pgup",
    "delete": "del",
}


ASCII_KEY_NAMES = {"\t": "tab"}


def _get_unicode_name_from_key(key: str) -> str:
    """Get the best guess for the Unicode name of the char corresponding to the key.

    This function can be seen as a pseudo-inverse of the function `_character_to_key`.
    """
    return KEY_TO_UNICODE_NAME.get(key, key)


def _get_key_aliases(key: str) -> list[str]:
    """Return all aliases for the given key, including the key itself"""
    return [key] + KEY_ALIASES.get(key, [])


@lru_cache(1024)
def format_key(key: str) -> str:
    """Given a key (i.e. the `key` string argument to Binding __init__),
    return the value that should be displayed in the app when referring
    to this key (e.g. in the Footer widget)."""

    display_alias = KEY_DISPLAY_ALIASES.get(key)
    if display_alias:
        return display_alias

    original_key = REPLACED_KEYS.get(key, key)
    tentative_unicode_name = _get_unicode_name_from_key(original_key)
    try:
        unicode_name = unicodedata.lookup(tentative_unicode_name)
    except KeyError:
        pass
    else:
        if unicode_name.isprintable():
            return unicode_name
    return tentative_unicode_name


@lru_cache(1024)
def key_to_character(key: str) -> str | None:
    """Given a key identifier, return the character associated with it.

    Args:
        key: The key identifier.

    Returns:
        A key if one could be found, otherwise `None`.
    """
    _, separator, key = key.rpartition("+")
    if separator:
        # If there is a separator, then it means a modifier (other than shift) is applied.
        # Keys with modifiers, don't come from printable keys.
        return None
    if len(key) == 1:
        # Key identifiers with a length of one, are also characters.
        return key
    try:
        return unicodedata.lookup(KEY_TO_UNICODE_NAME[key])
    except KeyError:
        pass
    try:
        return unicodedata.lookup(key.replace("_", " ").upper())
    except KeyError:
        pass
    # Return None if we couldn't identify the key.
    return None


def _character_to_key(character: str) -> str:
    """Convert a single character to a key value.

    This transformation can be undone by the function `_get_unicode_name_from_key`.
    """
    if not character.isalnum():
        try:
            key = (
                unicodedata.name(character).lower().replace("-", "_").replace(" ", "_")
            )
        except ValueError:
            key = ASCII_KEY_NAMES.get(character, character)
    else:
        key = character
    key = KEY_NAME_REPLACEMENTS.get(key, key)
    return key


def _normalize_key_list(keys: str) -> str:
    """Normalizes a comma separated list of keys.

    Replaces single letter keys with full name.
    """

    keys_list = [key.strip() for key in keys.split(",")]
    return ",".join(
        _character_to_key(key) if len(key) == 1 else key for key in keys_list
    )
