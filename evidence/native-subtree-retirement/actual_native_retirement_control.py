"""Actual native mount/remove/reflow: retire one branch, retain another scene."""
import argparse
import asyncio
import json
from pathlib import Path
import sys


async def run(output):
    import textual
    from textual.app import App, ComposeResult
    from textual.containers import VerticalGroup
    from textual.widgets import Static

    class RetainedBody(VerticalGroup):
        CACHE_SUBTREE_GEOMETRY = True

    class NativeApp(App):
        CSS = "RetainedBody {height: 10;} Static {height: 2;}"

        def compose(self) -> ComposeResult:
            with RetainedBody(id="retiring-branch"):
                yield Static("RETIRE ME", id="retired")
                yield Static("FIRST BRANCH")
            with RetainedBody(id="retained-branch"):
                yield Static("SIBLING LIVE")

    receipt = {"textual": textual.__file__, "scope": "Actual native scene/resource control; not installed Toad readiness"}
    app = NativeApp()
    try:
        async with app.run_test(size=(80, 30)) as pilot:
            await pilot.pause()
            compositor = app.screen._compositor
            retiring = app.query_one("#retiring-branch")
            retained = app.query_one("#retained-branch")
            compositor.reflow(app.screen, app.screen.size)
            original = compositor._subtree_geometry[retained]
            affected = compositor._subtree_geometry[retiring]
            retired = app.query_one("#retired")
            await retired.remove()
            receipt["unrelated_entry_retained_before_reflow"] = compositor._subtree_geometry.get(retained) is original
            receipt["affected_entry_evicted_before_reflow"] = compositor._subtree_geometry.get(retiring) is not affected
            await pilot.pause()
            compositor.reflow(app.screen, app.screen.size)
            receipt["unrelated_entry_retained_after_reflow"] = compositor._subtree_geometry[retained] is original
            frame = "\n".join(strip.text for strip in compositor.render_strips())
            receipt["visible_retained_body"] = "SIBLING LIVE" in frame
            receipt["retired_body_absent_from_frame"] = "RETIRE ME" not in frame
            receipt["no_retired_scene_custody"] = all(retired not in entry[1] and retired not in entry[2]
                and retired not in entry[3] for entry in compositor._subtree_geometry.values())
            assert all(receipt[name] for name in (
                "unrelated_entry_retained_before_reflow", "affected_entry_evicted_before_reflow",
                "unrelated_entry_retained_after_reflow", "visible_retained_body",
                "retired_body_absent_from_frame", "no_retired_scene_custody")), receipt
            receipt["result"] = "PASS"
    finally:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.source_root:
        sys.path.insert(0, str(args.source_root / "src"))
    asyncio.run(run(args.output))
