# ShiYiBot 剩余功能实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 完成 feature/text-agent 分支的剩余3项功能：search_web 真实实现、子Agent系统、MCP客户端

**Architecture:**
- search_web 使用 duckduckgo_search 库（免费、无需API key）格式化搜索结果
- 子Agent系统在现有 AgentCore 基础上新增 agents/ 目录，BaseAgent抽象类 + AgentRegistry 注册器 + 内置代码助手
- MCP客户端通过 httpx 异步调用外部MCP服务器，动态注册工具到 ToolRegistry

**Tech Stack:** Python asyncio, duckduckgo_search, httpx, 现有 BaseTool/ToolRegistry 架构

**Worktree:** `C:/Users/vayneluo/.config/superpowers/worktrees/shiyi-bot/feature/text-agent`

---

## Task 1: 实现 search_web 真实搜索

**Files:**
- Modify: `tools/builtin/search_web.py`
- Modify: `pyproject.toml`（添加 duckduckgo_search 依赖）

**Step 1: 安装 duckduckgo_search**

```bash
cd C:/Users/vayneluo/.config/superpowers/worktrees/shiyi-bot/feature/text-agent
uv add duckduckgo_search
```

Expected: duckduckgo_search 加入 pyproject.toml

**Step 2: 替换 search_web.py 为真实实现**

完整替换 `tools/builtin/search_web.py`：

```python
"""Web search tool using DuckDuckGo"""
from tools.base import BaseTool, ToolDefinition, ToolParameter
from loguru import logger


class Tool(BaseTool):
    """Web search tool (DuckDuckGo, no API key required)"""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="search_web",
            description="搜索互联网获取最新信息，适合查询新闻、事实、最新数据等",
            parameters={
                "query": ToolParameter(
                    type="string",
                    description="搜索关键词",
                    required=True
                ),
                "max_results": ToolParameter(
                    type="number",
                    description="最大结果数量，默认5",
                    required=False
                )
            }
        )

    async def execute(self, query: str, max_results: int = 5) -> str:
        """Execute web search via DuckDuckGo"""
        try:
            from duckduckgo_search import DDGS
            import asyncio

            logger.info(f"搜索: {query}, 最大结果: {max_results}")

            # DDGS is sync, run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: list(DDGS().text(query, max_results=int(max_results)))
            )

            if not results:
                return f"未找到关于'{query}'的搜索结果"

            # Format results
            formatted = [f"搜索结果：{query}\n"]
            for i, r in enumerate(results, 1):
                title = r.get("title", "无标题")
                body = r.get("body", "无摘要")
                href = r.get("href", "")
                formatted.append(f"{i}. **{title}**\n   {body}\n   {href}\n")

            return "\n".join(formatted)

        except ImportError:
            return "搜索功能未安装，请运行: uv add duckduckgo_search"
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return f"搜索失败: {e}"
```

**Step 3: 验证可运行**

```bash
cd C:/Users/vayneluo/.config/superpowers/worktrees/shiyi-bot/feature/text-agent
python -c "
import asyncio
from tools.builtin.search_web import Tool
async def test():
    t = Tool()
    result = await t.execute('Python asyncio 教程', max_results=3)
    print(result)
asyncio.run(test())
"
```

Expected: 打印3条搜索结果，包含标题和摘要

**Step 4: Commit**

```bash
git add tools/builtin/search_web.py pyproject.toml
git commit -m "feat: implement real web search using DuckDuckGo"
```

---

## Task 2: 实现子Agent系统（agents/ 目录）

**Files:**
- Create: `agents/__init__.py`
- Create: `agents/base_agent.py`
- Create: `agents/registry.py`
- Create: `agents/builtin/__init__.py`
- Create: `agents/builtin/code_assistant.py`
- Create: `agents/builtin/general_qa.py`
- Modify: `core/agent_core.py`（集成子Agent调用）
- Modify: `core/orchestrator.py`（初始化AgentRegistry）

### Step 1: 创建 agents/base_agent.py

