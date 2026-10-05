# Use the original scene and size owners for frame transitions

Base: merged native70 c5e7eba344bd2982f30338e8acd18210e19de2ac.
Same completed native checkout; Text70/68/69 source proofs and wheels retained.

Source finding: reflow_visible substitutes an empty predecessor when the last
committed scene is a full map. Its damage comparison then treats the root and
unchanged chrome as new. Full reflow after scrolling also uses the old full map
for damage instead of the latest viewport scene. These are source-supported
wrong predecessor choices, not attribution of the original RichVisual sample
or a measured CPU/FPS improvement.

Compositor owns the existing published scene map. Make that acquisition carry
reflow, visible reflow, lazy full geometry publication and layer projection;
delete their independent predecessor choices. Keep logical show/hide membership
and conservative viewport exposure separate: a complete geometry query does
not prove that every widget has consumed native size publication. Capture
geometry and current-placement validity retain their existing contracts.

Widget._size_updated already owns size, virtual extent and container changes
and explicitly returns whether a Resize event should be sent. Screen must use
that result instead of the parallel region-size-only ReflowResult.resized set.
Delete the set, field, comparison and every consumer. ScrollView keeps its
independently authored virtual extent and container projection but reuses the
existing Widget size commit; its original scrollbar resource retirement stays
with its existing scrollbar update behavior. No change to the size-hook ABI or
Toad Body/Window callbacks.

AST and complete declaration/caller/lifetime reading precede edits. Preserve
native show/hide order, viewport geometry targets, stable paint ties, authored
scroll extents, scrollbar feedback, capture and lazy-layout semantics. No new
map/cache/type/state flag, caller-built readiness predicate or alternate paint
path. Native Compositor/Screen/ScrollView only; no Toad writes.

Batch source and affected native App checks after the coherent implementation.
Existing Heisenberg workflow owns the next meaningful changed installed frame
and motion qualification; no repeat of native70/68/69 controls, provider,
recording, environment, installed package or native SDK build. Source-only
until those boundaries are qualified. CI is deferred; results are recorded
without adding a delivery wait.

## Qualified native source and App checkpoint

Original source63fe769a181bbd149c51f42ecfaa635aed0b7cd2: 21 checks passed,
0 failed in 4.00s, terminal exit0. The single affected batch ran
`tests/test_native_scene_size_publication.py`,
`tests/test_compositor_frame_damage.py` and
`tests/test_viewport_geometry_targets.py`. Original command/log and SHA are
bound in source-app01.json; no native70/68/69 controls were repeated.

The actual native Apps cover Screen Resize delivery after a virtual-only child
mount and a container-only authored ScrollView gutter change, preserving its
original virtual extent and scrollbar dimensions. They also cover first scroll
after full layout, full layout after viewport scroll, and an empty detached
viewport publication. Both Screen reflow paths now deliver the Widget's
committed outer/virtual/container dimensions rather than the raw layout inputs.

Three production files: 32 added / 43 deleted. Removed the independent resized
set, record field and consumer decision, repeated predecessor choices and the
ScrollView size-commit copy. Existing Widget owns size commit and resize need;
Compositor's derived published-map acquisition owns the previous paint scene.
Logical show/hide membership and conservative viewport sizing remain distinct.
No change to Widget/Toad size-hook ABI, authored extent policy or generic
layout invalidation.

This is scoped native source/App readiness. No installed terminal motion,
measured speed, CPU gain, smoothness or full performance acceptance. Heisenberg
owns the next meaningful installed union with native70/Toad463; CI is deferred
for this checkpoint. No wheel/build/package/App/film repeat is required for the
source-equal evidence head.
