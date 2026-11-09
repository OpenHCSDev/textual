from textual.app import App
from textual import events
from textual import on


class NotifyWithInlineLinkApp(App):
    @on(events.Mount)
    def on_mount(self) -> None:
        self.notify("Click [@click=bell]here[/] for the bell sound.")


if __name__ == "__main__":
    app = NotifyWithInlineLinkApp()
    app.run()
