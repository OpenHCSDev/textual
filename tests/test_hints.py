from dataclasses import dataclass
from itertools import combinations

import pytest

from textual.app import App, ComposeResult
from textual.css.scalar import Scalar
from textual.document._editing import EditingMode
from textual.geometry import Region
from textual.widgets import Static, Input, TextArea, Checkbox, RadioButton, Switch, Collapsible, Select
from textual.widgets._collapsible import CollapsibleTitle
from textual.widgets._hints import HintClick, HintLabel, HintSession


class DenseLinksApp(App):
    """27 targets two cells apart, so two-letter labels would touch."""

    CSS = "Static { margin-top: 5; }"

    def compose(self) -> ComposeResult:
        yield Static(" ".join(f"[@click=app.notify('{index}')]x[/]" for index in range(27)))


async def test_hint_labels_are_separated():
    app = DenseLinksApp()
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        await app.screen.action_show_hints()
        await pilot.pause()
        regions = [label.region for label in app.screen.query_children(HintLabel)]
        assert len(regions) == 27
        for first, second in combinations(regions, 2):
            assert first.y != second.y or first.right < second.x or second.right < first.x, (first, second)


class NativeControlsApp(App):
    CSS = "TextArea { height: 4; } Input { height: 3; }"

    def compose(self):
        yield Input('search stays', id='search')
        yield TextArea('draft stays', id='draft')
        yield Checkbox('Filter', id='filter')
        yield RadioButton('Choice', id='choice')
        yield Switch(id='switch')
        with Collapsible(title='Group', collapsed=True):
            yield Static('Members')
        yield Select([('One', 1), ('Two', 2)], id='select')


async def test_native_hints_focus_inputs_and_activate_control_owners():
    app = NativeControlsApp()
    async with app.run_test(size=(90, 40)) as pilot:
        await pilot.pause()

        async def choose(widget):
            await app.screen.action_show_hints()
            await pilot.pause()
            labels = [label for label in app.screen.query_children(HintLabel)
                      if label.target.widget is widget and label.display]
            assert len(labels) == 1, (widget, labels)
            await pilot.press(*labels[0].text)
            await pilot.pause()
            assert not app.screen.query_children(HintSession)

        search, draft = app.query_one(Input), app.query_one(TextArea)
        await choose(search)
        assert search.has_focus and search.value == 'search stays'
        await choose(draft)
        assert draft.has_focus and draft.text == 'draft stays'
        for widget in (app.query_one(Checkbox), app.query_one(RadioButton), app.query_one(Switch)):
            assert not widget.value
            await choose(widget)
            assert widget.value
            assert draft.has_focus and draft.text == 'draft stays'
        group = app.query_one(Collapsible)
        await choose(group.query_one(CollapsibleTitle))
        assert not group.collapsed
        await choose(group.query_one(CollapsibleTitle))
        assert group.collapsed
        select = app.query_one(Select)
        await choose(select)
        assert select.expanded
        await pilot.press('escape')


@dataclass(frozen=True)
class HintCaptionMode(EditingMode):
    """A label-only mode leaves native editing and binding behavior unchanged."""

    text: str

    @property
    def label(self) -> str:
        return self.text


class HintCaptionApp(App[None]):
    CSS = "TextArea { height: 4; } Static { margin-top: 1; }"

    def compose(self) -> ComposeResult:
        yield TextArea("draft stays")
        yield Static("[@click=app.notify('target')]Hint target[/]")


@pytest.mark.parametrize("click", tuple(HintClick))
async def test_hint_caption_initial_unset_width_mount(click: HintClick) -> None:
    app = HintCaptionApp()
    async with app.run_test(size=(80, 24)) as pilot:
        editor = app.query_one(TextArea)
        editor.editing_mode = HintCaptionMode("NORMAL")
        editor.focus()
        await pilot.pause()
        targets = app.screen._compositor.activation_targets(click)
        assert targets, "The session must borrow actual published targets"
        session = HintSession(app.screen, targets, click)
        assert session.styles.width is None

        await app.screen.mount(*session.labels, session)
        session.focus_on_host()
        await pilot.pause()

        assert app.screen.query_one(HintSession) is session
        assert app.screen.focused is session
        assert session.original_focus is editor
        assert session.styles.width == Scalar.from_number(
            min(app.screen.size.width, session.caption.cell_length)
        )
        assert session.render().plain == f"{editor.editing_mode.label} · {click.caption}"
        await pilot.press("escape")
        await pilot.pause()
        assert not app.screen.query_children(HintSession)
        assert editor.has_focus


@pytest.mark.parametrize("click", tuple(HintClick))
async def test_hint_caption_same_width_mode_change(click: HintClick) -> None:
    app = HintCaptionApp()
    async with app.run_test(size=(80, 24)) as pilot:
        editor = app.query_one(TextArea)
        original_mode = HintCaptionMode("NORMAL")
        replacement_mode = HintCaptionMode("INSERT")
        editor.editing_mode = original_mode
        editor.focus()
        await pilot.pause()
        assert app.screen._compositor.activation_targets(click)
        await app.screen._show_hints(click)
        await pilot.pause()
        session = app.screen.query_one(HintSession)
        width, offset = session.styles.width, session.absolute_offset
        positions = tuple(label.absolute_offset for label in session.labels)
        crop = Region(0, 0, session.size.width, 1)
        assert original_mode.label in "".join(
            strip.text for strip in session.render_lines(crop)
        )

        editor.editing_mode = replacement_mode
        await pilot.pause()

        assert app.screen.query_one(HintSession) is session
        assert app.screen.focused is session
        assert session.original_focus is editor
        assert session.styles.width == width
        assert session.absolute_offset == offset
        assert tuple(label.absolute_offset for label in session.labels) == positions
        painted = "".join(strip.text for strip in session.render_lines(crop))
        assert replacement_mode.label in painted
        assert original_mode.label not in painted
        assert session.render().plain == f"{replacement_mode.label} · {click.caption}"
        await pilot.press("escape")
        await pilot.pause()
        assert not app.screen.query_children(HintSession)
        assert editor.has_focus
