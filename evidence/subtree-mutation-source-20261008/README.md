# Explicit mutation geometry

Visible arrangement no longer forces complete offscreen acquisition merely to
fill an intrinsic cache entry. A partial source retains exact placed geometry.
`Compositor.acquire_subtree_geometry(root)` supplies the existing complete
`SubtreeGeometryPlacement` before writes; no paint or publication occurs. The
transaction owns that source independently of cache eviction. Missing placement
or an incomplete source returns None. Nested acquisition borrows held children.

Screen's mutation hook now returns original roots mapped to these placements
(or None for the exact published fallback). Both resource kinds capture native
parent edges once. Shared source matching retains distinct exact/translated
placement rules; held projection filters original prune admission and native
self-paint participation along captured ancestry. Screen overlays retain their
screen clip, distinct from the acquired body's incoming/expanded paint clip.

Mutation release calls `Screen.check_idle()`. Screen resumes its retained layout
members; the caller does not invalidate a window or manufacture a layout request.
Native scroll/source epochs remain unchanged, including capture currentness.

First affected batch at 01ccf09d: six passes, two failures. One control incorrectly
asserted that a held RLock already meant a source mutation; it now checks the
actual published mutation scope. The other exposed the real overlay clip defect:
complete explicit acquisition incorrectly returned IntrinsicSubtreeGeometry for
an overlay. The corrected clip and release checks passed (3 / 0.81s); that result
predates the shared captured-parent representation change. Initial tool output is
retained in the original conversation; neither result is overall acceptance.

Parent owns matching history transaction/reader lifetime and saved-history
application verification. No installed change or latency gain is claimed here.
Historical evidence scripts remain at their original source/API scope in Git.
