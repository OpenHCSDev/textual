# Native paint admission during widget batches

Base: Textual `412b5a2b5da8875dc2f3dc5be2365abddce0537b`.

Owner: TC2/PR221 contributor. Heisenberg owns the paired Toad viewport
preparation consumer and integration. No open Textual PR overlaps this scope.

## Confirmed defect

An actual framework App/Screen/Vertical/Label journey mounts a child within
`async with holder.batch()`, requests layout, and yields to the message loop.
The queued Screen compositor refresh runs with App batch count 1, consumes
two dirty rectangles, and passes a ChopsUpdate to App._display, which rejects
it because the batch remains active. Dirty rectangles are then empty.

This is source sanity evidence, not physical terminal acceptance. Earlier
label-update and height-change probes produced no committed dirty rectangles;
those probes did not establish the defect. Mounting a child does.

The actual retained-history recording loses chat history after scrolling.
The earlier claim of lost chrome was wrong: repeated image displays omitted
unchanged pixels. Raw decoded PNG tab/roster/details regions are identical
before and after, including the earlier887 candidate and original baseline.
The batch defect is independently confirmed, but is not established as the
cause of the physical history failure.

## Ownership and scope

Native Screen owns paint admission before preparation or consumption of dirty
regions. A protected preparation hook lets Toad use its existing viewport
owner after admission, deleting its separate atomic-only batch policy.
Batch completion must wake the existing screen refresh mechanism. Existing
after-refresh callbacks must remain queued until a deferred frame can paint.
No new paint registry, geometry cache, source reader or semantic state mirror.

This closes duplicate paint policies with drift (IMPL-12). App's existing
batch count and compositor dirty regions
remain the only authorities.

## Acceptance

Focused actual-framework journey: async widget mount/recompose within a batch;
damage retained while blocked; preparation and after-refresh callbacks deferred;
batch exit paints and releases callbacks without starvation. Paired Toad hook
and existing writer/waiter contracts are reviewed together. Parent/Heisenberg
then performs the sole installed original-history physical journey. No new
capture, provider call or package mutation in this source work.

## Source checkpoint

Actual-framework batch-mount and callback-across-await journeys pass on this
source through the restored Python 3.14 dependency environment. The same
batch-mount journey fails on unchanged installed Textual412 by admitting a
frame during batch 1. Existing call-later and call-after-refresh journeys pass.
No protocol, geometry or UI objects are mocked. These headless checks are
source regression evidence, not physical-terminal acceptance.

The initial pytest run lacked the restored environment's historical
pytest-asyncio extra: four async tests did not execute; the synchronous batch
test passed. That tooling failure is recorded, not counted as a product result.
The async journeys were executed directly with asyncio in the same interpreter.
After restoring that required dev plugin, the original focused pytest command
passed all five tests in 0.34 seconds. No broader repeat was run.

The repaint request on preparation refusal belongs to Screen. Toad deletes
both its compositor wrapper/batch guard and viewport's duplicate write; its
existing resource owner implements only the preparation hook. This preserves
after-refresh waits while queued scroll geometry has not yet reached Screen.

Production diff against Textual412: **18 lines deleted**, 42 added, confined
to `src/textual/screen.py` and `src/textual/app.py`. The callback queue remains
the existing queue; pending refresh is derived from existing scene flags and
dirty sets. Physical original-history acceptance is still outstanding.

## Paired installed counterevidence

The sole actual retained-history capture of Toad4103/Textual650 completed with
clean process custody and 1041 GIL samples, zero reported errors. It still
fails: the chat body becomes blank after End and 15 seconds idle. Static
chrome remains pixel-identical throughout. No Ready/live-fix claim.

The stable idle viewport contains Contents/ContentsGrid but no visible history
or fragments, with zero visible body resources. That points to the current
history geometry/resource relation; it does not establish native ANSI or
compositor corruption. Heisenberg owns that Toad producer/extent investigation.
