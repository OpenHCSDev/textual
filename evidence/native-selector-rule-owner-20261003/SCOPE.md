# Rule declarations own selector matching and specificity

Reuse the existing native checkout after merged45/46; no new environment,
recording, provider or scene/cache/type. Native CSS model/match/stylesheet is
owned here. Heisenberg owns the sole Toad Workspace consumer and next joined
installed workflow.

Source-first complete native/dependency AST and semantic reading found that
DOM query already uses SelectorSet.check correctly. Stylesheet._check_rule
bypasses that owner via _check_selectors; even compound target-only rules scan
the full ancestor path. RuleSet owns selector declarations and specificity.
SelectorSet owns selector matching. Extend those existing owners and delete
_check_selectors/Stylesheet._check_rule and every import/caller together.

SelectorSet.check(node, *, css_path_nodes=None) may borrow the existing original
per-pass path resource for relational matching. It does not retain another path
or answer. Target-only matching keeps live class/pseudo semantics and requires
no ancestry. Stylesheet.apply already acquires the path for its original cache
key and will reuse it; this change does not make each relational rule acquire
another path. RuleSet.check yields declared specificity from matching groups.
Toad Workspace consumes that behavior directly instead of a private stylesheet
checker and eagerly acquired path.

Preserve external TCSS grammar, combinator backtracking/order, custom CSS path,
pseudo classes, mutable parsed selectors, specificity/initial/cascade/cache
semantics. Existing parse owners remain unchanged. No CPU dominance/gain claim:
this removes a confirmed owner bypass and unnecessary matching work, not a
measurement. IMPL-12/13 and BOUND-2 apply to the bypassed owned behavior.

Batch coherent family implementation before final bounded CSS/native-App sanity.
One next meaningful installed UI change supplies physical qualification; no
unchanged45/46/405 gate or new capture. Before/after source evidence records
parse omissions and ambiguous dynamic resolution honestly.
