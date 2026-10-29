"""One transient native hint interaction over published activation targets."""
from __future__ import annotations

from enum import IntEnum
from typing import ClassVar

from textual import events
from textual.binding import ModeBinding
from textual.document._editing import VimMode
from textual.content import Content
from textual.css.scalar import Scalar
from textual.geometry import Offset
from textual.widget import Widget


class HintClick(IntEnum):
    """The two pointer intents offered by native hint sessions."""

    LEFT = 1
    RIGHT = 3

    @property
    def description(self) -> str:
        return f"{self.name.title()}-click hints"

    @property
    def caption(self) -> str:
        return f"{self.description} · Escape cancels"


class HintHost:
    """Screen capability; mounted children are the only session inventory."""

    async def action_show_hints(self) -> None:
        await self._show_hints(HintClick.LEFT)

    async def action_show_context_hints(self) -> None:
        await self._show_hints(HintClick.RIGHT)

    async def _show_hints(self, click: HintClick) -> None:
        self.dismiss_hints()
        targets = self._compositor.activation_targets(click)
        if not targets:
            return
        session = HintSession(self, targets, click)
        await self.mount(*session.labels, session)
        session.focus_on_host()

    MODE_BINDINGS: ClassVar[tuple[ModeBinding, ...]] = (
        ModeBinding("f", action_show_hints, HintClick.LEFT.description,
                    mode=VimMode, show=False),
        ModeBinding("ctrl+f", action_show_context_hints, HintClick.RIGHT.description,
                    mode=VimMode, show=False),
    )

    def dismiss_hints(self, *, restore=True) -> None:
        for session in self.query_children(HintSession):
            session.dismiss(restore=restore)

    def _on_frame_published(self) -> None:
        for session in self.query_children(HintSession):
            session.reconcile_publication()


class HintLabel(Widget):
    """One target's key; the typed span is read from the session that owns the prefix."""

    DEFAULT_CSS = """
    HintLabel {
        text-style: bold reverse;
    }
    HintLabel > .hint-label--typed {
        text-style: bold not reverse;
    }
    """
    COMPONENT_CLASSES: ClassVar[set[str]] = {"hint-label--typed"}
    hit_test_transparent = True
    ALLOW_SELECT = False

    def __init__(self, session, text, target, offset):
        super().__init__()
        self.session = session
        self.text = text
        self.target = target
        self.styles.position = "absolute"
        self.styles.overlay = "screen"
        self.styles.layer = "_tooltips"
        self.styles.width = len(text)
        self.styles.height = 1
        self.absolute_offset = offset

    def render(self) -> Content:
        typed = self.get_visual_style("hint-label--typed")
        return Content(self.text).stylize(typed, 0, len(self.session.prefix))


