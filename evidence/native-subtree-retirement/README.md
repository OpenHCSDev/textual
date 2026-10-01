# Native subtree retirement resource checkpoint

Heisenberg owns this narrow original Compositor retirement method under Toad275
whole foreground/TC1/T9 integration. Base Textual main ce9aa336 (merged17).
Parent's frozen S2/274/271 receiving stage is independent; do not silently
substitute this uninstalled source checkpoint into that package.

## Original relation and all consumers

`Screen._forget_pruned_widgets` calls the original `Compositor.discard_widgets` for
native prune/unregister. That method cleared every bounded subtree geometry
entry, including entries which own none of the retired widgets. This discards
warm native scene resources during unrelated body retirement. Same-run271
physical stacks show recursive arrangement during scrolling and A return;
those stacks do not establish the portion of CPU caused by this invalidation.

The existing compositor cache is the sole owner. Its entry is now one frozen
`SubtreeGeometry` resource with the original key, a read-only geometry mapping,
native members and invisible members. The dictionary key owns root identity;
the resource receives it when checking retirement rather than copying it.
`matches`, `restore_into` and `references_retired` own the original operations.
Creation, reuse and disposal all use this record; every cached[0..3] reader and
four-slot tuple declaration is deleted. Evict entries whose own resources
intersect the retired widgets; preserve other entries.
No second cache, timer, readiness flag or source/model/turn authority is added.
Native geometry keys/epochs, clips, damage, capacity and Screen-close clearing
retain their original owners. Screen retirement consumers inherit the change;
none retains its own widget/retirement catalog. A new native widget subclass
needs zero consumer edits because cached membership comes from arrangement.

Relevant ownership patterns: IDEN-7 (invalidation wider than retirement),
IMPL-13 (one resource mechanism) and TIME-1 (replace broad invalidation in place).
Production versus main: nine lines deleted, thirty-four added in one existing
file, including the record and complete producer/consumer migration. The
initial selective-eviction-only checkpoint was one deleted/five added; it is
superseded by the typed resource closure in this same draft.

## Actual native source control

Run with the existing normal installed271 Python; baseline uses installed
Textual4e9016. Candidate `--source-root` explicitly loads this source package.
This is development-source verification, not an installed Toad gate.

```
python evidence/native-subtree-retirement/actual_native_retirement_control.py baseline.json
python evidence/native-subtree-retirement/actual_native_retirement_control.py --source-root "$PWD" candidate.json
```

Real native App/VerticalGroup/Static mount, removal, reflow and terminal strips;
no model/agent/source fixture or mocked compositor. Baseline preserves correct
paint and releases removed scene custody but loses the unrelated cache entry.
Candidate passes the unchanged assertions before/after reflow: unrelated entry
identity retained, affected entry evicted, live sibling paint present, retired
text absent and no retired widget referenced by a retained cache entry.
Both cases shut down their native App. Source control finishes in less than1s.

The typed-resource control additionally verifies restored and content-updated
scenes equal uncached arrangements, content mutation invalidates the existing
entry, and zero capacity releases all entries. Native behavior assertions are
preserved while custody queries migrate to the one record's contract. No old
tuple reader or type-dispatch format fallback remains. Existing Textual budget
tests and Toad capture/pilot consumers inspect only cache count/keys, so their
contracts remain unchanged. Full-file and seven changed qualified-function
ratchets pass in `typed-resource-ratchet.json`.

## Remaining acceptance

Before Ready/activation, verify the affected normal immutable installed owner
and one meaningful saved-history physical A/B/A/held scroll/End/idle workflow
when parent assigns a coherent receiving prefix. Preserve the original271
raw trace and negative gates; do not repeat an unchanged provider/capture or
claim global CPU/sub50ms firstpaint/Strip reuse from native resource identity.
Absolute region/clip changes still invalidate geometry during scrolling and
remain in275. All original whole-workspace scope stays with Heisenberg.
