"""Click hints keep their keys on the original exposed target cells."""
from __future__ import annotations

from enum import IntEnum
from typing import ClassVar

from textual import events
from textual._activation import Activation
from textual._compositor import ActivationScene, FrameOverlay
from textual._on import on
from textual.binding import ModeBinding
from textual.content import Content
from textual.document._editing import VimMode
from textual.geometry import Region
from textual.widget import Widget


class HintClick(IntEnum):
    """The native pointer-button values used by hint bindings."""

    LEFT = 1
    RIGHT = 3

    @property
    def description(self) -> str:
        return f"{self.name.title()}-click hints"


class HintHost:
    """The screen owns one mounted hint interaction, not a second target roster."""

    async def action_show_hints(self) -> None:
        await self._show_hints(HintClick.LEFT)

    async def action_show_context_hints(self) -> None:
        await self._show_hints(HintClick.RIGHT)

    async def _show_hints(self, click: HintClick) -> None:
        self.dismiss_hints()
        excluded = (
            child
            for overlay in self.query_children(HintOverlay)
            for child in overlay.walk_children(with_self=True)
        )
        scene = self._compositor.activation_scene(click, excluded)
        if scene.targets:
            await HintSession.for_scene(self, scene, click).mount_on(self)

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


class HintOverlay(Widget):
    """Hint paint never intercepts the original control's pointer hit."""

    DEFAULT_CSS = "HintOverlay { text-style: bold reverse; }"
    hit_test_transparent = True
    ALLOW_SELECT = False


class HintLabel(HintOverlay):
    """One next key at the native click cell; the assigned sequence never changes."""

    DEFAULT_CSS = """
    HintLabel {
        position: absolute;
        overlay: screen;
        layer: _tooltips;
        width: auto;
        height: 1;
    }
    """

    def __init__(self, session, text: str, target: Activation):
        super().__init__()
        self.session = session
        self.text = text
        self.target = target

    def render(self) -> Content:
        prefix_length = len(self.session.prefix)
        return Content(self.text[prefix_length:prefix_length + 1])


class HintSession(HintOverlay, FrameOverlay, can_focus=True):
    """Own stable keys, current-frame positions, input, focus and retirement."""

    DEFAULT_CSS = """
    HintSession {
        position: absolute;
        overlay: screen;
        layer: _tooltips;
        width: 0;
        height: 0;
        scrollbar-size-horizontal: 0;
    }
    """
    alphabet = "asdfghjklqwertyuiopzxcvbnm"

    @classmethod
    def for_scene(cls, screen, scene: ActivationScene, click: HintClick):
        targets = sorted(scene.targets.values(), key=lambda target: (
            target.region.y, target.region.x))
        return cls(screen, targets, click)

    @classmethod
    def label_width(cls, count: int) -> int:
        width = 1
        while len(cls.alphabet) ** width < count:
            width += 1
        return width

    @classmethod
    def label(cls, index, width):
        characters = []
        for _ in range(width):
            index, digit = divmod(index, len(cls.alphabet))
            characters.append(cls.alphabet[digit])
        return "".join(reversed(characters))

    def __init__(self, screen, targets, click: HintClick):
        super().__init__()
        self.click = click
        self.original_focus: Widget | None = screen.focused
        self.prefix = ""
        width = self.label_width(len(targets))
        self.labels = tuple(
            HintLabel(self, self.label(index, width), target)
            for index, target in enumerate(targets)
        )

    async def mount_on(self, screen):
        await screen.mount(*self.labels, self)

    @property
    def _current_original_focus(self) -> Widget | None:
        original = self.original_focus
        if (original is not None and original.is_attached
                and original.screen is self.screen and self.screen is self.app.screen):
            return original
        return None

    def render(self) -> Content:
        return Content.empty()

    @on(events.Mount)
    def on_mount(self) -> None:
        if self.is_attached and self.screen is self.app.screen:
            self.screen.set_focus(self, scroll_visible=False)

    def frame_regions(self, compositor, geometry):
        placements = {label: Region(0, self.screen.size.height, 1, 1)
                      for label in self.labels}
        if not self.disabled:
            excluded = tuple(
                child for overlay in self.screen.query_children(HintOverlay)
                for child in overlay.walk_children(with_self=True))
            scene = compositor.activation_scene_from(geometry, self.click, excluded)
            for label in self.labels:
                target = scene.targets.get(label.target.identity)
                if target is not None:
                    label.target = target
                    if label.display and (placement := geometry.get(label)) is not None:
                        placements[label] = placement.region.at_offset(target.region.offset)
        return tuple(placements.items())

    def check_consume_key(self, key, character=None):
        return key == "escape" or (character is not None and character.isprintable())

    @on(events.Key)
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
                         if label.text.startswith(self.prefix) and label.target.available()]
            if not remaining:
                self.dismiss()
            elif len(remaining) == 1 and remaining[0].text == self.prefix:
                self.dismiss(target=remaining[0].target)
            else:
                for label in self.labels:
                    label.display = label.text.startswith(self.prefix)
                    if label.display:
                        label.refresh()

    @on(events.Paste)
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
        self.screen.run_worker(self._retire(target), group="hint-retirement")

    async def _retire(self, target):
        await self.screen.remove_children(self.labels)
        await self.remove()
        if target is not None:
            await target.activate()

    @on(events.Blur)
    def on_blur(self):
        self.dismiss(restore=False)

    def reconcile_publication(self):
        if self.disabled:
            return
        if self.original_focus is not None and self._current_original_focus is None:
            self.original_focus = None
        if not any(label.text.startswith(self.prefix) and label.target.available()
                   for label in self.labels):
            self.dismiss()
