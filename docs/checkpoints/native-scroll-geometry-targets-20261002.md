# Preserve declared geometry targets during native scrolling

Continue merged Textual25 in the same worktree. Heisenberg grants
Screen._refresh_layout and Compositor.reflow_visible target propagation;
he retains Toad registration/lifetime/sidebar and installed integration.

The same322/25 installed profile still observes retirement admission falling
through to full_map. Source shows normal viewport reflow receives the existing
Screen._layout_geometry_targets declaration, while the scroll fast path omits
it. That path rebuilds the viewport map without required offscreen body boxes.

Read all original reflow callers; make both native layout transactions consume
the same target declaration. Extend the existing Compositor algorithm, migrate
callers, delete the omitted/independent selection. No new map, cache, target
store, Widget copy or rendering implementation. Capture25 remains unchanged.

Implement the source batch before final native checks. Reuse existing geometry
and retained-body checks; Heisenberg owns one later changed installed gate.
No new environment, capture or provider operation in this contribution.
