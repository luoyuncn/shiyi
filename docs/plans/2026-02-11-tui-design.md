# ShiYi TUI 设计文档

> 日期: 2026-02-11
> 状态: 已确认，待实现

## 概述

为 ShiYi 的 CLI 通道实现基于 Textual 的 TUI 界面，替代当前的 print/input 循环。

**两种运行模式：**
- `shiyi` → 启动 TUI 界面（干净的对话界面）
- `shiyi --debug` → 启动 TUI 界面 + 底部日志面板

## 设计决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 整体风格 | 信息丰富式 | 充分利用终端空间展示有用信息 |
| 侧边栏 | 不要 | 保持界面简洁，信息通过 Header/Footer 展示 |
| 工具调用展示 | 对话流内联折叠块 | 类似 Claude Code，上下文连贯 |
| Debug 日志 | 底部可伸缩面板 | 类似浏览器 DevTools Console |
| Header | 单行状态栏 | FIGlet 占太多空间，单行信息密度更高 |
| 技术栈 | Textual + Rich | Python TUI 首选，async 原生支持 |

## 布局结构

### 标准模式

```
┌─────────────────────────────────────────────┐
│  ✦ ShiYi            DeepSeek-V3 │ a1b2c3 │ ●│  ← Header (1行)
├─────────────────────────────────────────────┤
│                                             │
│  👤 你                                      │
│  帮我搜索一下今天的天气                        │
│                                             │
│  ▸ search_web("今天北京天气")                 │  ← 工具调用折叠块
│                                             │
│  ✦ 十一                                     │
│  今天北京天气晴，气温 **25°C**，适合出行。      │
│                                             │
├─────────────────────────────────────────────┤
│ Tokens: 1.2k/128k ████░░░░ 0.9% │ 12条 │320ms│  ← Footer 状态栏 (1行)
├─────────────────────────────────────────────┤
│ > 输入消息... (/help 查看命令)                │  ← 输入区域
└─────────────────────────────────────────────┘
```

### Debug 模式（多一个日志面板）

```
┌─────────────────────────────────────────────┐
│  ✦ ShiYi            DeepSeek-V3 │ a1b2c3 │ ●│
├─────────────────────────────────────────────┤
│  (对话区域，同上)                             │
├─────────────────────────────────────────────┤
│ Tokens: 1.2k/128k ████░░░░ 0.9% │ 12条 │320ms│
├─ 日志 ──────────────────────────────────────┤
│ 10:23:45 DEBUG core.agent_core   LLM请求发出 │  ← 日志面板 (6-8行)
│ 10:23:46 INFO  tools.registry    执行search   │
│ 10:23:47 DEBUG memory.cache      缓存命中     │
├─────────────────────────────────────────────┤
│ > 输入消息...                                │
└─────────────────────────────────────────────┘
```

## 组件详细设计

### 1. Header (HeaderBar)

固定 1 行，深色背景。

**左侧：** `✦ ShiYi` 品牌标识，加粗高亮
**右侧：** `模型名 │ 会话ID前6位 │ 连接状态`

- 连接状态：`●` 绿色=已连接，红色=断开
- 会话切换时 ID 动态更新

### 2. Chat 对话区域 (ChatView)

占据主体空间，垂直滚动容器。

**消息类型及渲染：**

#### 用户消息
```
👤 你
帮我搜索一下今天的天气
```
- 标签 `👤 你` 使用高亮颜色
- 内容纯文本展示

#### 助手消息
```
✦ 十一
今天北京天气晴，气温 **25°C**，适合出行。
```
- 标签 `✦ 十一` 使用品牌色
- 内容支持完整 Markdown 渲染（Rich Markdown）
- 代码块带语法高亮

#### 工具调用块（折叠/展开）

折叠态：
```
▸ search_web("今天北京天气")
```

展开态：
```
▾ search_web("今天北京天气")
  参数: {"query": "今天北京天气"}
  结果: 北京今日天气：晴，25°C，微风...
  耗时: 1.2s
```

- 可点击切换折叠/展开
- 默认折叠（结果太长时尤其重要）

#### 思考过程面板
```
┌─ 思考中 ──────────────────────────┐
│ 用户想查天气，我需要调用 search_web │
│ 工具来获取实时天气数据...           │
└───────────────────────────────────┘
```
- 带边框的暗色面板，边框颜色使用灰色/暗色调
- 仅当 LLM 返回思考内容时显示

#### 流式输出行为

1. 流式文本逐块追加到当前助手消息
2. 响应完成后进行一次完整的 Markdown 重渲染（确保格式正确）
3. 新消息到达时自动滚动到底部
4. 用户手动向上滚动时暂停自动滚动，底部出现 `↓ 新消息` 提示按钮

### 3. Footer 状态栏 (StatusBar)

固定 1 行，类似 VS Code 底部状态栏。

```
Tokens: 1.2k/128k ████░░░░░░ 0.9%  │  会话消息: 12条  │  延迟: 320ms
```

**字段：**
- **Token 统计**: `已用/上限` + 可视化进度条 + 百分比
  - 进度条颜色：绿色 (<50%) → 黄色 (50-80%) → 红色 (>80%)
