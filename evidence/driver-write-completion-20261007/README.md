# Driver-owned write completion

Driver.call_after_flush schedules its synchronous callback on the original
Driver App loop after its output flush boundary. Synchronous drivers use their
actual flush; queued Linux and Windows writers use the original WriterThread
FIFO signal. The existing signal now carries and publishes onto that loop.
There is no Toad platform decision or ambient-loop wrapper in this capability.

Headless has no output to wait for. Inline flushes its buffered file. Web waits
for complete framed-packet acceptance at its existing OS write boundary; that
boundary now handles partial os.write results. Neither terminal pixels nor
browser paint are acknowledged. Flush/write failures cannot publish success.

Writer shutdown drains prior signals and clears the original driver's writer
custody; later queued-driver submission is refused outside application mode.
A retired App loop receives no completion. Callback exceptions execute under
the App loop's normal exception handling, not on the terminal writer thread.
WriterThread.call_after_flush now requires the original loop explicitly, and
all native consumers including its original control are migrated.

Source checkpoint, not yet qualified. Verification will cover the actual
writer FIFO/flush, owner-loop callback, synchronous file/pipe/headless paths,
closed-loop retirement, and a real source App. Windows console startup cannot
be exercised on this Linux host; its shared writer path is source-reviewed.
No provider, package/prefix/public runtime operation is part of this change.
