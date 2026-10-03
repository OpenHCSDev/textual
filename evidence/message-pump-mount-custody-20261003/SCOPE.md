# Registration, composition and remaining foreground work

Follow Text33/Toad364 from the same checkout. Existing MessagePump owns task
startup and Compose/Mount order; App/Widget own synchronous attachment and
style setup; AwaitMount owns completion. Trace the whole caller family before
changing scheduling. No new queue, timer, clock, CSS cache or copied mount flag.
Original04 identifies eager child compose inside App registration before tab
selection; its1.753561s writer gap establishes no speed gain.

Full remaining CPU/raster/firstpaint/cold/warm/runway/velocity/growingEnd/void/
focus/busy/sidebar/animation/TC1/T9/T4 scope remains active with Toad continuation.
144Hz6.944ms is the configurable target, not a checkpoint gate. Source first,
coherent owner implementation and deletion, then one final batched sanity and
changed installed real motion/profile path. Preserve original negatives.

Base is actual main940880 plus accepted Text33 ancestry while that PR is
reviewed. Integrate resulting main normally; no hidden feature-branch base.
Current branch is unqualified WIP, not installed or speed Ready.

## Implemented startup ownership

MessagePump moves its existing cooperative task boundary from AFTER Compose/
Mount to BEFORE preprocessing. No additional yield/timer, task factory change,
queue or startup flag. All native callers inherit it: App._register, virtual
scrollbar App._start_widget, and loading Widget._cover. Caller attachment,
registration and initial styles finish synchronously before child composition
can execute; AwaitMount still waits the same original mounted_event, Compose
still precedes Mount, and prune/unmount still joins the original child tasks.
This also allows _task assignment to finish before child initialization.

Source115 selected references across249 Textual/287 Toad modules,0 omissions;
Kepler independently read exact eager call chain and cancellation ownership.
Task factory eagerly runs _pre_process recursively; former message-loop yield
was too late. Source04 stack shows this exact nested path. Do not cancel child
pumps to solve latency: waiter cancellation does not retire admitted children.
WIP source checkpoint; final batched mount/message/paint checks and installed
changed saved-history motion remain required. No measured speed claim yet.
