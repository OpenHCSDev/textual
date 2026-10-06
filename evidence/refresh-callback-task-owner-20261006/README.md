# Refresh callback execution belongs to its sender

Screen retained each callback with its sender, checked that sender's paint, then
awaited the callback on Screen's task inside the sender's context. An async
callback could wait for its sender's next refresh: wait_for_refresh saw a foreign
task, queued another Screen callback, and waited while Screen was still awaiting
the first callback. One async widget callback could also prevent unrelated
senders' paint and callback admission.

Screen now owns admission only. It hands each admitted callback to the sender's
existing call_later / events.Callback / on_callback path. That original pump owns
execution, self-wait refusal, errors and teardown. No new task or queue is added.
Held callbacks remain in Screen's same queue; the original subtree, whole-frame,
batch and backdrop checks remain. One synchronous drain borrows one preparation
cohort; the repeated preparation and foreign callback context/invocation were
deleted. No preparation is acquired for an empty or batched callback queue.

Existing Package parser covered 249 native production modules, 463 native tests
and 288 Toad dependency modules with zero omissions. before.json records 208
lexical declaration/consumer sites. External dynamic callback targets remain
unresolved. Toad sources were read, not edited.

This source defect is not established as physical04's cause. The original footage
shows saved transcript paint. A callback held behind native readiness does not
itself suppress the capture helper's independent asyncio timeout; its missing
DTO/error still needs Parent's helper trace. Original recordings, helpers,+wheels and failed capture remain unchanged.

Changed-path qualification is pending. No installed, physical or provider run.
