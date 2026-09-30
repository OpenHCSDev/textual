# Lazy native geometry publication retains old and new damage

Heisenberg owns the compositor contribution to Toad252/254; Kepler owns251
queue/submission state and Einstein the next coherent installed native gate.
Base Textual2e49cb838. One existing production file, 25 lines deleted /15 added.

Actual preserved u02 input-frames106–110: one original accepted input, caption
moves from y38 to37. Frame109 emits Queued at its new row while the old Submitting
row persists until frame110, about27ms later. No second input was accepted.
This receipt establishes a matching canonical producer counterexample, not that
the original u02 call stack invoked full_map at that exact point.

Actual ToadApp/WorkspaceScreen/Prompt/QueueSummary source reproduction (no agent,
ACP/native runner, provider, input or public-root write): changing the caption
and revealing the existing delivery controls normally clears the old caption.
An original compositor.full_map lookup between mutation and timer reflow instead
paints two captions in the first frame. The same lookup with this source paints
one caption in every transition frame. Original red/green logs are retained.
This is run_test/native compositor evidence, not Linux terminal/native acceptance.

Cause: full_map lazily replaces the original visible scene without declaring its
old/new geometry damage. A later reflow sees only the new map and cannot recover
the retired coordinates. Compositor now owns one geometry-damage operation,
inherited by reflow, reflow_visible and lazy full_map publication. Both regions
feed the existing dirty ledger; ordinary clipped partial rendering remains.
No full repaint, caption cache, semantic flags, second map or terminal mirror
is added. IMPL-12: delete two copies of the same damage operation. A new geometry
consumer inherits correct publication rather than patching its local label.

Source repro command from a persistent output directory:
READ_FULL_MAP=1 CAPTION_ARTIFACTS=<owned-output> CAPTION_RECEIPT=candidate
PYTHONPATH=<this-WT>/src:<Toad254-WT>/src:<owned-pyte-target>
<253-frozen-python> actual_toad_caption.py

Next primary acceptance: one new coherent Einstein native/ACP/Linux terminal
Enter journey, idle and busy, proving original input physically visible before
delivery and transferring once to native/chat. Kepler fixes any canonical queue
flow regression independently. Do not replay old u02/c075 inputs or repeat an
unchanged candidate. Current global Textual2e49 is unchanged by this source work.
