"""One transient native hint interaction over published activation targets."""
from __future__ import annotations

from textual import events
from textual.geometry import Offset
from textual.widget import Widget
from textual.widgets._static import Static


class HintHost:
    """Screen capability; mounted children are the only session inventory."""

    async def action_show_hints(self) -> None:
        self.dismiss_hints()
        targets = self._compositor.activation_targets()
        if not targets:
            return
        session = HintSession(self, targets)
        await self.mount(*session.labels, session)
        session.focus_on_host()

    def dismiss_hints(self, *, restore=True) -> None:
        for session in self.query_children(HintSession):
            session.dismiss(restore=restore)

    def _on_frame_published(self) -> None:
        for session in self.query_children(HintSession):
            session.reconcile_publication()


class HintLabel(Static):
    hit_test_transparent = True
    ALLOW_SELECT = False

    def __init__(self, text, target):
        super().__init__(text, markup=False)
        self.target = target
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
        targets = sorted(targets, key=lambda target: (target.region.y, target.region.x))
        self.prefix = ""
        width = 1
        while len(self.alphabet) ** width < len(targets):
            width += 1
        self.labels = tuple(HintLabel(self.label(index, width), target)
                            for index, target in enumerate(targets))
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
                         if str(label.content).startswith(self.prefix)]
            if not remaining:
                self.dismiss()
            elif len(remaining) == 1 and remaining[0].content == self.prefix:
                self.dismiss(target=remaining[0].target)
            else:
                for label in self.labels:
                    label.display = str(label.content).startswith(self.prefix)

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
        if original is None or original.is_attached:
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
        if any(not label.target.available() for label in self.labels):
            self.dismiss()
