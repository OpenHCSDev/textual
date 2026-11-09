from textual.app import App
from textual import events
from textual import on


class ScreenApp(App):
    @on(events.Mount)
    def on_mount(self) -> None:
        self.screen.styles.background = "darkblue"
        self.screen.styles.border = ("heavy", "white")


if __name__ == "__main__":
    app = ScreenApp()
    app.run()
