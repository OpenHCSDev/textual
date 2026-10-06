# Position readers acquire their original path

Physical05 records a 96.39ms full arrangement from TextArea Undo's cursor-region
lookup. That is a position request, not a request to enumerate all descendants.
The recording does not retain the queried widget or explain its viewport miss;
no whole-journey timing reduction is claimed.

Compositor already owns committed scene selection, retained ancestry paths and
explicit complete layout. Two position decisions were competing with it:
completeness invalidation rejected committed full-map coordinates, and missing
positions/membership forced full_map even though only one widget was requested.

Published positions now derive directly from the same original _published_map
used by paint/hit layers. A missing position uses original reflow_visible with
the requested ancestry and existing scene members retained. Membership consumes
that same position acquisition. Explicit full_map enumeration still arranges all
descendants. Recursive measurement and scoped capture keep their original rules.
No additional map, cache, target registry, readiness rule or timer is introduced.

Native layout, scroll, hide/prune/reparent and mutation/capture consumers were
read before editing. Existing Package parsed 249 native production modules,
464 tests and 288 read-only Toad modules, zero omissions; before.json records
881 lexical sites. External dynamic consumers are not exhaustively resolved.
Toad and original Physical05 helpers/footage are unchanged.

Source checkpoint; changed reader/Undo/geometry qualification is pending.
No installed package, native artifact, saved source, provider or physical run.
