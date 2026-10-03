# Initial registration style lifetime

App._register currently completes descendant styling and notification before
applying their parent's initial rules. Styles._update_rules then publishes the
parent mutation through DOMNode._update_inherited_geometry, retiring resources
that those descendant notifications just acquired. Complete attachment and
default CSS collection also finish after some initial notifications.

Keep the algorithm on App._register. Attach the complete incoming native tree,
apply initial rules with ancestors first, then notify and start messages in the
existing descendant/group order. Preserve sibling insertion, original hooks,
positional selectors, virtual components and ordinary later invalidation. No new
cache, state flag, registry, owner type or alternate stylesheet path.

Heisenberg granted this native registration/style family. Frozen PR41 c4e5fd22
and its joined 393 recording remain unchanged. This draft is stacked on PR41
until that checkpoint lands. Existing NRA Package parsed all 249 native and 289
Toad production modules without omissions; actual dynamic receiver/MRO requires
semantic reading. No Toad registration override was found.

Source implementation precedes one batched affected native sanity check and the
next joined installed journey. Registration is an observed source path, not a
measured dominant CPU share. This does not close IRC End or scrolling smoothness.
