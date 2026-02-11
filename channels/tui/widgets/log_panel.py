"""Debug log panel widget"""
from textual.containers import Vertical
from textual.widgets import Static, RichLog


class LogPanel(Vertical):
    """Bottom log panel for debug mode — shows loguru output."""

    def compose(self):
        yield Static(" 日志", classes="log-title")
        yield RichLog(highlight=True, markup=True, wrap=True, id="log-output")

    def write_log(self, formatted_message: str):
        try:
            log_output = self.query_one("#log-output", RichLog)
            log_output.write(formatted_message.strip())
        except Exception:
            pass

    def write_rich(self, renderable):
        try:
            log_output = self.query_one("#log-output", RichLog)
            log_output.write(renderable)
        except Exception:
            pass
