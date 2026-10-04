# Reuse the original scene acquisition across layout and paint

Native contributor owns `_compositor.py`; Heisenberg415 owns the Toad reader,
viewport and frame consumers. Same checkout, normally integrated main48.
No new environment, compositor, map, cache, type, state flag or recording.

Read the original412 saved-session profile and original native lifecycle first.
It records `layers` during held Up and `_get_renders`/`render_regions` during
motion. Those are observed stack transitions, not calls, durations or CPU share.
Raw evidence stays at
`/home/ts/.cache/agent-scratch/body412-materialization-public-20261003-01/capture`.

The source supplies the concrete repeated work: Screen's size-publication pass
acquires `Compositor.layers`, sorting its original committed geometry. Paint
then acquires `visible_widgets`, independently sorting that same geometry in
`_paint_regions`. The existing ordered layer resource must carry the work for
visible clipping, hit testing, cuts and screen paint. Body capture orders its
own synchronous geometry through the same original ordering algorithm, without
publishing it as screen geometry or retaining another map.

Close full/partial/inline/export/subtree paint consumers together. Remove the
extra eager scene snapshot in `_get_renders` where the supplied paint mapping
already owns this synchronous cohort, and lend the same cuts resource through
partial composition and its update. Preserve native layer order, clipping,
exposure, source/style metadata, crop semantics, capture isolation and lazy
public geometry lookup. Keep ordinary widget lifecycle callbacks unchanged.
Patterns: IMPL-12/13, duplicated acquisition rather than new source authority.

Before evidence uses the existing NRA/refactor-audit Package parser over complete
native249 and Toad288 modules, zero parse omissions. AST establishes declared
consumers; dynamic extensions and arbitrary mutation of private compositor
resources cannot be resolved statically. Read the resulting sites semantically.

Implementation first. One final bounded native control batch must protect actual
layered/occluded/wide-row output, clipping, partial/full/export/capture and input
geometry. The next meaningful changed Heisenberg installed saved-session journey
supplies physical qualification. No unchanged412/48 repetition, provider call or
isolated speed claim. Full144Hz/CPU/IRC/DM/cold-warm performance remains active.
