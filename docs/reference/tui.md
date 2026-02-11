Role: 资深全栈交互工程师 & TUI 专家 Task: 为通用 AI Agent "ShiYi (十一)" 构建一套高颜值的 TUI (Terminal User Interface) 框架。

Design Philosophy: 参考 Claude Code 与 OpenAI Codex 的视觉风格，追求极简、专业、高性能。架构上需做到逻辑与 UI 彻底解耦，为未来多端接入（SSH, Cloud, Local）打好基础。

Core Requirements:

Header (The Brand): - 使用 FIGlet 或精美的 ASCII Art 渲染 "ShiYi" 艺术 Logo。

右上角展示动态 Session 状态（模型版本、连接延迟、运行环境）。

Main Layout (The Workspace):

Primary Chat: 居中显示，支持 Markdown 流式渲染。

Thought Buffer: 模拟 Claude 的思考过程，使用边框变色的 Panel 隔离 Agent 的推理链。

Side Dashboard (Toggleable): 实时监控 Agent 的工具调用栈 (Tool Call Stack) 和检索到的知识片段 (RAG Context)。

Footer (Session Metadata):

展示当前会话的 Session ID。

展示 Token 消耗实时统计及上下文窗口占用百分比（可视化进度条）。

Interaction:

实现类似 IDE 的命令模式，支持 / 指令。

所有的 UI 组件必须通过 asyncio 异步更新，严禁任何可能阻塞 UI 线程的操作。

Technical Specs:

Language: Python 3.10+

Key Libraries: Textual, Rich, Pydantic (用于状态数据管理)。

Mock Implementation: 包含一个模拟的 ShiYiEngine 类，它能产生带延迟的流式输出和虚拟的 Token 消耗数据。

Constraint: - 不要包含任何特定硬件（如树莓派）的绑定代码，保持环境无关性。

代码注释需清晰，方便后续接入真实的 Agent 后脑。