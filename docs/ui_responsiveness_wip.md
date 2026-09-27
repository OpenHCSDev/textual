# UI responsiveness framework checkpoint

Draft companion to the OpenHCSDev Toad responsiveness investigation.

- Primary lifetime issue: https://github.com/OpenHCSDev/textual/issues/4
- Filtering: https://github.com/OpenHCSDev/toad/issues/59
- Bounded history/worker views: https://github.com/OpenHCSDev/toad/issues/61
- Animation budget: https://github.com/OpenHCSDev/toad/issues/64

## Structural measurement revision follow-up

The viewport-stutter follow-up exposed a stale intrinsic-size cache during
progressive child admission: a parent could retain a29-row box while its child
already arranged33rows, clipping the tail for one frame. Native `NodeList`
propagates structure/display revisions synchronously, but the box cache previously
waited for the later layout notification. Arrangement and box measurement could
therefore describe different child structures in the same frame.

The box-model revision now includes the existing native child-structure revision.
Obsolete entries are retired through the same cache-generation boundary. There
is no extra ancestor walk, duplicate revision registry or forced full-map layout.
Two deterministic failing-before regressions cover nested admission and native
display-projection changes before idle notification delivery; existing cache tests
retain width reuse and obsolete-generation retirement assertions.

The Toad progressive-tail diagnostic passed six consecutive runs with this fix.
The corrected-environment framework run passed3,442tests (1skip,4xfail) in193.07s,
and six focused scrollbar/Markdown/prune snapshots passed. The framework job peaked
246.5MiB under a4GiB/no-swap limit.
The full80pilot run passed79cases including the prior frame failure; the large
comms case exceeded100s and remains a separate validation limit. Two serial native
candidate runs preserved72actions/52markers and recorded input maxima59.59/69.87ms
versus96.75ms in the matched landed control. Anchor-induced full geometry passes
fell22to0, but loop maxima112.89/124.73ms still miss the overall stutter target.
Validation used one worker with4GiB/no-swap limits; the full Toad job peaked494.2MiB.

## Removal completion and input ingress checkpoint

Native key-route evidence exposed an unrelated teardown barrier: a key entered
the app queue after5ms but waited another86ms before dispatch while widget removal
was being awaited through `App.call_next`. `AwaitRemove` now owns one shared
completion independently of the receiver's message pump. The app observes that
receipt only once it is done. Explicit waiters still wait for actual removal and
publication; cancelling a waiter cannot cancel node teardown or its final callback.
Self-removal retains its non-deadlocking semantics. Completed receipts release the
removed tasks, callback and task context instead of retaining the retired tree.

This also removes duplicate post-removal callbacks when both the caller and the
automatic receiver await the same receipt. Four failing-before regressions cover
input blocked by a held unmount, duplicate publication, cancellation propagation
and retired widgets retained by a completed receipt. Further tests cover async
publication cancellation, error replay and self-removal.

Driver ingress directly schedules the declared `App.post_message` operation on
its owning event loop. The previous coroutine adapter only called that method,
but added an unused cross-thread Future and an extra loop turn before enqueueing.
Tests verify one-handoff ordering and native bindings/focus/paste behavior.

Current full verification: **3,440 passed,1skipped,4xfailed** excluding snapshots;
**56 Toad pilots passed**. The focused native prune snapshot also passes.
Two serial unprofiled native runs completed all72actions/52typed markers:
input median24.56/29.42ms, p9554.36/49.04ms, maximum93.90/59.98ms. The earlier
published candidate's maximum was143.68ms. These are improved input-tail receipts,
not universal sub50ms acceptance: loop maxima remain121.48/103.23ms, including
roughly100ms sidebar layout+paint and62ms collections. Keep both repeated results.

## Declaration-bound dispatch checkpoint

`SelectorSet.check` owns target-only query matching. Single selectors and compound
selectors whose terms all apply to the target call the existing selector checks
directly. Relational selectors still use the existing interpreter and authoritative
CSS ancestry. This removes unnecessary ancestor-path allocation without caching
dynamic matches or adding widget-specific cases.

Reactive access now follows the same declaration-owned approach. At class
construction, `DOMNode` resolves each reactive to stored or computed access using
the concrete class's declarations. The descriptor directly calls that accessor on
reads, writes and recomputation. Stored reads do not rediscover compute methods or
recheck constructor readiness. Computed access preserves ordinary Python method
overrides; class metadata retains neither widgets nor bound instance callbacks.
Cold lazy initialization retains missing-constructor diagnostics and factory/
`Initialize` semantics. A private compute method introduced for an inherited
reactive is now correctly bound; a failing-before regression covers that bug.

Current checks: **3,431 passed, 1 skipped, 4 xfailed** excluding snapshots, and
**56 companion Toad pilots passed**. Thirteen selector tests cover old-interpreter
parity, custom ancestry, dynamic classes, inherited disabled state, focus and
elimination of unnecessary path construction. Six reactive access tests cover
probe-free reads, public/private inheritance, override dispatch, lazy defaults,
raw values, exception propagation and constructor diagnostics.

A focused sidebar action profile recorded **38,255 →1,972 total `hasattr` calls**;
reactive reads contributed **34,074 →0**. For roughly11.4k reads, cumulative
profiled reactive-get time fell from about36ms to8ms. This is a profiling result,
not an end-to-end timing claim. The latest unprofiled native filter workload
completed72actions and52typed markers, but input median42.63/p9595.47/
maximum143.68ms still misses the universal sub50ms target. Remaining layout,
paint, allocation/GC and consecutive-frame queue latency need further work.

## Included work

1. Reactive subscribers unregister watches from quiet publishers on close,
   cancellation and terminal message-pump cleanup. Reverse publisher ownership
   is weak. A real aged process had 2,268 closed FooterKey subscribers retained
   through Footer.compact; focused reproductions fail before this cleanup.