- **会话消息数**: 当前会话消息轮数
- **模型延迟**: 最近一次 LLM 首 token 延迟

**数据来源：** 从 AgentCore LLM 响应的 `usage` 字段提取 token 统计。

### 4. 输入区域 (InputArea)

固定 1-3 行，支持多行输入。

**交互规则：**
- `Enter` → 发送消息
- `Shift+Enter` → 换行（多行输入）
- `↑` / `↓` → 翻阅历史命令
- `/` 开头 → 进入命令模式（带自动补全提示）
- 发送时清空输入框，对话区出现用户消息
- 流式响应期间可继续编辑输入，但发送会排队等待

**占位符文字：** `输入消息... (/help 查看命令)`

### 5. 日志面板 (LogPanel) — 仅 Debug 模式

位于 Footer 状态栏下方、输入区上方。

**规格：**
- 默认高度 6-8 行
- `Ctrl+↑` / `Ctrl+↓` 调整面板高度
- 自动滚动到最新日志

**日志级别颜色：**
| 级别 | 颜色 |
|------|------|
| DEBUG | 灰色 |
| INFO | 蓝色 |
| WARNING | 黄色 |
| ERROR | 红色 |

**实现方式：** 自定义 loguru sink → 写入 Textual RichLog widget

**日志格式：**
```
HH:MM:SS LEVEL  module_name  消息内容
```

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+C` | 中断当前 LLM 响应 / 二次按退出 |
| `Ctrl+D` | 退出程序 |
| `Ctrl+L` | 清屏（清除对话显示，不删历史） |
| `Tab` | 命令自动补全 |
| `Ctrl+↑/↓` | 调整日志面板高度（Debug 模式） |

## 斜杠命令

保留现有命令，增加 TUI 相关命令：

| 命令 | 功能 |
|------|------|
| `/new` | 创建新会话 |
| `/list` | 列出所有会话 |
| `/switch <id>` | 切换到指定会话 |
| `/help` | 显示帮助信息 |
| `/clear` | 清屏（同 Ctrl+L） |

## 文件结构

```
channels/
  text_cli_channel.py       ← 保留不动，作为 fallback
  tui/
    __init__.py
    app.py                  ← ShiYiApp(textual.App) 主应用类
    widgets/
      __init__.py
      header.py             ← HeaderBar widget
      chat.py               ← ChatView widget (消息滚动容器)
      message.py            ← MessageBubble widget (单条消息)
      tool_call.py          ← ToolCallBlock widget (可折叠)
      input_area.py         ← InputArea widget (输入框)
      status_bar.py         ← StatusBar widget (Footer)
      log_panel.py          ← LogPanel widget (Debug日志)
    styles/
      theme.tcss            ← Textual CSS 主题样式
```

## 入口变更

### main.py 修改

```python
import argparse

def run():
    parser = argparse.ArgumentParser(description="ShiYi AI Assistant")
    parser.add_argument("--debug", action="store_true", help="启用 debug 日志面板")
    args = parser.parse_args()

    # debug 模式下设置日志级别为 DEBUG
    # 非 debug 模式下抑制终端日志输出（由 TUI 接管）
    # CLI channel enabled → 启动 TUI channel (ShiYiApp)
    # 传入 debug=args.debug 控制日志面板显隐
```

### Orchestrator 集成

```python
# orchestrator.py 中 CLI channel 的启动逻辑：
# if cli_enabled:
#     if tui_mode:
#         channel = ShiYiApp(config, session_manager, agent_core, debug=debug)
#         channel.run()  # Textual App 的 run() 接管事件循环
#     else:
#         channel = TextCLIChannel(config, session_manager, agent_core)
#         await channel.start()
```

注意：Textual App 的 `run()` 会接管 asyncio 事件循环，需要特殊处理与 Orchestrator 的其他 channel 共存。推荐方案：当 TUI 模式时，Orchestrator 在 Textual 的事件循环内启动其他 channel。

## 依赖变更

```toml
# pyproject.toml 新增
dependencies = [
    # ... 现有依赖
    "textual>=0.80.0",
]
```

Rich 不需要单独声明，textual 已包含 rich 作为依赖。

## Token 统计数据流

```
AgentCore.process_message_stream()
  → LLM API 响应包含 usage 字段
  → 新增事件类型: {"type": "usage", "prompt_tokens": N, "completion_tokens": N, "total_tokens": N}
  → StatusBar widget 监听 usage 事件并更新显示
```

需要修改 `AgentCore` 以在流式响应完成后 yield 一个 `usage` 事件。

## 实现优先级

1. **P0 - 基础框架**: App 骨架、布局、Header、输入区域、基本对话渲染
2. **P0 - 核心对话**: 流式输出、Markdown 渲染、消息持久化集成
3. **P1 - 工具调用**: 内联折叠块渲染
4. **P1 - 状态栏**: Token 统计、延迟显示
5. **P1 - Debug 面板**: loguru sink、日志面板
6. **P2 - 交互增强**: 命令补全、历史翻阅、思考过程面板
7. **P2 - 入口集成**: main.py argparse、Orchestrator TUI 启动路径