```python
"""Sub-agent base class"""
from abc import ABC, abstractmethod
from typing import AsyncIterator, Any


class BaseAgent(ABC):
    """Sub-agent abstract base class"""

    def __init__(self, config):
        self.config = config

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name (unique identifier)"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Agent description (used by main agent to decide when to delegate)"""
        pass

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Specialized system prompt for this agent"""
        pass

    @property
    def available_tools(self) -> list[str]:
        """Tools this agent can use (empty = all tools)"""
        return []

    @abstractmethod
    async def execute(
        self,
        task: str,
        context: dict[str, Any]
    ) -> AsyncIterator[dict]:
        """
        Execute task, yield event stream

        Yields:
            {"type": "text", "content": "..."}
            {"type": "tool_call", "tool": "...", "args": {...}}
            {"type": "tool_result", "tool": "...", "result": "..."}
            {"type": "done"}
        """
        pass
```

### Step 2: 创建 agents/registry.py

```python
"""Agent registry"""
from loguru import logger
from agents.base_agent import BaseAgent


class AgentRegistry:
    """Agent registry - manages all sub-agents"""
    _agents: dict[str, BaseAgent] = {}

    @classmethod
    async def initialize(cls, config):
        """Load built-in agents"""
        from agents.builtin.code_assistant import CodeAssistantAgent
        from agents.builtin.general_qa import GeneralQAAgent

        cls.register(CodeAssistantAgent(config))
        cls.register(GeneralQAAgent(config))
        logger.info(f"AgentRegistry 初始化完成，已加载 {len(cls._agents)} 个子Agent")

    @classmethod
    def register(cls, agent: BaseAgent):
        """Register an agent"""
        cls._agents[agent.name] = agent
        logger.debug(f"注册子Agent: {agent.name}")

    @classmethod
    def get_agent(cls, name: str) -> BaseAgent | None:
        """Get agent by name"""
        return cls._agents.get(name)

    @classmethod
    def list_agents(cls) -> list[dict]:
        """List all agents with descriptions"""
        return [
            {"name": name, "description": agent.description}
            for name, agent in cls._agents.items()
        ]
```

### Step 3: 创建 agents/builtin/code_assistant.py

```python
"""Code assistant sub-agent"""
import json
from typing import AsyncIterator, Any
from loguru import logger

from agents.base_agent import BaseAgent
from engines.llm.openai_compatible_engine import OpenAICompatibleEngine
from tools.registry import ToolRegistry


class CodeAssistantAgent(BaseAgent):
    """Code assistant - writing, debugging, testing code"""

    @property
    def name(self) -> str:
        return "code_assistant"

    @property
    def description(self) -> str:
        return "代码助手，擅长编写、调试、测试各种编程语言的代码"

    @property
    def system_prompt(self) -> str:
        return """你是专业的代码助手。
工作流程：理解需求 → 分析方案 → 编写代码 → 必要时测试验证 → 解释说明
要求：
- 代码简洁、注重可读性
- 提供简短的解释
- 遇到错误主动调试修复"""

    @property
    def available_tools(self) -> list[str]:
        return ["execute_shell", "file_operations", "search_web"]

    async def execute(
        self,
        task: str,
        context: dict[str, Any]
    ) -> AsyncIterator[dict]:
        """Execute coding task"""
        llm = OpenAICompatibleEngine(
            api_base=self.config.llm["api_base"],
            api_key=self.config.llm["api_key"],
            model=self.config.llm["model"],
            system_prompt=self.system_prompt,
            temperature=0.3,  # lower temp for code
            max_tokens=self.config.llm.get("max_tokens", 2000)
        )
        await llm.initialize()

        try:
            # Get tools available to this agent
            all_tools = ToolRegistry.get_tool_definitions()
            tools = [
                t for t in all_tools
                if t["function"]["name"] in self.available_tools
            ] if self.available_tools else all_tools

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": task}
            ]

            max_iterations = 5
            for _ in range(max_iterations):
                response = await llm.chat_with_tools(messages, tools=tools)

                if response["type"] == "text":
                    yield {"type": "text", "content": response["content"]}
                    messages.append({"role": "assistant", "content": response["content"]})
                    break

                elif response["type"] == "tool_calls":
                    tool_calls = response["tool_calls"]
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": tc["id"],
                                "type": "function",
                                "function": {"name": tc["name"], "arguments": tc["arguments"]}
                            }
                            for tc in tool_calls
                        ]
                    })

                    for tc in tool_calls:
                        tool_name = tc["name"]
                        tool_args = json.loads(tc["arguments"])

                        yield {"type": "tool_call", "tool": tool_name, "args": tool_args}

                        try:
                            tool = ToolRegistry.get_tool(tool_name)
                            if tool:
                                result = await tool.execute(**tool_args)
                            else:
                                result = f"工具不存在: {tool_name}"
                        except Exception as e:
                            result = f"工具执行失败: {e}"

                        yield {"type": "tool_result", "tool": tool_name, "result": str(result)}
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "name": tool_name,
                            "content": str(result)
                        })

        except Exception as e:
            logger.error(f"CodeAssistantAgent 执行失败: {e}")
            yield {"type": "error", "error": str(e)}
        finally:
            await llm.cleanup()

        yield {"type": "done"}
```

