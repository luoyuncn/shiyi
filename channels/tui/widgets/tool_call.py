"""Tool call collapsible block widget"""
import json

from textual.widgets import Collapsible, Static


class ToolCallBlock(Collapsible):
    """Inline collapsible block showing a tool call and its result."""

    def __init__(self, tool_name: str, args: dict, **kwargs):
        self.tool_name = tool_name
        self.tool_args = args

        args_preview = self._format_args_preview(args)
        title = f"⚡ {tool_name}({args_preview})"

        self._detail_widget = Static("⏳ 执行中...", classes="tool-detail")
        super().__init__(self._detail_widget, title=title, collapsed=True, **kwargs)

    def _format_args_preview(self, args: dict) -> str:
        if not args:
            return ""
        parts = []
        for k, v in args.items():
            s = json.dumps(v, ensure_ascii=False)
            if len(s) > 30:
                s = s[:27] + "..."
            parts.append(s)
        return ", ".join(parts)

    def set_result(self, result: str, elapsed: float = 0):
        detail_lines = []

        if self.tool_args:
            detail_lines.append(
                f"参数: {json.dumps(self.tool_args, ensure_ascii=False, indent=2)}"
            )

        # Truncate long results
        display_result = result
        if len(display_result) > 500:
            display_result = display_result[:500] + "\n... (已截断)"
        detail_lines.append(f"结果: {display_result}")

        if elapsed > 0:
            detail_lines.append(f"耗时: {elapsed:.1f}s")

        self._detail_widget.update("\n".join(detail_lines))
