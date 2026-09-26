# UI responsiveness framework checkpoint

Draft companion to the OpenHCSDev Toad responsiveness investigation.

- Primary lifetime issue: https://github.com/OpenHCSDev/textual/issues/4
- Filtering: https://github.com/OpenHCSDev/toad/issues/59
- Bounded history/worker views: https://github.com/OpenHCSDev/toad/issues/61
- Animation budget: https://github.com/OpenHCSDev/toad/issues/64

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
6. `_measured_virtual_size_requires_layout()` preserves the default feedback
   policy while allowing content-derived containers to declare their measured
   extent as an output. Watchers, authored changes and scrollbar invalidation
   remain normal.
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

## Verification

Full suite excluding snapshot tests: **3,132 passed, 1 skipped, 4 xfailed** with
`pytest tests --ignore=tests/snapshot_tests -q -n 2`.
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
