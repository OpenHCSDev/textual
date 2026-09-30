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

The actual retained-history terminal recording also loses chrome and history
after scrolling; a subsequent SVG export recovers some chrome. The batch
defect is an independently confirmed candidate cause, not yet proof of the
entire physical failure.

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

The repaint request on preparation refusal belongs to Screen. Toad deletes
both its compositor wrapper/batch guard and viewport's duplicate write; its
existing resource owner implements only the preparation hook. This preserves
after-refresh waits while queued scroll geometry has not yet reached Screen.
