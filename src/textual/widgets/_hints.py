"""Click-hint badges borrow their targets' original effects and frame positions."""
from __future__ import annotations

from enum import IntEnum
from typing import ClassVar

from rich.text import Text

from textual import events
from textual._compositor import ActivationScene, FrameOverlay, PaintedActivation
from textual._on import on
from textual.binding import ModeBinding
from textual.containers import VerticalScroll
from textual.content import Content
from textual.document._editing import VimMode
from textual.geometry import Offset, Region
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
    """A stable key retains the current frame's original painted activation."""

    DEFAULT_CSS = """
    HintLabel { width: auto; height: 1; }
    HintLabel > .hint-label--typed { text-style: bold not reverse; }
    """
    COMPONENT_CLASSES: ClassVar[set[str]] = {"hint-label--typed"}

    def __init__(self, session, text: str, painted: PaintedActivation):
        super().__init__()
        self.session = session
        self.text = text
        self.painted = painted

    @property
    def target(self):
        return self.painted.activation

    @property
    def preview(self):
        return self.painted.preview

    def update_paint(self, painted: PaintedActivation) -> None:
        self.painted = painted

    @property
    def content(self) -> Content:
        return Content(self.text)

    def render(self) -> Content:
        return self.content.stylize(
            self.get_visual_style("hint-label--typed"), 0, len(self.session.prefix))


class SpatialHintLabel(HintLabel):
    """The badge starts at its clickable item's exposed anchor, as before."""

    DEFAULT_CSS = """
    SpatialHintLabel { position: absolute; overlay: screen; layer: _tooltips; }
    """


class LegendHintLabel(HintLabel):
    """Only overlapping badges need a browsable copy of their styled target text."""

    DEFAULT_CSS = "LegendHintLabel { width: 100%; height: auto; }"

    def update_paint(self, painted: PaintedActivation) -> None:
        changed = tuple(self.preview) != tuple(painted.preview)
        super().update_paint(painted)
        if changed:
            self.refresh(layout=True)

    @property
    def content(self) -> Content:
        preview = Content.from_rich_text(Text.assemble(
            *((segment.text, segment.style or "") for segment in self.preview)))
        return super().content + Content(" ") + preview


class HintSession(HintOverlay, FrameOverlay, can_focus=True):
    """Share keys, current-frame discovery, input, focus and retirement."""

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
    label_type: ClassVar[type[HintLabel]] = HintLabel

    @classmethod
    def for_scene(cls, screen, scene: ActivationScene, click: HintClick):
        targets = sorted(scene.targets.values(), key=lambda item: (
            item.activation.region.y, item.activation.region.x))
        anchors = cls.anchors(screen.size, targets, cls.label_width(len(targets)))
        if anchors is None:
            return LegendHintSession(screen, targets, click)
        return SpatialHintSession(screen, targets, click, anchors)

    @staticmethod
    def anchors(size, targets, width):
        """Use original target positions; never search elsewhere on the screen."""
        if width > size.width:
            return None
        origins = (item.preview_region.offset if item.preview.cell_length
                   else item.activation.region.offset for item in targets)
        anchors = tuple(Offset(min(origin.x, size.width - width), origin.y)
                        for origin in origins)
        ordered = sorted(anchors, key=lambda offset: (offset.y, offset.x))
        if any(first.y == second.y and first.x + width >= second.x
               for first, second in zip(ordered, ordered[1:])):
            return None
        return anchors

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
            self.label_type(self, self.label(index, width), painted)
            for index, painted in enumerate(targets)
        )

    async def mount_on(self, screen):
        await screen.mount(self)

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
        self.focus_on_host()

    def focus_on_host(self):
        if self.is_attached and self.screen is self.app.screen:
            self.screen.set_focus(self, scroll_visible=False)

    def frame_regions(self, compositor, geometry):
        live = []
        if not self.disabled:
            excluded = tuple(
                child for overlay in self.screen.query_children(HintOverlay)
                for child in overlay.walk_children(with_self=True))
            scene = compositor.activation_scene_from(geometry, self.click, excluded)
            for label in self.labels:
                painted = scene.targets.get(label.target.identity)
                if painted is not None:
                    label.update_paint(painted)
                    if label.display:
                        live.append(label)
        return self.place_labels(geometry, live)

    def place_labels(self, geometry, live):
        """A list uses native layout; spatial badges override only placement."""
        return ()

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
                self._filter_labels()

    def _filter_labels(self):
        remaining = []
        for label in self.labels:
            label.display = label.text.startswith(self.prefix)
            if label.display:
                label.refresh()
                remaining.append(label)
        self.reveal(remaining)

    def reveal(self, labels):
        """Spatial badges already sit on their targets."""

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


class SpatialHintSession(HintSession):
    """Keep each badge on the same target's position in the frame being drawn."""

    label_type = SpatialHintLabel

    def __init__(self, screen, targets, click: HintClick, anchors):
        super().__init__(screen, targets, click)
        for label, anchor in zip(self.labels, anchors):
            label.absolute_offset = anchor

    async def mount_on(self, screen):
        await screen.mount(*self.labels, self)

    def place_labels(self, geometry, live):
        hidden = {label: Region(0, self.screen.size.height, len(label.text), 1)
                  for label in self.labels}
        anchors = self.anchors(self.screen.size, [label.painted for label in live],
                               self.label_width(len(self.labels)))
        if anchors is None:
            self.disabled = True
            targets = [label.painted for label in self.labels]
            self.screen.run_worker(self._become_legend(targets), group="hint-retirement")
            return tuple(hidden.items())
        for label, anchor in zip(live, anchors):
            placement = geometry.get(label)
            if placement is not None:
                hidden[label] = placement.region.at_offset(anchor)
        return tuple(hidden.items())

    async def _become_legend(self, targets):
        screen = self.screen
        replacement = LegendHintSession(screen, targets, self.click)
        replacement.original_focus = self.original_focus
        replacement.prefix = self.prefix
        replacement._filter_labels()
        await replacement.mount_on(screen)
        await self._retire(None)

    async def _retire(self, target):
        await self.screen.remove_children(self.labels)
        await super()._retire(target)


class LegendHintSession(HintSession, VerticalScroll):
    """Only overlapping keys use the existing wrapped, scrollable target list."""

    DEFAULT_CSS = """
    LegendHintSession {
        dock: bottom;
        width: 100%;
        height: auto;
        min-height: 1;
        max-height: 100%;
        scrollbar-size-vertical: 0;
    }
    """
    label_type = LegendHintLabel

    def compose(self):
        yield from self.labels

    def reveal(self, labels):
        if labels and labels[0].is_attached:
            labels[0].scroll_visible(animate=False, force=True)

    def reconcile_publication(self):
        super().reconcile_publication()
        for label in self.labels:
            label.display = label.text.startswith(self.prefix) and label.target.available()
