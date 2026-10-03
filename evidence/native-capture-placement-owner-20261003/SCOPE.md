# Use the original capture placement for native geometry queries

Extend existing Compositor geometry acquisition; no new type, map, cache, flag,
scene, environment or recording. Parent granted `_get_geometry`/`get_offset`;
Heisenberg owns the independent Toad body/writer family and its physical recorder.
Reuse this checkout after normal main integration; keep scoped44 frozen.

Existing capture geometry already declares placements for its admitted members.
`_get_geometry` should consume those placements before constructing an ancestor
list. Only missing queries need the original ancestry relation to refuse an
omitted capture descendant; unrelated queries keep ordinary scene selection.
`get_offset` currently bypasses this behavior and independently chooses visible
or lazy full geometry. Delete that algorithm: offset derives from `find_widget`.
Screen and Widget geometry readers consume the same original placement owner.
Ordinary missing geometry retains lazy arrangement; no capture descendant may
escape to another scene. Nested/failed synchronous captures restore custody.

Read original `_arrange_root`, cover/scrollbar geometry, Intrinsic/Placed resources,
DOM ancestry, Widget region/content/size, StylesCache rendering, Screen public
geometry methods and the Toad capture caller. NRA Package parsed all249 native
and289 Toad production modules with no omissions at the production-equal frozen
source; targeted before/after owner evidence records consumer closure. AST does
not resolve all dynamic overrides or external plugin calls; those retain the
public geometry contract and need semantic reading.

Source reasoning and coherent implementation come first. One final bounded native
batch must detect omitted-child fallback, wrong external-scene selection, offset
bypassing capture, and failure/nesting leakage; use the actual native App. One
later changed installed journey belongs to Heisenberg and joins useful changed
source. No repeat44 tests/film, test-first design, provider call, overlay or new
capture. This removes repeated work and a competing selector, not a measured
CPU share or a smoothness claim.
