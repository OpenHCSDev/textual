# Callback binding and original arity

The existing `count_parameters` owner serves `invoke` and reactive watchers.
Python bound methods expose attributes on their original function. Storing a
bound arity there therefore makes later unbound counts wrong; looking up that
hint before deriving binding also makes bound counts wrong when the unbound
function was counted first. Partial counting bypasses the underlying owner.

This independent API correction will keep the existing function hint as raw
arity, derive binding before reading it, and derive partial arity through the
same original owner. No new cache, callable wrapper or state owner is needed.
Source reasoning and complete consumer migration precede the final affected
controls. Native viewport projection PR63 stays frozen and independent.

The claim that every repeated bound count inspects its signature was incorrect:
CPython's method attribute lookup delegates to the original function. That
performance claim is withdrawn. No frame-time gain is claimed here.
