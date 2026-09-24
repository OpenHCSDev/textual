"""Terminal-write callbacks acknowledge the write and flush, in order."""

from io import StringIO
from threading import Event

from textual.drivers._writer_thread import WriterThread


class RecordingOutput(StringIO):
    def __init__(self):
        super().__init__()
        self.events = []

    def write(self, text):
        self.events.append(("write", text))
        return super().write(text)

    def flush(self):
        self.events.append(("flush", self.getvalue()))
        return super().flush()


def test_callback_follows_all_earlier_writes_and_flush():
    output = RecordingOutput()
    writer = WriterThread(output)
    done = Event()
    writer.start()
    try:
        writer.write("opening")
        writer.write(" frame")
        writer.call_after_flush(lambda: (output.events.append(("callback", output.getvalue())), done.set()))
        assert done.wait(2), "Writer did not acknowledge its flush"
        assert output.events.index(("flush", "opening frame")) < output.events.index(("callback", "opening frame"))
    finally:
        writer.stop()
