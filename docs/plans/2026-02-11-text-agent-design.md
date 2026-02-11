# ShiYiBot 文字版 Agent 系统设计

**设计日期**: 2026-02-11
**目标**: 在现有语音版基础上，扩展支持文字输入输出，构建多通道、多Agent协作的智能助理系统

---

## 目录

- [1. 整体架构](#1-整体架构)
- [2. 目录结构](#2-目录结构)
- [3. 设计模式](#3-设计模式)
- [4. 数据流和交互流程](#4-数据流和交互流程)
- [5. 技术选型](#5-技术选型)
- [6. 核心组件设计](#6-核心组件设计)
- [7. 工具系统](#7-工具系统)
- [8. 子Agent系统](#8-子agent系统)
- [9. 记忆系统](#9-记忆系统)
- [10. 配置文件](#10-配置文件)
- [11. 启动流程](#11-启动流程)
- [12. 实施路线图](#12-实施路线图)
- [13. 测试策略](#13-测试策略)

---

## 1. 整体架构

### 1.1 系统分层架构

```
┌─────────────────────────────────────────────────────┐
│  入口层 (Entry Layer)                                │
│  ├─ main.py (启动orchestrator)                       │
│  ├─ voice_channel.py (语音通道)                      │
│  ├─ text_cli_channel.py (CLI通道)                    │
│  └─ text_api_channel.py (Web API通道)                │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  调度层 (Orchestration Layer)                        │
│  ├─ session_manager.py (会话管理器)                  │
│  └─ orchestrator.py (总调度器)                       │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  Agent层 (Agent Layer)                               │
│  ├─ agent_core.py (主Agent核心)                      │
│  ├─ sub_agents/ (子Agent池)                          │
│  └─ context_manager.py (上下文管理)                  │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  能力层 (Capability Layer)                           │
│  ├─ tools/ (工具系统)                                │
│  │   ├─ registry.py (工具注册器)                     │
│  │   ├─ builtin/ (内置工具)                          │
│  │   └─ mcp_client.py (MCP工具接入)                  │
│  └─ memory/ (记忆系统 - SQLite)                      │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  引擎层 (Engine Layer - 复用现有)                    │
│  ├─ engines/llm/ (LLM引擎)                           │
│  ├─ engines/stt/ (语音专用)                          │
│  └─ engines/tts/ (语音专用)                          │
└─────────────────────────────────────────────────────┘
```

### 1.2 核心理念

1. **通道无关性** - 语音、CLI、API都是输入通道，统一转换为文本流进入Agent层
2. **会话隔离** - 每个会话独立的上下文、历史、状态（单用户多会话模型）
3. **异步优先** - 全异步架构，支持并发处理和流式响应
4. **引擎复用** - 语音版的LLM引擎直接复用，STT/TTS仅语音通道使用

### 1.3 核心概念关系

```
LLM引擎 vs 主Agent:

┌──────────────────────────────────────────┐
│  主Agent (AgentCore)                     │
│  ┌─────────────────────────────────┐   │
│  │ 1. 加载会话历史                  │   │
│  │ 2. 构建prompt（历史+工具定义）    │   │
│  └─────────────────────────────────┘   │
│                  ↓                       │
│  ┌─────────────────────────────────┐   │
│  │ LLM引擎 (纯粹的推理)             │   │
│  │ - 调用DeepSeek API               │   │
│  │ - 返回：文本 或 工具调用请求      │   │
│  └─────────────────────────────────┘   │
│                  ↓                       │
│  ┌─────────────────────────────────┐   │
│  │ 3. 解析响应并执行                │   │
│  │    - 普通文本 → 返回             │   │
│  │    - 工具调用 → 执行工具         │   │
│  │    - 子Agent → 调用子Agent       │   │
│  │ 4. 保存对话历史                  │   │
│  └─────────────────────────────────┘   │
└──────────────────────────────────────────┘
```

**核心关系**: 主Agent = LLM推理 + 工具调用 + 上下文管理 + 记忆管理

---

## 2. 目录结构

### 2.1 新的项目结构

```
shiyi-bot/
├── main.py                          # 主入口（启动orchestrator）
├── config/
│   ├── config.yaml                  # 统一配置
│   └── settings.py                  # 配置加载器
│
├── channels/                        # 🆕 通道层
│   ├── base.py                      # 通道抽象基类
│   ├── voice_channel.py             # 语音通道（包装现有AssistantCore）
│   ├── text_cli_channel.py          # CLI通道
│   └── text_api_channel.py          # Web API通道（FastAPI）
│
├── core/
│   ├── assistant.py                 # 保留：语音版AssistantCore
│   ├── orchestrator.py              # 🆕 总调度器
│   ├── session_manager.py           # 🆕 会话管理器
│   ├── agent_core.py                # 🆕 主Agent核心（LLM推理+工具调用）
│   ├── context_manager.py           # 🆕 上下文管理
│   ├── sentence_splitter.py         # 保留
│   └── state_machine.py             # 保留
│
├── agents/                          # 🆕 子Agent系统
│   ├── base_agent.py                # 子Agent基类
│   ├── registry.py                  # Agent注册器
│   └── builtin/                     # 内置子Agent
│       ├── code_assistant.py        # 代码助手Agent
│       ├── general_qa.py            # 通用问答Agent
│       └── iot_controller.py        # IoT控制Agent（示例）
│
├── tools/                           # 🆕 工具系统
│   ├── base.py                      # 工具基类
│   ├── registry.py                  # 工具注册器
│   ├── mcp_client.py                # MCP协议客户端
│   └── builtin/                     # 内置工具
│       ├── web_search.py            # 网络搜索
│       ├── file_operations.py       # 文件操作
│       └── shell_executor.py        # Shell命令执行
│
├── memory/                          # 🆕 记忆系统
│   ├── storage.py                   # SQLite存储层
│   └── cache.py                     # 内存缓存层
│
├── engines/                         # 保留：现有引擎
│   ├── llm/
│   ├── stt/                         # 仅语音通道使用
│   ├── tts/                         # 仅语音通道使用
│   ├── vad/                         # 仅语音通道使用
│   └── wake_word/                   # 仅语音通道使用
│
├── audio/                           # 保留：音频处理
└── utils/                           # 保留：工具函数
```

### 2.2 关键变化

- **保留现有代码** - `core/assistant.py`、`engines/`、`audio/` 完全保留，确保语音版不受影响
- **新增通道层** - 将语音版包装成一个通道，与CLI/API平行
- **Agent系统独立** - 新建 `agents/` 和 `tools/` 目录，清晰分离职责
- **记忆系统独立** - `memory/` 管理所有持久化和缓存

---

## 3. 设计模式

### 3.1 策略模式 (Strategy Pattern) - 通道层

不同的输入输出策略可互换：

```python
# 抽象策略
class BaseChannel(ABC):
    async def send_to_agent(self, session_id, message):
        async for chunk in agent_core.process_message(session_id, message):
            await self.on_response_chunk(chunk)

    @abstractmethod
    async def on_response_chunk(self, chunk: str):
        pass

# 具体策略1：语音输出
class VoiceChannel(BaseChannel):
    async def on_response_chunk(self, chunk: str):
        await self.sentence_queue.put(chunk)  # TTS

# 具体策略2：文本输出
class TextCLIChannel(BaseChannel):
    async def on_response_chunk(self, chunk: str):
        print(chunk, end='', flush=True)  # 终端

# 具体策略3：API响应
class TextAPIChannel(BaseChannel):
    async def on_response_chunk(self, chunk: str):
        await self.sse_queue.put(chunk)  # SSE推送
```

### 3.2 注册器模式 (Registry Pattern) - 工具和Agent管理

```python
class ToolRegistry:
    _tools: dict[str, Tool] = {}

    @classmethod
    def register(cls, func):
        """装饰器：注册工具"""
        tool = Tool(name=func.__name__, func=func)
        cls._tools[tool.name] = tool
        return func

@ToolRegistry.register
async def search_web(query: str) -> str:
    """搜索网络"""
    return await do_search(query)
```

### 3.3 单例模式 (Singleton) - 全局管理器

```python
class SessionManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._sessions = {}
            cls._instance._storage = MemoryStorage()
        return cls._instance
```

### 3.4 责任链模式 (Chain of Responsibility) - Agent调用链

```python
class AgentCore:
    async def process_message(self, session_id, message):
        # 主Agent先尝试处理
        response = await self.llm_engine.chat(message)

        # 如果需要子Agent
        if response.requires_sub_agent:
            sub_result = await self.invoke_sub_agent(...)
            final = await self.llm_engine.summarize(sub_result)
            return final

        return response
```

### 3.5 适配器模式 (Adapter) - 包装现有语音版

```python
class VoiceChannel(BaseChannel):
    """将现有的AssistantCore适配成通道"""

    def __init__(self, config):
        self.assistant = AssistantCore(config)

    async def start(self):
        await self.assistant.start()
```

### 3.6 模板方法模式 (Template Method) - 工具调用流程

```python
class BaseTool(ABC):
    async def execute(self, **kwargs) -> Any:
        await self.validate_params(kwargs)      # 1. 校验
        result = await self.run(kwargs)          # 2. 执行
        await self.log_execution(kwargs, result) # 3. 日志
        return result

    @abstractmethod
    async def run(self, params: dict) -> Any:
        pass
```

### 3.7 设计模式总结

| 设计模式 | 应用位置 | 作用 |
|---------|---------|------|
| 策略模式 | 通道层 | 不同I/O策略可插拔 |
| 注册器模式 | 工具/Agent系统 | 动态注册和发现 |
| 单例模式 | SessionManager | 全局唯一管理器 |
| 责任链模式 | Agent调用链 | 任务委托和协作 |
| 适配器模式 | VoiceChannel | 包装现有代码 |
| 模板方法模式 | 工具基类 | 统一调用流程 |

---

## 4. 数据流和交互流程

### 4.1 完整请求流程（文字版）

```
┌──────────────┐
│ 用户输入文字  │ (CLI输入 或 API请求)
└──────────────┘
       ↓
┌──────────────────────────────────────────┐
│ 通道层 (TextCLIChannel / TextAPIChannel)  │
│  - 创建/获取session_id                     │
│  - 调用 agent_core.process_message()      │
└──────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────┐
│ SessionManager                            │
│  - 从缓存/SQLite加载会话上下文             │
│  - 返回历史对话                            │
└──────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────┐
│ AgentCore                                 │
│  1. 构建messages = [历史 + 新消息]         │
│  2. 添加工具定义到LLM请求                  │
│  3. 调用 LLM引擎流式推理                   │
└──────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────┐
│ LLM引擎 (OpenAICompatibleEngine)          │
│  - 调用DeepSeek API                       │
│  - 流式返回：文本chunk 或 tool_call        │
└──────────────────────────────────────────┘
       ↓ (如果需要调用工具)
┌──────────────────────────────────────────┐
│ ToolRegistry                              │
│  - 查找工具: search_web, execute_shell... │
│  - 执行工具函数                            │
│  - 返回结果                                │
└──────────────────────────────────────────┘
       ↓ (工具结果返回给LLM继续推理)
┌──────────────────────────────────────────┐
│ AgentCore                                 │
│  - 把工具结果添加到messages                │
│  - 再次调用LLM                             │
│  - 流式返回最终答案                         │
└──────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────┐
│ 通道层接收流式响应                          │
│  - CLI: 打印到终端                          │
│  - API: 推送到客户端                        │
└──────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────┐
│ SessionManager                            │
│  - 异步保存对话历史到SQLite                 │
│  - 检查token长度，触发摘要（如需要）         │
└──────────────────────────────────────────┘
```

### 4.2 多通道并行运行

```
启动时:
main.py → Orchestrator → 并行启动所有通道

运行时:
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ VoiceChannel │  │ CLIChannel   │  │ APIChannel   │
│ (独立loop)   │  │ (独立loop)   │  │ (FastAPI)    │
└──────────────┘  └──────────────┘  └──────────────┘
       ↓                 ↓                 ↓
       └─────────────────┴─────────────────┘
                        ↓
            ┌───────────────────────┐
            │  共享的 AgentCore      │
            │  共享的 SessionManager │
            └───────────────────────┘

每个会话完全隔离：
- VoiceChannel: session_voice
- CLIChannel:   session_cli_1
- APIChannel:   session_api_1, session_api_2...
```

### 4.3 子Agent调用流程

```
用户: "帮我写一个Python爬虫并测试"
       ↓
主Agent分析 → 调用 code_assistant 子Agent
       ↓
子Agent执行:
  1. 生成代码
  2. 调用 run_code 工具测试
  3. 返回结果给主Agent
       ↓
主Agent整合 → 格式化输出给用户
```

---

## 5. 技术选型

### 5.1 Web API技术栈

**选择：Streamable HTTP (JSONL格式)**

与SSE对比：

| 特性 | SSE | Streamable HTTP (JSONL) | 选择 |
|-----|-----|------------------------|------|
| 协议标准 | W3C SSE | HTTP Chunked | ✅ HTTP |
| HTTP方法 | 仅GET | 任意 | ✅ HTTP |
| 浏览器支持 | EventSource API | fetch API | ✅ HTTP |
| 格式灵活性 | 固定事件格式 | 任意（JSON/文本） | ✅ HTTP |
| LLM生态 | 少用 | **主流**（OpenAI/Anthropic/MCP） | ✅ HTTP |
| 工具调用 | 需包装 | 原生支持 | ✅ HTTP |

**事件类型定义：**

```python
# 文本chunk
{"type": "text", "content": "你好"}

# 工具调用
{"type": "tool_call", "tool": "search_web", "args": {"query": "天气"}}

# 工具结果
{"type": "tool_result", "tool": "search_web", "result": "晴天"}

# 子Agent调用
{"type": "sub_agent_start", "agent": "code_assistant", "task": "写代码"}
{"type": "sub_agent_done", "agent": "code_assistant", "result": "..."}

# 错误
{"type": "error", "error": "API调用失败"}

# 完成
{"type": "done"}
```

**FastAPI实现：**

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import json

app = FastAPI(title="ShiYiBot API")

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式对话 - JSONL格式"""
    session_id = request.session_id or await session_manager.create_session()

    async def generate():
        try:
            async for event in agent_core.process_message_stream(
                session_id,
                request.message
            ):
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "error": str(e)}) + "\n"
        finally:
            yield json.dumps({"type": "done"}) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson"
    )
```

### 5.2 持久化方案

**选择：SQLite + 内存LRU缓存**

- **零中间件依赖** - 无需Redis等外部服务
- **轻量高效** - SQLite性能优秀，支持异步
- **热数据内存化** - LRU缓存活跃会话，毫秒级响应
- **异步写入** - 不阻塞主流程

```python
架构：
内存层（快）→ SQLite（持久）
LRU缓存      异步写入
```

### 5.3 技术栈总结

| 组件 | 技术选型 | 理由 |
|-----|---------|------|
| Web框架 | FastAPI | 异步、类型安全、自动文档 |
| 流式协议 | Streamable HTTP (JSONL) | 兼容LLM生态、灵活 |
| 数据库 | SQLite + SQLAlchemy | 零依赖、轻量 |
| 缓存 | LRU内存缓存 | 简单高效 |
| LLM引擎 | 复用现有OpenAICompatibleEngine | 代码复用 |
| 工具协议 | 装饰器注册 + MCP | 内置+外部灵活组合 |

---

## 6. 核心组件设计

### 6.1 会话管理器 (SessionManager)

**职责：** 管理会话生命周期、消息持久化、缓存协调

```python
class Session:
    session_id: str
    created_at: datetime
    last_active: datetime
    context: ConversationContext
    metadata: dict

class SessionManager:
    async def create_session(metadata: dict) -> Session
    async def get_session(session_id: str) -> Session | None
    async def get_context(session_id: str) -> ConversationContext
    async def save_message(session_id, role, content, metadata)
    async def list_sessions(limit: int) -> list[Session]
    async def delete_session(session_id: str)
```

### 6.2 Agent核心 (AgentCore)

**职责：** LLM推理、工具调用、子Agent协作

```python
class AgentCore:
    async def process_message_stream(
        session_id: str,
        user_message: str
    ) -> AsyncIterator[dict]:
        """
        流式处理消息

        Yields:
            {"type": "text", "content": "..."}
            {"type": "tool_call", ...}
            {"type": "tool_result", ...}
            {"type": "sub_agent_start", ...}
        """

    async def invoke_sub_agent(
        agent_name: str,
        task: str,
        context: dict
    ) -> AsyncIterator[dict]:
        """调用子Agent"""

    async def _execute_tool(
        tool_name: str,
        parameters: dict
    ) -> Any:
        """执行工具"""
```

### 6.3 通道基类 (BaseChannel)

**职责：** 定义通道接口，实现策略模式

```python
class BaseChannel(ABC):
    @abstractmethod
    async def start(self):
        """启动通道"""

    @abstractmethod
    async def stop(self):
        """停止通道"""

    async def send_to_agent(self, session_id: str, message: str):
        """发送消息到Agent层（统一接口）"""
        async for event in agent_core.process_message_stream(session_id, message):
            if event["type"] == "text":
                await self.on_text_chunk(event["content"])
            elif event["type"] == "tool_call":
                await self.on_tool_call(event)
            # ...

    @abstractmethod
    async def on_text_chunk(self, chunk: str):
        """处理文本chunk（各通道自己实现）"""
```

### 6.4 上下文管理器 (ContextManager)

**职责：** Token窗口管理、自动摘要

```python
class ContextManager:
    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens

    async def get_context_messages(
        session_id: str,
        messages: list[dict]
    ) -> list[dict]:
        """
        获取适合LLM的消息列表
        自动处理token限制（摘要或截断）
        """
        if self._estimate_tokens(messages) > self.max_tokens:
            return await self._summarize_messages(messages)
        return messages

    async def _summarize_messages(messages: list[dict]) -> list[dict]:
        """
        摘要策略：
        - 保留最近3轮对话（原文）
        - 将更早的对话摘要成精简版
        """
```

---

## 7. 工具系统

### 7.1 工具基类

```python
class ToolDefinition(BaseModel):
    """工具定义 - 转换为OpenAI function calling格式"""
    name: str
    description: str
    parameters: Dict[str, ToolParameter]

    def to_openai_format(self) -> dict:
        """转换为OpenAI的function定义格式"""

class BaseTool(ABC):
    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        pass

    async def run(self, **kwargs) -> Any:
        """模板方法：校验 → 执行 → 日志"""
        await self.validate_params(kwargs)
        result = await self.execute(**kwargs)
        await self._log_execution(kwargs, result)
        return result
```

### 7.2 工具注册器

```python
class ToolRegistry:
    _tools: Dict[str, BaseTool] = {}

    @classmethod
    async def initialize(cls, tools_config: dict):
        """
        初始化工具系统
        1. 加载内置工具
        2. 加载MCP工具（如果启用）
        """

    @classmethod
    def register(cls, tool: BaseTool):
        """注册工具"""

    @classmethod
    def get_tool(cls, name: str) -> BaseTool | None:
        """获取工具"""

    @classmethod
    def get_tool_definitions(cls) -> List[dict]:
        """获取所有工具定义（OpenAI格式）"""
```

### 7.3 内置工具示例

#### search_web

```python
class Tool(BaseTool):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="search_web",
            description="搜索互联网获取最新信息",
            parameters={
                "query": ToolParameter(type="string", description="搜索关键词", required=True)
            }
        )

    async def execute(self, query: str) -> str:
        # 接入搜索API（DuckDuckGo/Google/Bing）
```

#### file_operations

```python
class Tool(BaseTool):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_operations",
            description="读取或写入文件",
            parameters={
                "operation": ToolParameter(type="string", enum=["read", "write", "append", "list"]),
                "path": ToolParameter(type="string"),
                "content": ToolParameter(type="string", required=False)
            }
        )

    async def execute(self, operation: str, path: str, content: str = "") -> str:
        # 文件读写操作
```

#### execute_shell

```python
class Tool(BaseTool):
    async def validate_params(self, params: dict):
        """安全检查：禁止危险命令"""
        command = params.get("command", "")
        dangerous = ["rm -rf", "dd if=", "mkfs", "format"]
        for danger in dangerous:
            if danger in command:
                raise ValueError(f"禁止执行危险命令: {danger}")

    async def execute(self, command: str, timeout: int = 30) -> str:
        # 执行Shell命令
```

### 7.4 MCP工具接入

```python
class MCPClient:
    """MCP协议客户端 - 接入外部工具服务"""

    @classmethod
    async def initialize(cls, servers: List[Dict]):
        """
        连接MCP服务器并注册工具
        1. 获取服务器的工具列表
        2. 包装成MCPTool
        3. 注册到ToolRegistry
        """

class MCPTool(BaseTool):
    """MCP工具包装器"""

    async def execute(self, **kwargs) -> str:
        """调用MCP服务器执行工具"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.server_url}/execute",
                json={"tool": self.name, "parameters": kwargs}
            )
            return response.json()["result"]
```

---

## 8. 子Agent系统

### 8.1 子Agent基类

```python
class BaseAgent(ABC):
    @property
    @abstractmethod
    def description(self) -> str:
        """Agent描述（主Agent用于判断何时调用）"""

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """专业领域的system prompt"""

    @property
    def available_tools(self) -> list[str]:
        """该Agent可用的工具列表（空=所有工具）"""
        return []

    @abstractmethod
    async def execute(
        self,
        task: str,
        context: Dict[str, Any]
    ) -> AsyncIterator[dict]:
        """执行任务，返回事件流"""
```

### 8.2 代码助手子Agent示例

```python
class CodeAssistantAgent(BaseAgent):
    @property
    def description(self) -> str:
        return "代码助手，擅长编写、调试、测试代码"

    @property
    def system_prompt(self) -> str:
        return """
        你是专业的代码助手。
        工作流程：理解需求 → 设计方案 → 编写代码 → 测试验证 → 优化
        """

    @property
    def available_tools(self) -> list[str]:
        return ["execute_shell", "file_operations", "search_web"]

    async def execute(self, task: str, context: dict) -> AsyncIterator[dict]:
        # 创建专用LLM实例
        llm = OpenAICompatibleEngine(
            system_prompt=self.system_prompt,
            temperature=0.3  # 代码生成用较低temperature
        )

        # 流式推理 + 工具调用
        async for chunk in llm.chat_stream(messages, tools=self.available_tools):
            yield chunk
```

### 8.3 Agent注册器

```python
class AgentRegistry:
    _agents: Dict[str, BaseAgent] = {}

    @classmethod
    async def initialize(cls, config: dict):
        """加载内置Agent"""
        await cls.register("code_assistant", CodeAssistantAgent(config))
        await cls.register("general_qa", GeneralQAAgent(config))

    @classmethod
    def get_agent(cls, name: str) -> BaseAgent | None:
        """获取Agent"""

    @classmethod
    def list_agents(cls) -> list[dict]:
        """列出所有Agent及其描述"""
```

### 8.4 主Agent调用子Agent

```python
class AgentCore:
    async def _should_use_sub_agent(self, user_message: str) -> tuple[bool, str | None]:
        """使用LLM判断是否需要调用子Agent"""
        agent_list = AgentRegistry.list_agents()
        prompt = f"""
        用户消息：{user_message}
        可用的子Agent：{agent_list}
        判断：这个任务是否需要调用子Agent？返回Agent名称或"none"。
        """
        response = await self.llm_engine.chat_simple(prompt)
        # ...

    async def process_message_stream(self, session_id, user_message):
        should_delegate, agent_name = await self._should_use_sub_agent(user_message)

        if should_delegate:
            yield {"type": "sub_agent_start", "agent": agent_name}
            agent = AgentRegistry.get_agent(agent_name)
            async for event in agent.execute(user_message, context):
                yield event
            yield {"type": "sub_agent_done", "agent": agent_name}
        else:
            # 主Agent处理
```

---

## 9. 记忆系统

### 9.1 存储层 (SQLite)

**表结构：**

```sql
-- 会话表
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    last_active DATETIME NOT NULL,
    metadata JSON DEFAULT '{}',
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0
);

-- 消息表
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,  -- user | assistant | tool | system
    content TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    metadata JSON DEFAULT '{}',
    INDEX idx_session (session_id)
);
```

**存储类：**

```python
class MemoryStorage:
    def __init__(self, db_path: str = "data/sessions.db"):
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    async def create_session(metadata: dict) -> str
    async def get_session(session_id: str) -> SessionRecord
    async def save_message(session_id, role, content, metadata)
    async def get_messages(session_id, limit=100) -> List[MessageRecord]
    async def list_sessions(limit, offset) -> List[SessionRecord]
    async def delete_session(session_id)
```

### 9.2 缓存层 (LRU)

```python
class ConversationContext:
    session_id: str
    messages: list[dict]
    metadata: dict
    created_at: datetime
    last_active: datetime

class LRUCache:
    def __init__(self, max_size: int = 100):
        self._cache: OrderedDict[str, ConversationContext] = OrderedDict()

    def get(session_id: str) -> ConversationContext | None:
        """获取（LRU：移到末尾）"""

    def put(session_id: str, context: ConversationContext):
        """放入（满则淘汰最久未使用）"""
```

### 9.3 会话管理器整合

```python
class SessionManager:
    def __init__(self, memory_config):
        self.storage = MemoryStorage(memory_config.sqlite_path)
        self.cache = LRUCache(max_size=memory_config.cache_size)
        self.context_manager = ContextManager()

    async def get_session(session_id) -> ConversationContext:
        # 1. 尝试从缓存获取
        context = self.cache.get(session_id)
        if context:
            return context

        # 2. 从数据库加载
        record = await self.storage.get_session(session_id)
        messages = await self.storage.get_messages(session_id)

        # 3. 重建上下文并缓存
        context = ConversationContext(...)
        self.cache.put(session_id, context)
        return context

    async def save_message(session_id, role, content, metadata):
        # 1. 更新缓存
        context = self.cache.get(session_id)
        if context:
            context.add_message(role, content, metadata)

        # 2. 异步写入数据库（不阻塞）
        asyncio.create_task(
            self.storage.save_message(session_id, role, content, metadata)
        )
```

### 9.4 上下文摘要

```python
class ContextManager:
    async def get_context_messages(
        session_id: str,
        messages: list[dict]
    ) -> list[dict]:
        """自动处理token限制"""
        token_count = self._estimate_tokens(messages)

        if token_count <= self.max_tokens:
            return messages

        # 触发摘要
        return await self._summarize_messages(messages)

    async def _summarize_messages(messages: list[dict]) -> list[dict]:
        """
        策略：
        1. 保留system prompt
        2. 保留最近3轮对话（原文）
        3. 将更早的对话摘要成精简版
        """
        KEEP_RECENT_ROUNDS = 3
        recent = messages[-(KEEP_RECENT_ROUNDS * 2):]
        old = messages[:-(KEEP_RECENT_ROUNDS * 2)]

        # 调用LLM摘要旧对话
        summary = await llm_engine.chat_simple(f"摘要以下对话：{old}")

        return [
            {"role": "system", "content": f"历史摘要：{summary}"},
            *recent
        ]
```

---

## 10. 配置文件

### 10.1 config.yaml

```yaml
# 系统配置
system:
  name: "ShiYiBot"
  log_level: "INFO"
  audio_sample_rate: 16000

# 通道配置
channels:
  voice:
    enabled: true           # 是否启用语音通道

  cli:
    enabled: true           # 是否启用CLI通道
    default_session: true   # 启动时自动创建会话

  api:
    enabled: true           # 是否启用API通道
    host: "0.0.0.0"
    port: 8000
    cors_origins: ["*"]

# Agent配置
agent:
  max_context_tokens: 4000     # 上下文窗口
  auto_summarize: true         # 自动摘要
  enable_sub_agents: true      # 启用子Agent功能

# LLM引擎配置
llm:
  api_base: "${DEEPSEEK_API_BASE}"
  api_key: "${DEEPSEEK_API_KEY}"
  model: "deepseek-chat"
  system_prompt: "你是ShiYiBot，一个智能助理。"
  temperature: 0.7
  max_tokens: 2000
  enable_function_calling: true

# 工具配置
tools:
  builtin:
    - search_web
    - execute_shell
    - file_operations

  mcp:
    enabled: false
    servers: []
    # - url: "http://localhost:3000/mcp"
    #   name: "custom_tools"

# 记忆系统配置
memory:
  storage_type: "sqlite"
  sqlite_path: "data/sessions.db"
  cache_size: 100
  auto_flush_interval: 60

# 语音引擎配置（仅voice通道使用）
wake_word:
  enabled: true
  model_path: "models/hey_jarvis.tflite"
  threshold: 0.5

vad:
  silence_duration_ms: 500
  max_recording_seconds: 30
  continuous_window_seconds: 3

stt:
  provider: "tencent"
  app_id: "${TENCENT_APP_ID}"
  secret_id: "${TENCENT_SECRET_ID}"
  secret_key: "${TENCENT_SECRET_KEY}"
  region: "ap-guangzhou"

tts:
  provider: "edge"
  voice: "zh-CN-XiaoxiaoNeural"
  rate: "+0%"
  pitch: "+0Hz"

audio:
  input_device_index: null
  output_device_index: null
  chunk_size: 1600
  input_channels: 1
```

---

## 11. 启动流程

### 11.1 主入口 (main.py)

```python
async def main():
    # 1. 加载配置
    config = load_config()
    setup_logger(config.system.log_level)

    # 2. 创建Orchestrator
    orchestrator = Orchestrator(config)

    # 3. 处理退出信号
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _request_stop():
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _request_stop)

    # 4. 启动
    run_task = asyncio.create_task(orchestrator.start())

    # 5. 等待退出
    await stop_event.wait()
    await orchestrator.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### 11.2 Orchestrator (总调度器)

```python
class Orchestrator:
    def __init__(self, config: Settings):
        self.config = config

        # 初始化核心组件（单例）
        self.session_manager = SessionManager(config.memory)
        self.agent_core = AgentCore(config)

        # 初始化通道（根据配置启用）
        self.channels = []

        if config.channels.voice.get("enabled"):
            self.channels.append(VoiceChannel(config))

        if config.channels.cli.get("enabled"):
            self.channels.append(
                TextCLIChannel(config, self.agent_core, self.session_manager)
            )

        if config.channels.api.get("enabled"):
            self.channels.append(
                TextAPIChannel(config, self.agent_core, self.session_manager)
            )

    async def start(self):
        # 1. 初始化核心组件
        await self._initialize_core()

        # 2. 并行启动所有通道
        self.running = True
        channel_tasks = [
            asyncio.create_task(channel.start())
            for channel in self.channels
        ]

        # 3. 等待所有通道
        await asyncio.gather(*channel_tasks, return_exceptions=True)

    async def _initialize_core(self):
        # 1. 初始化工具注册器
        await ToolRegistry.initialize(self.config.tools)

        # 2. 初始化Agent核心
        await self.agent_core.initialize()

        # 3. 初始化会话管理器
        await self.session_manager.initialize()
```

---

## 12. 实施路线图

### 阶段1：核心基础（2-3天）

**目标：** 实现最小可用的文字版系统

**任务：**
- ✓ 配置文件重构
- ✓ 会话管理器（SessionManager + SQLite + 缓存）
- ✓ Agent核心（AgentCore，复用现有LLM引擎）
- ✓ CLI通道（TextCLIChannel）
- ✓ 简单工具系统（3个内置工具：search_web、file_operations、execute_shell）

**验收标准：**
- CLI启动并创建会话
- 发送消息，LLM回复
- 会话持久化和恢复

**文件清单：**
```
core/
  session_manager.py        🆕
  agent_core.py             🆕
  context_manager.py        🆕
  orchestrator.py           🆕
memory/
  storage.py                🆕
  cache.py                  🆕
channels/
  base.py                   🆕
  text_cli_channel.py       🆕
tools/
  base.py                   🆕
  registry.py               🆕
  builtin/
    file_operations.py      🆕
    execute_shell.py        🆕
    search_web.py           🆕
config/
  config.yaml               📝 修改
main.py                     📝 修改
```

### 阶段2：工具调用（1-2天）

**目标：** LLM可以调用工具完成任务

**任务：**
- ✓ 增强LLM引擎支持function calling
- ✓ AgentCore实现工具调用循环
- ✓ 流式事件系统（text/tool_call/tool_result）
- ✓ CLI显示工具调用过程

**验收标准：**
- "帮我搜索Python教程" → 调用search_web
- "读取README.md文件" → 调用file_operations
- "查看当前目录" → 调用execute_shell

### 阶段3：Web API（1-2天）

**目标：** 提供HTTP API服务

**任务：**
- ✓ FastAPI通道（TextAPIChannel）
- ✓ Streamable HTTP流式响应
- ✓ 会话管理API
- ✓ CORS配置

**API端点：**
```
POST /api/chat              非流式
POST /api/chat/stream       流式（JSONL）
GET  /api/sessions          列出会话
POST /api/sessions          创建会话
DELETE /api/sessions/:id    删除会话
```

**验收标准：**
- Postman/curl测试API
- 流式响应正确分块
- 多会话隔离

### 阶段4：语音通道适配（1天）

**目标：** 将现有语音版包装成通道

**任务：**
- ✓ VoiceChannel包装AssistantCore
- ✓ Orchestrator同时运行voice+cli+api
- ✓ 配置文件启用/禁用通道

**验收标准：**
- 同时启动3个通道
- 语音通道独立工作
- CLI和API可以并行使用

### 阶段5：子Agent系统（2-3天，可选）

**目标：** 实现主-子Agent协作

**任务：**
- ✓ Agent基类和注册器
- ✓ 代码助手子Agent示例
- ✓ 主Agent判断逻辑
- ✓ 子Agent事件流集成

**验收标准：**
- "帮我写个Python爬虫" → 调用code_assistant
- 子Agent调用工具完成任务
- 结果返回主Agent整合

### 阶段6：MCP工具接入（1-2天，可选）

**目标：** 支持外部MCP工具服务

**任务：**
- ✓ MCP客户端实现
- ✓ 动态工具注册
- ✓ 配置文件添加MCP服务器

**验收标准：**
- 连接到MCP服务器
- 调用外部工具
- 工具结果正确返回

### 阶段7：优化和完善（持续）

- ✓ 上下文自动摘要
- ✓ Token计数优化
- ✓ 错误处理和重试
- ✓ 日志和监控
- ✓ 性能优化
- ✓ 单元测试和集成测试
- ✓ 文档完善

---

## 13. 测试策略

### 13.1 单元测试

```python
# tests/test_session_manager.py
@pytest.mark.asyncio
async def test_create_session():
    manager = SessionManager({"sqlite_path": ":memory:", "cache_size": 10})
    await manager.initialize()

    context = await manager.create_session({"channel": "test"})
    assert context.session_id is not None

@pytest.mark.asyncio
async def test_message_persistence():
    manager = SessionManager({"sqlite_path": ":memory:", "cache_size": 10})
    await manager.initialize()

    context = await manager.create_session()
    await manager.save_message(context.session_id, "user", "你好")

    # 清空缓存，强制从数据库加载
    manager.cache.clear()

    loaded = await manager.get_session(context.session_id)
    assert len(loaded.messages) == 1
    assert loaded.messages[0]["content"] == "你好"
```

### 13.2 集成测试

```python
# tests/test_agent_integration.py
@pytest.mark.asyncio
async def test_tool_calling_flow():
    """测试完整的工具调用流程"""
    agent = AgentCore(config)
    await agent.initialize()

    events = []
    async for event in agent.process_message_stream(
        session_id="test",
        user_message="读取README.md文件"
    ):
        events.append(event)

    # 验证事件流
    assert any(e["type"] == "tool_call" for e in events)
    assert any(e["type"] == "tool_result" for e in events)
    assert any(e["type"] == "text" for e in events)
```

### 13.3 手动测试清单

**CLI测试：**
- [ ] 启动CLI，显示欢迎信息
- [ ] 输入消息，收到流式回复
- [ ] /new 创建新会话
- [ ] /list 列出会话
- [ ] /switch 切换会话
- [ ] Ctrl+C 正常退出
- [ ] 重启后会话恢复

**API测试：**
- [ ] POST /api/chat 返回完整响应
- [ ] POST /api/chat/stream 流式返回JSONL
- [ ] 创建多个会话，互不干扰
- [ ] 工具调用在API中正确返回

**并发测试：**
- [ ] 同时运行voice+cli+api
- [ ] CLI和API可以并行使用
- [ ] 语音通道不受影响

**工具测试：**
- [ ] search_web 正常工作
- [ ] file_operations 读写文件
- [ ] execute_shell 执行命令（安全检查生效）

---

## 总结

### 核心设计原则

1. **分层架构** - 通道/调度/Agent/能力/引擎清晰分离
2. **设计模式** - 策略、注册器、单例、责任链、适配器等
3. **异步优先** - 全异步架构，支持高并发
4. **流式优先** - Streamable HTTP (JSONL)，兼容LLM生态
5. **轻量级** - 零中间件，SQLite+内存缓存
6. **可扩展** - 工具和Agent可插拔

### 技术栈

| 组件 | 技术选型 |
|-----|---------|
| Web框架 | FastAPI |
| 流式协议 | Streamable HTTP (JSONL) |
| 数据库 | SQLite + SQLAlchemy (async) |
| 缓存 | LRU内存缓存 |
| LLM | 复用现有OpenAICompatibleEngine |
| 工具协议 | 装饰器注册 + MCP |

### 关键特性

- ✅ 多通道支持（语音/CLI/API并行运行）
- ✅ 单用户多会话隔离
- ✅ 工具调用（内置+MCP）
- ✅ 主-子Agent协作
- ✅ 流式响应（兼容OpenAI/Anthropic/MCP）
- ✅ 轻量级持久化（SQLite+LRU）
- ✅ 自动上下文摘要

---

**设计完成日期**: 2026-02-11
**下一步**: 创建git worktree，开始实施
