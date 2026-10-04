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
