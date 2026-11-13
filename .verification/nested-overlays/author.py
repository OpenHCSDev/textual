import json
from pathlib import Path
r=Path.cwd()
test='''async def test_select_overlay_paints_above_its_containing_screen_overlay():
    class NestedOverlayApp(App):
        CSS = """
        Screen { layers: lower upper; }
        #workspace { overlay: screen; layer: upper; width: 32; height: 12; }
        Select { width: 30; height: 3; }
        #body { height: 8; }
        """

        def compose(self):
            yield Container(
                Select([("First setting", "first"), ("Second setting", "second")],
                       value="first"),
                Static("Workspace body", id="body"),
                id="workspace",
            )

    app = NestedOverlayApp()
    async with app.run_test(size=(40, 16)) as pilot:
        await pilot.click(Select)
        await pilot.pause()
        select = app.query_one(Select)
        overlay = select.query_one(SelectOverlay)
        body = app.query_one("#body")
        # Read the committed scene before any geometry lookup can acquire it.
        scene = app.screen._compositor._published_map
        geometry = scene[overlay]
        assert select.expanded
        assert geometry.order > scene[body].order
        x, y, _, _ = geometry.region
        hit = app.screen._compositor.get_widget_at(x + 1, y + 1)[0]
        assert hit is overlay or overlay in hit.ancestors
        await pilot.press("down", "enter")
        assert select.value == "second"


'''
ops=[dict(operation='ensure_import',file_path=str(r/'tests/test_compositor.py'),import_source='from textual.widgets import Select\nfrom textual.widgets._select import SelectOverlay'),dict(operation='insert_before_target',file_path=str(r/'tests/test_compositor.py'),target_qualname='test_point_hits_follow_layer_clip_visibility_and_scene_changes',source=test)]
Path('.verification/nested-overlays/control.plan.json').write_text(json.dumps({'recipes':[{'recipe_id':'nested-screen-overlay-control','operations':ops}]},indent=2))
ops=[dict(operation='patch_target',file_path=str(r/'src/textual/_compositor.py'),target_qualname='Compositor._place_children',replacements=[dict(old_source='((1, 0, 0),) + child_order[-1:] if overlay else child_order',new_source='((order[0][0] + 1, 0, 0),) + child_order[-1:] if overlay else child_order')])]
Path('.verification/nested-overlays/fix.plan.json').write_text(json.dumps({'recipes':[{'recipe_id':'derive-nested-screen-overlay-depth','operations':ops}]},indent=2))
