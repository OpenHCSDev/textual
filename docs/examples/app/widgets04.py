from textual.app import App
from textual.widgets import Button, Welcome
from textual import events
from textual import on


class WelcomeApp(App):
    @on(events.Key)
    async def on_key(self) -> None:
        await self.mount(Welcome())
        self.query_one(Button).label = "YES!"


if __name__ == "__main__":
    app = WelcomeApp()
    app.run()
