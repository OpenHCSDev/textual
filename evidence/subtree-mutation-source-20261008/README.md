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
application verification. Four matching source application paths passed. The
immutable 3c7d5ec0/de83aa39 saved-history run then completed without application
error: median 25.1ms, p95 210.7ms, maximum 369.6ms versus published 32.8/191.3/228.2ms.
The tail regressed; this pair is not published and no overall gain is claimed.
The subsequent diagnostic main-thread sample found 142 samples through ordinary
arrangement and six through explicit acquisition. Those samples neither identify
acquisition as the cause nor supply call counts or CPU durations.
Explicit complete geometry acquisition remains synchronous.
One uncached custom visual can still render a whole widget within a band; no
renderer deadline or readiness exemption is introduced.
Historical evidence scripts remain at their original source/API scope in Git.

## Requested positions in partial geometry

Ordinary visible arrangement previously required a complete source for every
retained position path. A matching partial source therefore could not supply a
position it already owned: the compositor bypassed the capture/reuse path and
descended again. The same original acquired path relation now carries the actual
requested positions to each ancestor. `SubtreeGeometry.matches` checks placement
first, then requires those positions in its captured geometry. Complete sources
also own absent answers; partial logical/invisible membership does not establish
a position. Missing positions use the original acquisition path, and the new
partial source can supply them on the next unchanged frame. Full capture still
requires complete scope; held-source, revision, internal scroll, clip and layer
checks remain intact.

Source projection intersects those requests with its original immutable geometry
membership before routing them through borrowed children. It preserves original
ordinals, captured ancestry and last-assignment ordering, without scanning every
unrelated global request in every child source. The synchronous ancestor relation
still walks each requested target's path; this change does not remove that work
or make partial placed geometry translatable.

One affected real native App check passed (0.64s): 100 rows, acquired and missing
offscreen targets, changing target membership, scroll/reversal and a child height
write. Every phase compares actual published geometry and rendered strips with
the original uncached compositor. An already covered partial source is reused;
a missing target is acquired before reuse, and that partial source still refuses
complete capture. This is geometry/paint confirmation, not saved-history latency
acceptance. The next affected saved-history run belongs to Parent; no installed
or public change is made here. Raw control output and the original Package
before/after consumer census are retained beside this file.
