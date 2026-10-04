# Native style cohorts preserve one publication and declared repaint intent

Source first: DOM.set_styles keyword updates loop over native descriptors inside
Styles.batch_update. That owner batches pending damage, deliberately preserving
immediate rule mutation. Each field still publishes through Styles._update_rules,
DOM._style_rules_updated and subtree/ancestor measurement retirement. Sidebar
width/min/max belong to one requested width cohort; independent publication is
unnecessary. Existing Styles.replace_rules already prepares all native descriptor
values through their MRO and publishes one changed cohort plus declared effects.
Use that existing owner for the keyword API; preserve raw imperative setters and
CSS parse/merge boundary. No replacement transaction/schema/queue/type/registry.

Styles._refresh aggregates request layout/children/parent effects but drops node
repaint, calling Widget.refresh defaultTrue. OffsetProperty explicitly requests
repaintFalse. Pass the existing aggregate to original Widget.refresh; retain actual
geometry/measurement source retirement and normal layout damage/paint. No source
value is treated as a mirror of a layout or presentation event.

Same WT on new branch stacked on frozen52; no native52 source modification,
Toad/Sash/sidebar files, environment/native copy, installed write/provider/movie.
Heisenberg owns Toad controls/runway and next single changed drag/scroll journey.
NRA AST complete native/Toad/tools before editing; semantic source reading of
native descriptor normalization/publication/refresh and every API consumer.
Coherent implementation then one bounded affected native batch LAST; next joined
installed original drag/scroll must qualify the user report. Existing51/52 source
cannot itself prove LIVE419/Text50 fixed. No causal CPU/smoothness/144Hz claim.

## Source checkpoint and final controls

Production `f30daa40c3` relative frozen52: two files, **7 added/9 deleted**.
The keyword loop is replaced by one call to existing replace_rules; its temporary
input is original rules plus requested keyword updates. Styles preserves original
request repaint. The original raw setter/batch interruption contract remains;
invalid keyword cohorts now publish nothing, following existing replacement
normalization. The old interrupted-keyword control was migrated to exercise the
original imperative batch it described; the new cohort control verifies rejection
without partial live writes.

Final affected batch: **116 passed in 2.42s**, original App/Widgets/native geometry
and cached rows, no substituted UI/protocol/state responses. It covers width/
min/max/offset cohort publication once, normalized no-op, clear/defaults, invalid
cohort atomicity, display publication, offset-only geometry/hit movement retaining
rendered row identity, CSS normalization/MRO, inheritance and interrupted imperative
damage. No failed final controls or replay. Resource warnings right-sized to one
short process using existing dependencies; no new cap/environment/native copy.

After AST: native249 modules, zero omissions. Before native/Toad/tools160/60/1
lexical sites (249/288/41 modules), zero omissions; dynamic resolution limitation
recorded. No own Toad edits; Heisenberg owns sidebar/Sash/runway consumers.

**Installed qualification remains pending**: one joined actual sidebar width-drag/
scroll and saved-history body motion with Heisenberg. Source controls do not prove
visible drag latency or overall CPU gain. Frozen52 source is carried unchanged.