### Step 4: 创建 agents/builtin/general_qa.py

```python
"""General Q&A sub-agent"""
from typing import AsyncIterator, Any
from loguru import logger

from agents.base_agent import BaseAgent
from engines.llm.openai_compatible_engine import OpenAICompatibleEngine


class GeneralQAAgent(BaseAgent):
    """General Q&A agent - knowledge, analysis, writing"""

    @property
    def name(self) -> str:
        return "general_qa"

    @property
    def description(self) -> str:
        return "通用问答助手，擅长知识查询、分析推理、文本写作"

    @property
    def system_prompt(self) -> str:
        return """你是通用问答助手。
要求：
- 回答准确、客观
- 结构清晰
- 必要时使用搜索工具获取最新信息"""

    @property
    def available_tools(self) -> list[str]:
        return ["search_web"]

    async def execute(
        self,
        task: str,
        context: dict[str, Any]
    ) -> AsyncIterator[dict]:
        """Execute Q&A task"""
        llm = OpenAICompatibleEngine(
            api_base=self.config.llm["api_base"],
            api_key=self.config.llm["api_key"],
            model=self.config.llm["model"],
            system_prompt=self.system_prompt,
            temperature=0.7,
            max_tokens=self.config.llm.get("max_tokens", 2000)
        )
        await llm.initialize()

        try:
            from tools.registry import ToolRegistry
            import json

            all_tools = ToolRegistry.get_tool_definitions()
            tools = [
                t for t in all_tools
                if t["function"]["name"] in self.available_tools
            ] if self.available_tools else all_tools

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": task}
            ]

            for _ in range(3):
                response = await llm.chat_with_tools(messages, tools=tools)

                if response["type"] == "text":
                    yield {"type": "text", "content": response["content"]}
                    break

                elif response["type"] == "tool_calls":
                    for tc in response["tool_calls"]:
                        tool_name = tc["name"]
                        tool_args = json.loads(tc["arguments"])
                        yield {"type": "tool_call", "tool": tool_name, "args": tool_args}

                        try:
                            tool = ToolRegistry.get_tool(tool_name)
                            result = await tool.execute(**tool_args) if tool else f"工具不存在: {tool_name}"
                        except Exception as e:
                            result = f"工具执行失败: {e}"

                        yield {"type": "tool_result", "tool": tool_name, "result": str(result)}
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "name": tool_name,
                            "content": str(result)
                        })

        except Exception as e:
            logger.error(f"GeneralQAAgent 执行失败: {e}")
            yield {"type": "error", "error": str(e)}
        finally:
            await llm.cleanup()

        yield {"type": "done"}
```

### Step 5: 创建 agents/__init__.py 和 agents/builtin/__init__.py