2. Optional DOM/message storage is lazy; immutable selector names are class
   metadata. Unused message signals are not allocated during dispatch, and a
   processed message is released before an idle queue wait.
3. Stopped/completed timers release callbacks/tasks. Closed widget/screen
   presentation state and compositor roots are cleared at their owning lifetime.
4. Box-model caches retire obsolete measurement revisions.
5. Viewport layout can retain declared anchor geometry paths without walking
   unrelated offscreen descendants. `_layout_geometry_targets()` is the screen
   declaration used by the application.
6. `_measured_virtual_size_requires_layout()` distinguishes committed layout
   output from an authored measurement input. Child-derived containers, including
   scrolling containers, no longer invalidate ancestor measurements merely for
   committing their extent. Watchers, authored changes and scrollbar visibility
   changes still invalidate normally. Custom extent-input widgets may override
   the hook.
7. `Stylesheet.is_local_display_class()` derives a conservative invalidation
   scope from parsed rules. Ordinary class mutation is unchanged; an application
   may opt into a node-local display update only when the declaration proves it
   safe. Descendant/custom/inherited rules force the normal subtree path.
8. `DOMNode.set_display_constraint(reason, allowed)` composes independent model
   visibility restrictions with the current authored CSS display value. Native
   displayed-child projections and layout are invalidated without restyling the
   subtree. Relative-child measurement observes the same effective display.
   `Stylesheet.references_class()` derives marker dependencies from parsed rules,
   including compound/ancestor selectors and source replacement/reparse.

## Structural follow-up

This draft includes the following structural changes. The companion Toad branch
pins this framework checkpoint. Correctness receipts do not establish latency targets.

- Removal retires parent arrangement and StreamLayout placements, inactive
  compositor maps, layer projections and pending widget invalidations. A native
  ownership reproduction failed against the previous source. Closed subscribers
  alone were not a sufficient lifetime check.
- Acyclic LRU storage releases acyclic payloads when the cache owner is dropped.
- Sparse horizontal exposure avoids painting covered parent backgrounds.
- Focus invalidation follows declaration targets; inherited paint is invalidated
  through style owners. Unchanged non-transition rules avoid animated rule-graph
  construction. Declared transitions still reconcile pending targets even when
  their current values are equal, including delayed transitions.
- Native layout and full-repaint intent commit in one frame. Content height
  measurement counts wrapping boundaries without constructing formatted lines.
- Screen resolution observes weak topology ownership. Optional inactive-scene
  presentation retirement is available but was not enabled in Toad after its
  cold-remeasurement tradeoff was measured.
- Opt-in subtree geometry reuse has a validated, configurable entry budget:
  `Compositor.max_subtree_geometry_entries` and
  `Screen.SUBTREE_GEOMETRY_CACHE_ENTRIES`. Zero disables it; the default64 is a
  heuristic, not a formal working-set bound.
- Inherited paint uses immutable data-only `PaintState` records. Style mutations
  and native topology changes own its validation epoch, avoiding repeated
  ancestor walks between mutations. Custom ancestry bypasses epoch reuse;
  ancestor collection and move/reset/merge/clear cases retain native behavior.
  The record uses NamedTuple to preserve Python3.9 compatibility.
- Footer consumes `Screen.active_bindings` through an immutable display
  projection. Repeated notifications coalesce; compatible native FooterKeys are
  updated/reordered rather than rebuilt. Reconciliation shares the native
  recompose transaction, checks retirement after awaits, and reschedules changed
  revisions. Keys still simulate native key events, so dispatch observes the
  current owner and keymap rather than a captured callback.

## Verification

Published checkpoint suite excluding snapshot tests: **3,412 passed, 1 skipped,
4 xfailed** with
`pytest tests --ignore=tests/snapshot_tests -q -n 2`.
Focused footer/scrollbar/opacity visual snapshots: **25 passed**. The companion
Toad pilot suite passed **52 cases** before the final transition regression and
NamedTuple compatibility cleanup; focused framework tests and the final full
framework suite cover those later changes.
The reactive lifetime fixture was also rerun after correcting its callback
closure construction: all five cases passed. Scoped Ruff and whitespace checks
pass. Tests cover weak publisher lifetime, live-watch preservation, real Footer
churn, lazy-storage independence, timer lifetime, cache generations, viewport
geometry/render parity, and class-scope invalidation after CSS edits.
Display-constraint tests cover independent reasons, CSS changes while hidden,
pre-mount restrictions, relative measurement, and native layout without CSS work.

The Toad branch contains the interaction runners, live profiler/DTO capture,
headless replay, source receipts, and evidence audit. Raw real-session captures
are private local artifacts, not repository fixtures.

## Still open

This checkpoint does not establish the target frame rate. The target is 16.7 ms
steady-state animation work at 60 Hz with responsive input during filtering and
loading. Whole-transcript/live-block scaling, remaining GC/render work, and
clean repeated real-terminal acceptance still need work. Passing correctness
tests or headless settlement is not proof of smooth UI performance.

The pre-async-activation native navigation workload completed83actions, including ten
tabs, resize, scrolling and selection. It still had a189.7ms maximum loop gap
and139.8ms GC pause; target-mode flush medians were696.2ms for opening and169.3ms
for switching. The four-thread/all-seven-filter run applied all52markers but
input acknowledgment still reached134.9ms. These are performance failures.

The subsequent Toad async-activation follow-up recorded loading-frame flush
median53.52/max62.59ms and switching median55.09/max105.18ms. Input/GC tails still
miss the universal sub50ms goal; see the companion Toad tracking plan for the
separate loading, final-shell and content-ready receipts.
