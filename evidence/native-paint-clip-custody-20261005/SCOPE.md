# Native paint rectangle custody

Base: actual Textual main06771827eeff2a98c40a41fd2bc6cb6313db7a87.
Merged65 source, e253 wheel and all controls remain untouched.

The existing compositor paint mapping derives ordered widget paint from original
MapGeometry. It currently stores an unbounded clip and each cuts/render/chops
consumer re-intersects the same original region. Make `_paint_regions` own the
positive rectangle within original scene/capture bounds, then consumers borrow
that fact. Damage crop and foreground exposure are distinct later selections.
Raw MapGeometry, source order, geometry lookup, membership and retirement remain
their original owners. Existing layers are already cached per published scene;
complete widget membership remains necessary and is not removed.

Claims: `_paint_regions`, `_cuts_for_regions`, `_get_renders`, `_render_chops` and
related compositor paint-query consumers. No new type, field, map, flag, cache,
timer or alternate scene. Heis owns Toad body/frame consumers. Source only;
no App, package, provider, recording or gain qualification/purpose.

Complete roots and consumer evidence precede changes. Source semantics first,
coherent caller migration, then proportionate validation under an actual later
grant. Pattern IMPL-12: repeated geometry acquisition by related consumers.

## Published coherent source

Production7934c06e0cbb03aa4e10fb53bc1a09f088f49e73: one production file,
16 added /23 deleted lines relative to actual main06771827. Source only, untested.

The first pair member stays the ORIGINAL widget region, including its origin and
logical dimensions. The second is the positive original region/clip intersection
within this screen or detached capture's bounds. Only this existing paint mapping
owns that admitted rectangle. MapGeometry itself and all considered/invisible
membership remain unchanged, including offscreen explicit geometry and full-map
or complete body capture.

Cuts trust this already bounded rectangle rather than intersecting region, clip
and bounds again. Widget rendering keeps the distinct vertical damaged-row crop
and foreground-exposure selection. It emits the actual selected rectangle plus
strips; the only native unpack consumer now borrows that rectangle directly. The
unused original-region return and the repeated chop intersection are deleted.
Original widget origin is still used to request relative render_lines, preserving
metadata/selection/link coordinate semantics. Partial horizontal damage retains
original cut alignment; no dirty-x clipping or renderer policy is added.

Existing layer sorting is already cached per published scene, so it stays. The
unbounded geometric clip is still available from original MapGeometry to geometry
consumers. Positive-pixel paint membership is distinct from complete native widget
membership; empty intersections cannot paint and remain available to logical
geometry/lifetime consumers through their original owners.

Complete native249/tests460 and Toad288/tests397/tools41 roots parsed without
omissions before. After native249/tests460 parsed without omissions. All actual
native cut/render/chop producers and callers were migrated; wrappers in existing
controls only delegate to the original renderer and do not unpack its old triple.
No obsolete triple annotation/unpack/reintersection remains in the owned roots.
The original graph and after acquisitions are in owner-consumers.json; dynamic
aliases/external private-method overrides remain explicit limitations.

Heis confirmed no known Toad reader requires the paint pair's unbounded clip.
Pager edge readers borrow the unchanged original region, not paint extent. His
pixel/window consumers keep their genuine Window clipping fact; once normally
paired with this library, their extra region intersection can be reviewed as an
identity operation. No such caller migration is made against old native65 or the
current installed prefix, and no compatibility/version branch is introduced.

No source App/control run, wheel, package access, keeper, provider, capture or
frame/CPU measurement was performed. Final affected controls remain to exercise
partial horizontal/vertical damage, offscreen-origin body capture, overlays,
selection/link metadata and native interaction/retirement under the next actual
grant. Frozen65/e253/controls and Heis453 tuple remain immutable.