`agents/__init__.py`:
```python
from agents.base_agent import BaseAgent
from agents.registry import AgentRegistry

__all__ = ["BaseAgent", "AgentRegistry"]
```

`agents/builtin/__init__.py`:
```python
from agents.builtin.code_assistant import CodeAssistantAgent
from agents.builtin.general_qa import GeneralQAAgent

__all__ = ["CodeAssistantAgent", "GeneralQAAgent"]
```

### Step 6: 在 core/agent_core.py 中集成子Agent

在 `AgentCore.__init__` 中添加：
```python
self.enable_sub_agents = config.agent.get("enable_sub_agents", False) if hasattr(config, 'agent') else False
```

在 `process_message_stream` 方法后添加子Agent调用方法：

```python
async def process_with_sub_agent(
    self,
    agent_name: str,
    task: str,
    context: dict
) -> AsyncIterator[dict]:
    """Delegate task to a sub-agent"""
    from agents.registry import AgentRegistry

    agent = AgentRegistry.get_agent(agent_name)
    if not agent:
        yield {"type": "error", "error": f"子Agent不存在: {agent_name}"}
        return

    yield {"type": "sub_agent_start", "agent": agent_name, "task": task}

    async for event in agent.execute(task, context):
        yield event

    yield {"type": "sub_agent_done", "agent": agent_name}
```

### Step 7: 在 orchestrator.py 中初始化 AgentRegistry

在 `_initialize_core` 方法中，在 `ToolRegistry.initialize` 后添加：

```python
# Initialize Agent registry (if sub-agents enabled)
agent_config = getattr(self.config, 'agent', {})
if isinstance(agent_config, dict) and agent_config.get("enable_sub_agents", False):
    from agents.registry import AgentRegistry
    await AgentRegistry.initialize(self.config)
    logger.info("AgentRegistry 初始化完成")
```

### Step 8: 在 config.yaml 中添加 agent 配置段

在 `# 工具配置` 前添加：

```yaml
# Agent配置
agent:
  enable_sub_agents: true
  max_context_tokens: 4000
```

### Step 9: 验证子Agent系统可加载

```bash
cd C:/Users/vayneluo/.config/superpowers/worktrees/shiyi-bot/feature/text-agent
python -c "
import asyncio
from config.settings import load_config
from agents.registry import AgentRegistry

async def test():
    config = load_config()
    await AgentRegistry.initialize(config)
    agents = AgentRegistry.list_agents()
    print('已注册的子Agent:')
    for a in agents:
        print(f'  - {a[\"name\"]}: {a[\"description\"]}')

asyncio.run(test())
"
```

Expected:
```
已注册的子Agent:
  - code_assistant: 代码助手，擅长编写、调试、测试各种编程语言的代码
  - general_qa: 通用问答助手，擅长知识查询、分析推理、文本写作
```

### Step 10: Commit

```bash
git add agents/ core/agent_core.py core/orchestrator.py config/config.yaml
git commit -m "feat: implement sub-agent system with code_assistant and general_qa"
```

---

## Task 3: 实现 MCP 客户端

**Files:**
- Create: `tools/mcp_client.py`
- Modify: `tools/registry.py`（支持 MCP 工具加载）
- Modify: `pyproject.toml`（添加 httpx 依赖）

### Step 1: 安装 httpx

```bash
uv add httpx
```

### Step 2: 创建 tools/mcp_client.py

