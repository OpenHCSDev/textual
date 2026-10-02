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

## Published source checkpoint

Production: two files,12 added/4 deleted lines. Screen obtains its existing
geometry-target declaration once for the transaction. Both normal viewport
reflow and fast scroll reflow consume that same iterable; Compositor passes it
to its original arrangement. The target parameter is required for direct fast
reflow callers; all original callers and two direct native test consumers were
migrated. No copied target state, geometry, cache or new type.

Existing NRA parses249 Textual modules with zero omissions before and after.
There is one production fast-reflow caller, the original Screen owner. Toad
source/recorder tools have no direct calls. AST names alone do not prove dynamic
resolution; original receiver semantics were read before implementation.

The original real native target checks pass actual fast-path execution and
four width/scroll transactions, full-reference geometry without full-layout
query, and foreign/removed refusal. Whole-body capture and failure cleanup
remain correct. The existing joined real Toad body family also passes all three
body kinds, target boxes, style/resize/reentry/input/disposal. Source receipt:
`native-scroll-geometry26-source-receipt.json`.

This is a useful source checkpoint only. Heisenberg owns the one later changed
installed gate; no new capture/environment/provider or performance claim here.
