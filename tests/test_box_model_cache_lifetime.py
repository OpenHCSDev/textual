from fractions import Fraction

from textual.app import App
from textual.geometry import Size
from textual.widget import Widget
from textual.widgets import Static


async def test_obsolete_measurement_revisions_are_released_without_losing_width_reuse():
    app = App()
    async with app.run_test() as pilot:
        widget = Static("wrapped text " * 30)
        await app.mount(widget)
        await pilot.pause()
        fraction = Fraction(1)
        widths = (30, 60, 90)

        def measured(width):
            return widget._get_box_model(Size(width, 20), app.size, fraction, fraction)

        for index in range(12):
            widget.update("changed paragraph " * (index + 1))
            widget.styles.padding = (0, index % 3)
            await pilot.pause()
            models = {width: measured(width) for width in widths}
            for width, model in models.items():
                assert measured(width) is model, "Same-revision width result should remain reusable"
            expected = (widget._layout_updates, widget.styles._cache_key)
            assert all(key[-2:] == expected for key in widget._box_model_cache.keys()), (
                "Unreachable previous-generation box models retained", list(widget._box_model_cache.keys())
            )


async def test_ancestor_measurements_remain_correct_after_child_layout_changes():
    app = App()
    async with app.run_test() as pilot:
        leaf = Static("first")
        container = Widget(leaf)
        container.styles.height = "auto"
        await app.mount(container)
        await pilot.pause()
        before = container._layout_updates
        old_height = container.size.height
        leaf.update("line\n" * 12)
        await pilot.pause()
        assert container._layout_updates > before
        assert container.size.height > old_height
        key = (container._layout_updates, container.styles._cache_key)
        assert all(entry[-2:] == key for entry in container._box_model_cache.keys())
