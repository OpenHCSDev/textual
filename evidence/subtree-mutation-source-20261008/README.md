# Explicit mutation geometry

`Compositor.render_subtree_strips` keeps mandatory `admit`: it acquires the
complete original paint cohort synchronously, then returns `Size` and an
iterator of strip bands. Each band uses the original cuts and renderer, is at
most the acquired viewport height, and closes borrowed geometry before yielding.
Preceding-source callers drain before writing; retirement callers can cooperate
between bands while their original witnesses and custody remain current. The
six band controls at `57523e1b` passed (1.86s) and were not repeated here.

Visible arrangement no longer forces complete offscreen acquisition merely to
fill an intrinsic cache entry. A partial source retains exact placed geometry.
`Compositor.acquire_subtree_geometry(root)` supplies the existing complete
`SubtreeGeometryPlacement` before writes; no paint or publication occurs. The
transaction owns that source independently of cache eviction. Missing placement
or an incomplete source returns None. Expansion to an unmodified ancestor
borrows held children; a new descendant scope inside a held complete source is
unavailable because that source does not own every descendant arrangement input.

Screen's mutation hook now returns original roots mapped to these placements
(or None for the exact published fallback). Both resource kinds capture native
parent edges once. Shared source matching retains distinct exact/translated
placement rules; held projection filters original prune admission and native
self-paint participation along captured ancestry. Screen overlays retain their
screen clip, distinct from the acquired body's incoming/expanded paint clip.

Mutation release calls `Screen.check_idle()`. Screen resumes its retained layout
members; the caller does not invalidate a window or manufacture a layout request.
Native scroll/source epochs remain unchanged, including capture currentness.
Layout messages record actionable intent before the message pump's queued next
callbacks run. Callback admission also derives that intent from the original
pending members after release; it can precede Idle. It uses the same acquired
mutation mapping and the existing layout-intent owner. Geometry wakeups do not
create new requests for members already consumed by that publication.

An opaque source whose destination changes retains exact original rectangles.
It still owns captured membership and self-paint ancestry: children now covered
by their original parent's retained paint cannot return through the final held
snapshot merge. An incomplete fallback remains placed and partial.

First affected batch at 01ccf09d: six passes, two failures. One control incorrectly
asserted that a held RLock already meant a source mutation; it now checks the
actual published mutation scope. The other exposed the real overlay clip defect:
complete explicit acquisition incorrectly returned IntrinsicSubtreeGeometry for
an overlay. The corrected clip and release checks passed (3 / 0.81s); that result
predates the shared captured-parent representation change. Initial tool output is
retained in the original conversation; neither result is overall acceptance.

The shared source/ancestry batch then passed twelve checks and exposed one real
opaque-source regression: after scrolling, fallback restored children covered
by retained self-paint. The corrected fallback, original overlay retirement and
held-scroll checks passed (3 / 0.85s). The unchanged ancestor expansion plus
explicit descendant refusal passed (1 / 0.46s).

Ordinary pending-member release passed in the first callback batch. Two queue
control negatives are retained: they incorrectly required layout intent still
to be false when another original admission could already have recorded it.
The final real message-pump control releases on the same pump that acquired the
transaction, queues admission within that callback delivery, and verifies the
sender stays queued until actual layout completes (1 / 0.39s). No held paint
damage hides the pending layout requirement.

Raw logs and the existing Package AST census are retained beside this file.
The census covers production and current tests with zero parse omissions;
historical evidence scripts retain their original private API shape.

Parent owns matching history transaction/reader lifetime and saved-history
application verification. Parent reports four matching source application paths
passed, but source was changing during those runs; the final committed pair still
needs its immutable saved-history measurement. No installed change or latency
gain is claimed here. Explicit complete geometry acquisition remains synchronous.
One uncached custom visual can still render a whole widget within a band; no
renderer deadline or readiness exemption is introduced.
Historical evidence scripts remain at their original source/API scope in Git.
