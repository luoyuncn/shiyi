"""Status bar widget — token stats, message count, latency"""
from textual.widget import Widget
from textual.reactive import reactive
from rich.table import Table
from rich.text import Text


class StatusBar(Widget):
    """Single-line footer status bar."""

    prompt_tokens: reactive[int] = reactive(0)
    completion_tokens: reactive[int] = reactive(0)
    total_tokens: reactive[int] = reactive(0)
    max_tokens: reactive[int] = reactive(128000)
    message_count: reactive[int] = reactive(0)
    latency_ms: reactive[int] = reactive(0)

    def _make_progress_bar(self, used: int, total: int, width: int = 10) -> Text:
        if total <= 0:
            return Text("░" * width, style="#30363d")

        ratio = min(used / total, 1.0)
        filled = int(ratio * width)
        pct = ratio * 100

        if ratio < 0.5:
            bar_style = "#3fb950"
        elif ratio < 0.8:
            bar_style = "#d29922"
        else:
            bar_style = "#f85149"

        bar = Text()
        bar.append("█" * filled, style=bar_style)
        bar.append("░" * (width - filled), style="#30363d")
        bar.append(f" {pct:.1f}%", style=bar_style)
        return bar

    def render(self):
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="right", ratio=1)

        # Token stats
        left = Text()
        left.append(" Tokens: ", style="#8b949e")
        total = self.prompt_tokens + self.completion_tokens
        if total > 0:
            if total >= 1000:
                left.append(f"{total / 1000:.1f}k", style="#c9d1d9")
            else:
                left.append(str(total), style="#c9d1d9")
            left.append(f"/{self.max_tokens // 1000}k ", style="#484f58")
            left.append_text(self._make_progress_bar(total, self.max_tokens))
        else:
            left.append("- ", style="#484f58")

        # Message count
        center = Text()
        center.append(f"消息: {self.message_count}", style="#8b949e")

        # Latency
        right = Text()
        if self.latency_ms > 0:
            right.append(f"延迟: {self.latency_ms}ms", style="#8b949e")
        right.append(" ")

        grid.add_row(left, center, right)
        return grid

    def update_usage(self, prompt_tokens: int, completion_tokens: int):
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens

    def reset_usage(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.message_count = 0
        self.latency_ms = 0
