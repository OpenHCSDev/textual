# Shared message-pump task lifetime

Native73 left a real-entry cycle: run_test installed App._task, while run_async
entered App's replacement _process_messages with no task enrollment. A routed
pointer's completion could then bubble into its waiting App queue.

MessagePump._process_messages now owns actual task acquisition and release for
both App entrypoints and scheduled widget pumps. App supplies its existing startup
body through _process_messages_body. The test launcher retains only its local join
handle; Screen no longer clears task custody during its exit hook. Widget scheduling
still enrolls the original task before its coroutine starts, and never reinstalls
an eager task which has already completed. Timer/Worker/Markdown tasks are distinct
resources and stay with their original owners.

Original pointer completion, driver coroutine admission, capture, queues, shutdown
and selection boundaries are unchanged. No missing-task fallback or new queue,
timer, Toad override or completion exemption is added. App's duplicate body context
was removed; the shared lifetime borrows its existing polymorphic _context.

Existing refactor-audit Package parsed 249 native production and 462 test modules,
zero omissions. before.json groups all 1286 lexical task/lifetime/entrypoint sites
by source coordinates. Dynamic external subclasses remain unresolved explicitly.

Source checkpoint. Next qualification is actual run_async/HeadlessDriver FIFO
press/move/release/wheel with bubbling to App, plus terminal task release. The old
33 native73 controls and closed physical03 are not rerun. No installed, physical,
provider, package or public runtime operation is authorized by this checkpoint.
