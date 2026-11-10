"""Native click hints: spatial keys and a readable list share one interaction."""
from __future__ import annotations

from enum import IntEnum
from typing import ClassVar

from rich.text import Text

from textual import events
from textual._compositor import ActivationScene, FrameOverlay, PaintedActivation
from textual._hint_spaces import HintSpaces
from textual.binding import ModeBinding
from textual.containers import VerticalScroll
from textual.geometry import Offset, Region
from textual.content import Content
from textual.document._editing import VimMode
from textual.widget import Widget
from textual._on import on


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
        excluded = (
            child
            for overlay in self.query_children(HintOverlay)
            for child in overlay.walk_children(with_self=True)
        )
        scene = self._compositor.activation_scene(click, excluded)
        if not scene.targets:
            return
        session = HintSession.for_scene(self, scene, click)
        await session.mount_on(self)
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


class HintOverlay(Widget):
    """Transient hint paint, never an activation target or body-cell source."""

    DEFAULT_CSS = """
    HintOverlay { text-style: bold reverse; }
    """
    hit_test_transparent = True
    ALLOW_SELECT = False


class HintLabel(HintOverlay):
    """A key retains its painted activation rather than copying the record's fields."""

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

    @property
    def content(self) -> Content:
        return Content(self.text)

    def render(self) -> Content:
        return self.content.stylize(
            self.get_visual_style("hint-label--typed"), 0, len(self.session.prefix))


class SpatialHintLabel(HintLabel):
    """A compact key in a blank cell beside the original target."""

    DEFAULT_CSS = """
    SpatialHintLabel { position: absolute; overlay: screen; layer: _tooltips; }
    """

    def __init__(self, session, text: str, painted: PaintedActivation):
        super().__init__(session, text, painted)
        self.styles.width = len(text)


class LegendHintLabel(HintLabel):
    """A crowded-scene entry keeps the complete styled target text readable."""

    DEFAULT_CSS = """
    LegendHintLabel { width: 100%; height: auto; }
    """

    @property
    def content(self) -> Content:
        preview = Content.from_rich_text(Text.assemble(
            *((segment.text, segment.style or "") for segment in self.preview)))
        return super().content + Content(" ") + preview


class HintCaption(HintOverlay):
    """Fixed caption; docking excludes its cells from the scrolling key area."""

    DEFAULT_CSS = """
    HintCaption { dock: left; width: auto; max-width: 50%; height: 1; }
    """

    def __init__(self, session):
        super().__init__()
        self.session = session

    def render(self) -> Content:
        return self.session.caption


class HintSession(HintOverlay, FrameOverlay, can_focus=True):
    """Own key assignment, input and focus for every hint presentation."""

    DEFAULT_CSS = """
    HintSession {
        dock: bottom;
        overlay: screen;
        layer: _tooltips;
        width: 100%;
        height: 1;
        scrollbar-size-horizontal: 0;
    }
    """
    alphabet = "asdfghjklqwertyuiopzxcvbnm"
    label_type: ClassVar[type[HintLabel]] = HintLabel

    @classmethod
    def for_scene(cls, screen, scene: ActivationScene, click: HintClick):
        targets = sorted(scene.targets.values(), key=lambda item: (
            item.activation.region.y, item.activation.region.x))
        offsets = cls.offsets(scene, screen.size, targets)
        if offsets is None:
            return LegendHintSession(screen, targets, click)
        return SpatialHintSession(screen, targets, click, offsets)

    @classmethod
    def offsets(cls, scene, size, targets):
        spaces = HintSpaces(size, scene.occupied, cls.label_width(len(targets)))
        return spaces.allocate(
            target.preview_region.offset if target.preview.cell_length
            else target.activation.region.offset for target in targets)

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
        self.caption_widget = HintCaption(self)

    def compose(self):
        yield self.caption_widget

    async def mount_on(self, screen):
        await screen.mount(self)

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
        original = self._current_original_focus
        return original.key_mode_label if original is not None else super().key_mode_label

    @property
    def caption(self) -> Content:
        mode_label = self.key_mode_label
        return Content(
            f"{mode_label} · {self.click.caption}" if mode_label else self.click.caption
        )

    def render(self) -> Content:
        return Content.empty()

    @on(events.Mount)
    def on_mount(self) -> None:
        self.screen.bindings_updated_signal.subscribe(self, self._bindings_changed)

    @on(events.Unmount)
    def on_unmount(self) -> None:
        self.screen.bindings_updated_signal.unsubscribe(self)

    def _bindings_changed(self, _screen: Widget) -> None:
        self.caption_widget.refresh(layout=True)

    def focus_on_host(self):
        if self.is_attached and self.screen is self.app.screen:
            self.screen.set_focus(self, scroll_visible=False)

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
                         if label.display and label.text.startswith(self.prefix)]
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
        """Spatial keys already point at their source; a list owns scrolling."""

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
            self.refresh_bindings()
            self.caption_widget.refresh(layout=True)
        for label in self.labels:
            if label.display and not label.target.available():
                label.display = False
        if not any(label.display for label in self.labels):
            self.dismiss()


class SpatialHintSession(HintSession):
    """Place compact keys before publication, without covering body glyphs."""

    label_type = SpatialHintLabel

    def __init__(self, screen, targets, click: HintClick, offsets):
        super().__init__(screen, targets, click)
        for label, offset in zip(self.labels, offsets):
            label.absolute_offset = offset

    async def mount_on(self, screen):
        await screen.mount(*self.labels, self)

    def frame_regions(self, compositor, geometry):
        hidden = tuple((label, Region(0, self.screen.size.height, len(label.text), 1))
                       for label in self.labels)
        if self.disabled:
            return hidden
        overlays = tuple(
            child for overlay in self.screen.query_children(HintOverlay)
            for child in overlay.walk_children(with_self=True))
        scene = compositor.activation_scene_from(geometry, self.click, overlays)
        targets = [scene.targets.get(label.target.identity, label.painted)
                   for label in self.labels]
        offsets = self.offsets(scene, self.screen.size, targets)
        if offsets is None:
            self.disabled = True
            self.screen.run_worker(self._become_legend(targets), group="hint-retirement")
            return hidden
        regions = []
        for label, painted, offset in zip(self.labels, targets, offsets):
            label.painted = painted
            region = (Region(offset.x, offset.y, len(label.text), 1)
                      if label.display and label.target.identity in scene.targets
                      else Region(0, self.screen.size.height, len(label.text), 1))
            regions.append((label, region))
        return tuple(regions)

    async def _become_legend(self, targets):
        screen = self.screen
        replacement = LegendHintSession(screen, targets, self.click)
        replacement.original_focus = self.original_focus
        replacement.prefix = self.prefix
        for old, new in zip(self.labels, replacement.labels):
            new.display = old.display
        await self._retire(None)
        await replacement.mount_on(screen)
        replacement.focus_on_host()

    async def _retire(self, target):
        await self.screen.remove_children(self.labels)
        await super()._retire(target)


class LegendHintSession(HintSession, VerticalScroll):
    """When keys cannot fit beside text, show a wrapped, vertically browsable list."""

    DEFAULT_CSS = """
    LegendHintSession { height: auto; max-height: 50%; }
    LegendHintSession > HintCaption { dock: top; width: 100%; max-width: 100%; }
    """
    label_type = LegendHintLabel

    def compose(self):
        yield from super().compose()
        yield from self.labels

    def frame_regions(self, compositor, geometry):
        return ()

    def reveal(self, labels):
        if labels and labels[0].is_attached:
            labels[0].scroll_visible(animate=False, force=True)