```python
"""MCP (Model Context Protocol) client - connects to external tool servers"""
import httpx
from loguru import logger

from tools.base import BaseTool, ToolDefinition, ToolParameter


class MCPTool(BaseTool):
    """Wrapper for a tool provided by an MCP server"""

    def __init__(self, server_url: str, tool_schema: dict):
        self.server_url = server_url
        self._definition = self._parse_schema(tool_schema)

    def _parse_schema(self, schema: dict) -> ToolDefinition:
        """Parse MCP tool schema into ToolDefinition"""
        params = {}
        input_schema = schema.get("inputSchema", {})
        properties = input_schema.get("properties", {})
        required_list = input_schema.get("required", [])

        for param_name, param_schema in properties.items():
            params[param_name] = ToolParameter(
                type=param_schema.get("type", "string"),
                description=param_schema.get("description", ""),
                required=param_name in required_list,
                enum=param_schema.get("enum")
            )

        return ToolDefinition(
            name=schema["name"],
            description=schema.get("description", ""),
            parameters=params
        )

    @property
    def definition(self) -> ToolDefinition:
        return self._definition

    async def execute(self, **kwargs) -> str:
        """Call the MCP server to execute the tool"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.server_url}/tools/call",
                    json={
                        "name": self.definition.name,
                        "arguments": kwargs
                    }
                )
                response.raise_for_status()
                result = response.json()

                # MCP standard response format
                content = result.get("content", [])
                if content:
                    return "\n".join(
                        item.get("text", "") for item in content
                        if item.get("type") == "text"
                    )
                return str(result)

        except httpx.TimeoutException:
            raise TimeoutError(f"MCP server 超时: {self.server_url}")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"MCP server 返回错误 {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise RuntimeError(f"MCP 工具调用失败: {e}")


class MCPClient:
    """MCP protocol client - discovers and registers tools from MCP servers"""

    @classmethod
    async def initialize(cls, servers: list[dict], tool_registry) -> int:
        """
        Connect to MCP servers and register their tools

        Args:
            servers: List of server configs: [{"url": "http://...", "name": "..."}]
            tool_registry: ToolRegistry to register tools into

        Returns:
            Number of tools registered
        """
        total = 0
        for server_config in servers:
            url = server_config.get("url", "")
            name = server_config.get("name", url)
            if not url:
                continue

            try:
                count = await cls._load_server_tools(url, name, tool_registry)
                total += count
                logger.info(f"MCP服务器 '{name}' 已加载 {count} 个工具")
            except Exception as e:
                logger.warning(f"MCP服务器 '{name}' ({url}) 加载失败: {e}")

        return total

    @classmethod
    async def _load_server_tools(cls, url: str, name: str, tool_registry) -> int:
        """Load tools from a single MCP server"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{url}/tools/list")
            response.raise_for_status()
            data = response.json()

        tools = data.get("tools", [])
        for tool_schema in tools:
            mcp_tool = MCPTool(server_url=url, tool_schema=tool_schema)
            tool_registry.register(mcp_tool)
            logger.debug(f"注册MCP工具: {tool_schema['name']} (来自 {name})")

        return len(tools)
```

### Step 3: 修改 tools/registry.py 支持 MCP 工具加载

在 `ToolRegistry.initialize` 方法中，在内置工具加载完成后添加：

```python
# Load MCP tools if enabled
mcp_config = tools_config.get("mcp", {})
if isinstance(mcp_config, dict) and mcp_config.get("enabled", False):
    servers = mcp_config.get("servers", [])
    if servers:
        from tools.mcp_client import MCPClient
        count = await MCPClient.initialize(servers, cls)
        logger.info(f"MCP 工具加载完成，共 {count} 个工具")
```

### Step 4: Commit

```bash
git add tools/mcp_client.py tools/registry.py pyproject.toml
git commit -m "feat: implement MCP client for external tool server integration"
```

---

## Task 4: 推送到远端

```bash
git push origin feature/text-agent
```

Expected: 分支推送成功

---

## 验收标准

### search_web
- [ ] `python -c "..."` 测试返回真实搜索结果
- [ ] 无需 API key

### 子Agent系统
- [ ] `AgentRegistry.list_agents()` 返回 code_assistant 和 general_qa
- [ ] `config.yaml` 包含 `agent.enable_sub_agents: true`
- [ ] orchestrator 启动时可正常初始化

### MCP客户端
- [ ] `tools/mcp_client.py` 文件存在
- [ ] `config.yaml` 中 `mcp.enabled: false` 时不尝试连接
- [ ] 代码结构符合 MCP 协议标准 (`/tools/list`, `/tools/call` 端点)
