# Native style mutation and layout request have distinct lifetimes

Source: Styles._update_rules commits authored inputs, then DOMNode._style_rules_updated
retires descendant measurements and ancestor geometry through the original hooks.
Styles._refresh then calls Widget.refresh(layout=True), which treats the request
as another source mutation and runs _invalidate_layout/_measurement_updated again.
Raw style writes must remain synchronous source invalidation without unsolicited
refresh; imperative content refresh must still invalidate before an await.

Use the existing style-notification / Widget layout publication family to carry
already-published style requests. Keep source mutation owned by Styles and ordinary
Widget input mutation owned by its current public refresh contract. Delete repeated
retirement from style scheduling, not legitimate layout or actual content writes in
leaf notify hooks. All native and Toad overrides/callers must migrate coherently;
no new mirror, cache, flag, typed wrapper, scene map, timer or alternate renderer.
Public/custom override contracts require explicit source review before selecting a
hook signature; a new keyword cannot silently break existing subclass hooks.

Native ownership: Widget/DOM style-to-layout scheduling, Styles notification callers,
original native widget overrides. Heisenberg owns Toad source/admission/preparation/
paint/retirement and its eight style-notification overrides; coordinate the exact
shared boundary directly. No edits to his worktree. Native52/53 source and installed
qualification stay frozen on main and are not a performance finish line.

Current main c1c1ebe5; existing NRA Package complete native249 and Toad288 parsed with
zero omissions. Source activation from original422 is not CPU dominance or a latency
measurement. Read all declarations, writes and hooks before implementation. Coherent
family implementation first; affected controls and one changed installed user path
last with the workflow owner. No old film, new worktree/environment/native copy or
parallel measurement project. Full structural UI responsiveness remains active.
