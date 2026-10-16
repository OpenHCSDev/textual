"""One transient native hint interaction over published activation targets."""
from __future__ import annotations

from textual import events
from textual.geometry import Offset
from textual.widget import Widget
from textual.widgets._static import Static


class HintLabel(Static):
    hit_test_transparent = True
    ALLOW_SELECT = False

    def __init__(self, text, target):
        super().__init__(text, markup=False)
        self.styles.position = "absolute"
        self.styles.overlay = "screen"
        self.styles.layer = "_tooltips"
        self.styles.width = len(text)
        self.styles.height = 1
        self.styles.text_style = "bold reverse"
        column = min(target.region.x, max(0, target.widget.screen.size.width - len(text)))
        self.absolute_offset = Offset(column, target.region.y)


class HintSession(Widget, can_focus=True):
    """Own label input and its short-lived paint; never copy navigation state."""

    alphabet = "asdfghjklqwertyuiopzxcvbnm"
    ALLOW_SELECT = False
    hit_test_transparent = True

    def __init__(self, screen, targets):
        super().__init__()
        self.original_focus = screen.focused
        self.targets = tuple(sorted(targets, key=lambda target: (target.region.y, target.region.x)))
        self.prefix = ""
        width = 1
        while len(self.alphabet) ** width < len(self.targets):
            width += 1
        self.choices = tuple((self.label(index, width), target) for index, target in enumerate(self.targets))
        self.labels = tuple(HintLabel(label, target) for label, target in self.choices)
        self.styles.position = "absolute"
        self.styles.overlay = "screen"
        self.styles.width = 0
        self.styles.height = 0

    @classmethod
    def label(cls, index, width):
        characters = []
        for _ in range(width):
            index, digit = divmod(index, len(cls.alphabet))
            characters.append(cls.alphabet[digit])
        return "".join(reversed(characters))

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
            remaining = [(label, target) for label, target in self.choices if label.startswith(self.prefix)]
            if not remaining:
                self.dismiss()
            elif len(remaining) == 1 and remaining[0][0] == self.prefix:
                self.dismiss(target=remaining[0][1])
            else:
                for widget, (label, _target) in zip(self.labels, self.choices):
                    widget.display = label.startswith(self.prefix)

    def on_paste(self, event: events.Paste):
        original = self.original_focus
        self.dismiss()
        event.stop()
        if original is not None and original.is_attached:
            original.post_message(event)

    def dismiss(self, *, target=None, restore=True):
        if self.disabled:
            return
        self.disabled = True
        # Restore before a pointer's ordinary dispatch, never asynchronously
        # after that click has already chosen a different focus target.
        original = self.original_focus
        if restore and original is not None and original.is_attached and self.screen is self.app.screen:
            original.focus(scroll_visible=False)
        self.screen.run_worker(self._retire(target), group="hint-retirement")

    async def _retire(self, target):
        screen = self.screen
        if screen._hint_session is self:
            screen._hint_session = None
        await screen.remove_children(self.labels)
        await self.remove()
        if target is not None:
            await target.activate()

    def on_blur(self):
        self.dismiss(restore=False)

    def reconcile_publication(self):
        if self.disabled:
            return
        if any(not target.available() for target in self.targets):
            self.dismiss()