class HintSession(Widget, can_focus=True):
    """Own label input and its short-lived paint; never copy navigation state."""

    DEFAULT_CSS = """
    HintSession {
        text-style: bold reverse;
    }
    """
    alphabet = "asdfghjklqwertyuiopzxcvbnm"
    ALLOW_SELECT = False
    hit_test_transparent = True

    def __init__(self, screen, targets, click: HintClick):
        super().__init__()
        self.click = click
        self.original_focus: Widget | None = screen.focused
        targets = sorted(targets, key=lambda target: (target.region.y, target.region.x))
        self.prefix = ""
        width = 1
        while len(self.alphabet) ** width < len(targets):
            width += 1
        labels = []
        for index, target in enumerate(targets):
            text = self.label(index, width)
            labels.append(HintLabel(self, text, target, target.region.offset))
        self.labels = tuple(labels)
        self.styles.position = "absolute"
        self.styles.overlay = "screen"
        self.styles.layer = "_tooltips"
        self.styles.height = 1

    @property
    def _current_original_focus(self) -> Widget | None:
        original = self.original_focus
        if (
            original is not None
            and original.is_attached
            and original.screen is self.screen
            and self.screen is self.app.screen
        ):
            return original
        return None

    @property
    def key_mode_label(self) -> str:
        """Taking hint focus does not replace the originating editor's mode."""
        original = self._current_original_focus
        return original.key_mode_label if original is not None else super().key_mode_label

    @property
    def caption(self) -> Content:
        """One complete caption supplies paint, width and reserved cells."""
        mode_label = self.key_mode_label
        return Content(
            f"{mode_label} · {self.click.caption}" if mode_label else self.click.caption
        )

    def render(self) -> Content:
        return self.caption

    def on_mount(self) -> None:
        self.screen.bindings_updated_signal.subscribe(self, self._bindings_changed)
        self._bindings_changed(self.screen)

    def on_unmount(self) -> None:
        self.screen.bindings_updated_signal.unsubscribe(self)

    def _bindings_changed(self, _screen: Widget) -> None:
        if self.disabled:
            return
        self._reconcile_caption_geometry()
        self.refresh()

    def _reconcile_caption_geometry(self) -> None:
        size = self.screen.size
        width = min(size.width, self.caption.cell_length)
        desired_width = Scalar.from_number(width)
        offset = Offset(0, size.height - 1)
        if self.styles.width == desired_width and self.absolute_offset == offset:
            return
        self.styles.width = desired_width
        self.absolute_offset = offset
        placed: dict[int, list[tuple[int, int]]] = {offset.y: [(0, width)]}
        for label in self.labels:
            label.absolute_offset = self.free_offset(
                placed, size, label.target.region.offset, len(label.text)
            )

    @staticmethod
    def free_offset(placed, size, origin, width):
        """Nearest cell to origin where a label keeps one blank cell beside every placed label.

        Labels are placed in target order; placed maps each row to the spans already taken
        on it and is extended here. A full screen leaves the label on its target.
        """
        for distance in range(size.width + size.height):
            for dy in sorted(range(-distance, distance + 1), key=abs):
                y = origin.y + dy
                if not 0 <= y < size.height:
                    continue
                dx = distance - abs(dy)
                for x in dict.fromkeys((origin.x + dx, origin.x - dx)):
                    if 0 <= x <= size.width - width and all(
                        x > end or x + width < start for start, end in placed.get(y, ())
                    ):
                        placed.setdefault(y, []).append((x, x + width))
                        return Offset(x, y)
        return origin

    @classmethod
    def label(cls, index, width):
        characters = []
        for _ in range(width):
            index, digit = divmod(index, len(cls.alphabet))
            characters.append(cls.alphabet[digit])
        return "".join(reversed(characters))

    def focus_on_host(self):
        if self.is_attached and self.screen is self.app.screen:
            self.screen.set_focus(self, scroll_visible=False)

    def check_consume_key(self, key, character=None):
        return key == "escape" or (character is not None and character.isprintable())

    def on_key(self, event: events.Key):
        if self.disabled:
            return
        if event.key == "escape":
            event.stop()
            event.prevent_default()
            self.dismiss()
        elif event.is_printable:
            event.stop()
            event.prevent_default()
            self.prefix += event.character
            remaining = [label for label in self.labels
                         if label.display and label.text.startswith(self.prefix)]
            if not remaining:
                self.dismiss()
            elif len(remaining) == 1 and remaining[0].text == self.prefix:
                self.dismiss(target=remaining[0].target)
            else:
                for label in self.labels:
                    label.display = label in remaining
                for label in remaining:
                    label.refresh()

    def on_paste(self, event: events.Paste):
        original = self.original_focus
        self.dismiss()
        event.stop()
        if original is not None and original.is_attached:
            original.post_message(event)

    def restore_focus(self):
        if self.screen is not self.app.screen:
            return
        original = self.original_focus
        if original is None or self._current_original_focus is not None:
            self.screen.set_focus(original, scroll_visible=False)

    def dismiss(self, *, target=None, restore=True):
        if self.disabled:
            return
        self.disabled = True
        if restore:
            self.restore_focus()
        screen = self.screen
        screen.run_worker(self._retire(screen, target), group="hint-retirement")

    async def _retire(self, screen, target):
        await screen.remove_children(self.labels)
        await self.remove()
        if target is not None:
            await target.activate()

    def on_blur(self):
        self.dismiss(restore=False)

    def reconcile_publication(self):
        if self.disabled:
            return
        if self.original_focus is not None and self._current_original_focus is None:
            self.original_focus = None
            self.refresh_bindings()
            self.refresh()
        self._reconcile_caption_geometry()
        for label in self.labels:
            if label.display and not label.target.available():
                label.display = False
        if not any(label.display for label in self.labels):
            self.dismiss()
