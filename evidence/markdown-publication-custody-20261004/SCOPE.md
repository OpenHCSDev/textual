# Markdown publication custody

Native Markdown currently acquires its own document lock but independently chooses global App.batch_update around awaited first-batch replacement and append-block publication. The original Widget.batch context manager already owns widget locking and update batching; native recompose consumes that capability. Markdown bypasses it at both publication sites.

Migrate both native sites to the existing widget-owned batch lifetime. No new hook, class, map, state, timer or root-screen bypass. Default Widget.batch still acquires the original reentrant lock and App batching; ordinary native Markdown retains its existing global atomic publication. Parser preparation remains outside that batch and document source ordering remains under the existing outer lock. Cancellation releases the two original contexts through their existing context managers.

Heisenberg owns the Toad Body/Window source-resource continuation. PreparedConversationMarkdown reaches these native algorithms through its original MeasuredViewportBody + ConversationMarkdown inheritance. Local source publication must retain preceding pixels or a valid pending-body presentation through native remove/mount and width/style changes; no blind no-op override. Generic Widget.recompose is another existing batch consumer and must be covered by the rich body owner. Public Widget.batch semantics are unchanged in this native checkpoint.

Existing refactor-audit Package parses complete native and Toad production roots. Attribute syntax is not dynamic resolution; source sites are read against actual owner/MRO and RLock task-reentrancy. BOUND-2: leaf algorithms must consume the existing batching owner rather than reach past it. This checkpoint enables that owner relationship, not a demonstrated stall/CPU improvement. No physical/performance readiness claim.

Source reasoning and coherent combined owner implementation precede one final proportionate native/App and affected installed Toad validation. Prior Text58/55 checks and movies are not repeated. No new WT/env/native copy, package access or provider call.
