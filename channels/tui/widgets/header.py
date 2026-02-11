"""Header bar widget — brand + session status"""
from textual.widget import Widget
from textual.reactive import reactive
from rich.table import Table
from rich.text import Text


class HeaderBar(Widget):
    """Single-line header: brand on left, status on right."""

    model_name: reactive[str] = reactive("")
    session_id: reactive[str] = reactive("")
    connected: reactive[bool] = reactive(True)

    def render(self):
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="right", ratio=1)

        left = Text()
        # Gemini-style clean header
        left.append("✨ ", style="bold #F4B400") # Sparkle icon
        left.append("ShiYi", style="bold #E3E3E3")
        left.append("  AI Assistant", style="#9AA0A6")

        right = Text()
        if self.model_name:
            right.append(self.model_name, style="#A8C7FA")
            right.append("  •  ", style="#444746")
        if self.session_id:
            right.append(self.session_id[:8], style="#9AA0A6")
            right.append("  •  ", style="#444746")

        status_text = "Online" if self.connected else "Offline"
        status_color = "#3fb950" if self.connected else "#f85149"
        right.append("● ", style=status_color)
        right.append(status_text, style="#9AA0A6")

        grid.add_row(left, right)
        return grid
