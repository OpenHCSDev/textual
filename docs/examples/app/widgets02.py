from textual.app import App
from textual.widgets import Welcome
from textual import events
from textual import on
from textual.widgets import Button


class WelcomeApp(App):
    @on(events.Key)
    def on_key(self) -> None:
        self.mount(Welcome())

    @on(Button.Pressed)
    def on_button_pressed(self) -> None:
        self.exit()


if __name__ == "__main__":
    app = WelcomeApp()
    app.run()
