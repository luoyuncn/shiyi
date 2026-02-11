# Phase 1: Core Foundation - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the minimal viable text-based agent system with session management, CLI interface, and basic tool support.

**Architecture:** SQLite + LRU cache for session persistence, AgentCore wrapping existing LLM engine, simple tool registry with 3 built-in tools, CLI channel for user interaction.

**Tech Stack:** Python 3.11, SQLite + aiosqlite, SQLAlchemy async, existing OpenAICompatibleEngine, asyncio

---

## Task 1: Memory Storage Layer (SQLite)

**Files:**
- Create: `memory/__init__.py`
- Create: `memory/storage.py`
- Create: `tests/test_memory_storage.py`

### Step 1: Write failing test for session creation

Create `tests/test_memory_storage.py`:

```python
"""Tests for memory storage layer"""
import pytest
from datetime import datetime
from memory.storage import MemoryStorage


@pytest.mark.asyncio
async def test_create_session():
    """Test creating a new session"""
    storage = MemoryStorage(db_path=":memory:")
    await storage.initialize()

    session_id = await storage.create_session({"channel": "test"})

    assert session_id is not None
    assert len(session_id) == 36  # UUID format

    # Verify session exists
    session = await storage.get_session(session_id)
    assert session is not None
    assert session.metadata["channel"] == "test"

    await storage.cleanup()


@pytest.mark.asyncio
async def test_save_and_get_messages():
    """Test saving and retrieving messages"""
    storage = MemoryStorage(db_path=":memory:")
    await storage.initialize()

    session_id = await storage.create_session({})

    # Save messages
    await storage.save_message(session_id, "user", "你好")
    await storage.save_message(session_id, "assistant", "你好！有什么可以帮你的？")

    # Retrieve messages
    messages = await storage.get_messages(session_id)
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "你好"
    assert messages[1].role == "assistant"

    await storage.cleanup()
```

### Step 2: Run test to verify it fails

Run:
```bash
cd ~/.config/superpowers/worktrees/shiyi-bot/feature/text-agent
.venv/Scripts/python -m pytest tests/test_memory_storage.py -v
```

Expected: FAIL with "No module named 'memory'"

### Step 3: Create memory package init

Create `memory/__init__.py`:

```python
"""Memory system - SQLite storage and LRU cache"""
from memory.storage import MemoryStorage
from memory.cache import LRUCache, ConversationContext

__all__ = ["MemoryStorage", "LRUCache", "ConversationContext"]
```

### Step 4: Implement storage layer

Create `memory/storage.py`:

```python
"""SQLite storage layer for session persistence"""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, DateTime, JSON, Text, Integer, select, update, delete
from loguru import logger

Base = declarative_base()


class SessionRecord(Base):
    """Session record table"""
    __tablename__ = "sessions"

    session_id = Column(String(36), primary_key=True)
    created_at = Column(DateTime, nullable=False)
    last_active = Column(DateTime, nullable=False)
    metadata = Column(JSON, default=dict)
    message_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)


class MessageRecord(Base):
    """Message record table"""
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    metadata = Column(JSON, default=dict)


class MemoryStorage:
    """SQLite storage manager"""

    def __init__(self, db_path: str = "data/sessions.db"):
        self.db_path = db_path
        self.engine = None
        self.session_factory = None

    async def initialize(self):
        """Initialize database"""
        from pathlib import Path

        # Create data directory if needed
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # Create async engine
        self.engine = create_async_engine(
            f"sqlite+aiosqlite:///{self.db_path}",
            echo=False
        )

        # Create tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Create session factory
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        logger.info(f"数据库初始化完成: {self.db_path}")

    async def create_session(self, metadata: dict) -> str:
        """Create new session"""
        session_id = str(uuid.uuid4())
        now = datetime.now()

        async with self.session_factory() as session:
            record = SessionRecord(
                session_id=session_id,
                created_at=now,
                last_active=now,
                metadata=metadata,
                message_count=0,
                total_tokens=0
            )
            session.add(record)
            await session.commit()

        return session_id

    async def get_session(self, session_id: str) -> Optional[SessionRecord]:
        """Get session"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(SessionRecord).where(SessionRecord.session_id == session_id)
            )
            return result.scalar_one_or_none()

    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict = None
    ):
        """Save message"""
        message_id = str(uuid.uuid4())
        now = datetime.now()

        async with self.session_factory() as session:
            # Save message
            message = MessageRecord(
                id=message_id,
                session_id=session_id,
                role=role,
                content=content,
                timestamp=now,
                metadata=metadata or {}
            )
            session.add(message)

            # Update session last_active and message_count
            await session.execute(
                update(SessionRecord)
                .where(SessionRecord.session_id == session_id)
                .values(
                    last_active=now,
                    message_count=SessionRecord.message_count + 1
                )
            )

            await session.commit()

    async def get_messages(
        self,
        session_id: str,
        limit: int = 100
    ) -> List[MessageRecord]:
        """Get session messages"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(MessageRecord)
                .where(MessageRecord.session_id == session_id)
                .order_by(MessageRecord.timestamp.asc())
                .limit(limit)
            )
            return list(result.scalars().all())

    async def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[SessionRecord]:
        """List all sessions"""
        async with self.session_factory() as session:
            result = await session.execute(
                select(SessionRecord)
                .order_by(SessionRecord.last_active.desc())
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())

    async def delete_session(self, session_id: str):
        """Delete session and its messages"""
        async with self.session_factory() as session:
            # Delete messages
            await session.execute(
                delete(MessageRecord).where(MessageRecord.session_id == session_id)
            )

            # Delete session
            await session.execute(
                delete(SessionRecord).where(SessionRecord.session_id == session_id)
            )

            await session.commit()

    async def cleanup(self):
        """Cleanup resources"""
        if self.engine:
            await self.engine.dispose()
```

### Step 5: Run test to verify it passes

Run:
```bash
.venv/Scripts/python -m pytest tests/test_memory_storage.py -v
```

Expected: PASS (2 tests)

### Step 6: Commit

```bash
git add memory/ tests/test_memory_storage.py
git commit -m "feat: add SQLite storage layer for session persistence"
```

---

## Task 2: LRU Cache Layer

**Files:**
- Create: `memory/cache.py`
- Create: `tests/test_memory_cache.py`

### Step 1: Write failing test for LRU cache

Create `tests/test_memory_cache.py`:

```python
"""Tests for LRU cache"""
import pytest
from datetime import datetime
from memory.cache import LRUCache, ConversationContext


def test_cache_put_and_get():
    """Test basic cache operations"""
    cache = LRUCache(max_size=3)

    ctx1 = ConversationContext(session_id="session1")
    ctx2 = ConversationContext(session_id="session2")

    cache.put("session1", ctx1)
    cache.put("session2", ctx2)

    assert cache.get("session1") == ctx1
    assert cache.get("session2") == ctx2
    assert cache.get("session3") is None


def test_cache_lru_eviction():
    """Test LRU eviction when cache is full"""
    cache = LRUCache(max_size=2)

    ctx1 = ConversationContext(session_id="session1")
    ctx2 = ConversationContext(session_id="session2")
    ctx3 = ConversationContext(session_id="session3")

    cache.put("session1", ctx1)
    cache.put("session2", ctx2)
    cache.put("session3", ctx3)  # Should evict session1

    assert cache.get("session1") is None
    assert cache.get("session2") == ctx2
    assert cache.get("session3") == ctx3


def test_conversation_context():
    """Test ConversationContext operations"""
    ctx = ConversationContext(session_id="test", metadata={"channel": "cli"})

    ctx.add_message("user", "你好")
    ctx.add_message("assistant", "你好！")

    assert len(ctx.messages) == 2
    assert ctx.messages[0]["role"] == "user"
    assert ctx.messages[1]["content"] == "你好！"

    # Test to_dict
    data = ctx.to_dict()
    assert data["session_id"] == "test"
    assert len(data["messages"]) == 2
```

### Step 2: Run test to verify it fails

Run:
```bash
.venv/Scripts/python -m pytest tests/test_memory_cache.py -v
```

Expected: FAIL with "No module named 'memory.cache'"

### Step 3: Implement LRU cache

Create `memory/cache.py`:

```python
"""LRU cache for hot session data"""
from collections import OrderedDict
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ConversationContext:
    """Conversation context"""
    session_id: str
    messages: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)

    def add_message(self, role: str, content: str, metadata: dict = None):
        """Add message"""
        self.messages.append({
            "role": role,
            "content": content,
            "metadata": metadata or {}
        })
        self.last_active = datetime.now()

    def to_dict(self) -> dict:
        """Convert to dict"""
        return {
            "session_id": self.session_id,
            "messages": self.messages,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat()
        }


class LRUCache:
    """LRU cache for active sessions"""

    def __init__(self, max_size: int = 100):
        self._cache: OrderedDict[str, ConversationContext] = OrderedDict()
        self._max_size = max_size

    def get(self, session_id: str) -> Optional[ConversationContext]:
        """Get session (LRU: move to end)"""
        if session_id in self._cache:
            self._cache.move_to_end(session_id)
            return self._cache[session_id]
        return None

    def put(self, session_id: str, context: ConversationContext):
        """Put into cache"""
        if session_id in self._cache:
            self._cache.move_to_end(session_id)
        else:
            if len(self._cache) >= self._max_size:
                # Evict oldest
                oldest_id, _ = self._cache.popitem(last=False)
                from loguru import logger
                logger.debug(f"缓存满，淘汰会话: {oldest_id}")

        self._cache[session_id] = context

    def remove(self, session_id: str):
        """Remove session"""
        self._cache.pop(session_id, None)

    def clear(self):
        """Clear cache"""
        self._cache.clear()

    def size(self) -> int:
        """Current cache size"""
        return len(self._cache)
```

### Step 4: Run test to verify it passes

Run:
```bash
.venv/Scripts/python -m pytest tests/test_memory_cache.py -v
```

Expected: PASS (3 tests)

### Step 5: Commit

```bash
git add memory/cache.py tests/test_memory_cache.py
git commit -m "feat: add LRU cache for hot session data"
```

---

## Task 3: Session Manager

**Files:**
- Create: `core/session_manager.py`
- Create: `tests/test_session_manager.py`

### Step 1: Write failing test for session manager

Create `tests/test_session_manager.py`:

```python
"""Tests for session manager"""
import pytest
from core.session_manager import SessionManager
from pydantic import BaseModel


class MemoryConfig(BaseModel):
    """Memory config for testing"""
    sqlite_path: str = ":memory:"
    cache_size: int = 10
    auto_flush_interval: int = 60


@pytest.mark.asyncio
async def test_create_and_get_session():
    """Test session creation and retrieval"""
    config = MemoryConfig()
    manager = SessionManager(config)
    await manager.initialize()

    # Create session
    context = await manager.create_session({"channel": "test"})
    assert context.session_id is not None

    # Get session from cache
    retrieved = await manager.get_session(context.session_id)
    assert retrieved is not None
    assert retrieved.session_id == context.session_id

    await manager.cleanup()


@pytest.mark.asyncio
async def test_save_and_load_messages():
    """Test message persistence"""
    config = MemoryConfig()
    manager = SessionManager(config)
    await manager.initialize()

    context = await manager.create_session({})
    session_id = context.session_id

    # Save messages
    await manager.save_message(session_id, "user", "你好")
    await manager.save_message(session_id, "assistant", "你好！")

    # Clear cache to force database load
    manager.cache.clear()

    # Load from database
    loaded = await manager.get_session(session_id)
    assert len(loaded.messages) == 2

    await manager.cleanup()
```

### Step 2: Run test to verify it fails

Run:
```bash
.venv/Scripts/python -m pytest tests/test_session_manager.py -v
```

Expected: FAIL with "No module named 'core.session_manager'"

### Step 3: Implement session manager

Create `core/session_manager.py`:

```python
"""Session manager - integrates storage and cache"""
import asyncio
from typing import Optional
from loguru import logger

from memory.storage import MemoryStorage, SessionRecord
from memory.cache import LRUCache, ConversationContext


class SessionManager:
    """Session manager - singleton"""

    def __init__(self, memory_config):
        self.config = memory_config

        # Storage layer
        self.storage = MemoryStorage(memory_config.sqlite_path)

        # Cache layer
        self.cache = LRUCache(max_size=memory_config.cache_size)

        # Auto flush task
        self._flush_task = None
        self._running = False

    async def initialize(self):
        """Initialize"""
        await self.storage.initialize()

        # Start auto flush loop
        self._running = True
        self._flush_task = asyncio.create_task(self._auto_flush_loop())

        logger.info("会话管理器初始化完成")

    async def create_session(self, metadata: dict = None) -> ConversationContext:
        """Create new session"""
        # Create in database
        session_id = await self.storage.create_session(metadata or {})

        # Create in-memory context
        context = ConversationContext(
            session_id=session_id,
            metadata=metadata or {}
        )

        # Put into cache
        self.cache.put(session_id, context)

        logger.info(f"创建会话: {session_id}")
        return context

    async def get_session(self, session_id: str) -> Optional[ConversationContext]:
        """Get session (from cache first, then database)"""
        # Try cache first
        context = self.cache.get(session_id)
        if context:
            return context

        # Load from database
        record = await self.storage.get_session(session_id)
        if not record:
            return None

        # Load messages
        messages = await self.storage.get_messages(session_id)

        # Rebuild context
        context = ConversationContext(
            session_id=session_id,
            messages=[
                {
                    "role": msg.role,
                    "content": msg.content,
                    "metadata": msg.metadata
                }
                for msg in messages
            ],
            metadata=record.metadata,
            created_at=record.created_at,
            last_active=record.last_active
        )

        # Put into cache
        self.cache.put(session_id, context)

        return context

    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict = None
    ):
        """Save message"""
        # Update cache
        context = self.cache.get(session_id)
        if context:
            context.add_message(role, content, metadata)

        # Async write to database (non-blocking)
        asyncio.create_task(
            self.storage.save_message(session_id, role, content, metadata)
        )

    async def list_sessions(self, limit: int = 50) -> list[SessionRecord]:
        """List all sessions"""
        return await self.storage.list_sessions(limit=limit)

    async def delete_session(self, session_id: str):
        """Delete session"""
        self.cache.remove(session_id)
        await self.storage.delete_session(session_id)

    async def _auto_flush_loop(self):
        """Auto flush loop"""
        interval = self.config.auto_flush_interval

        while self._running:
            await asyncio.sleep(interval)
            logger.debug(f"缓存状态: {self.cache.size()} 个活跃会话")

    async def cleanup(self):
        """Cleanup resources"""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            await asyncio.gather(self._flush_task, return_exceptions=True)

        await self.storage.cleanup()
        self.cache.clear()
```

### Step 4: Run test to verify it passes

Run:
```bash
.venv/Scripts/python -m pytest tests/test_session_manager.py -v
```

Expected: PASS (2 tests)

### Step 5: Commit

```bash
git add core/session_manager.py tests/test_session_manager.py
git commit -m "feat: add session manager integrating storage and cache"
```

---

## Task 4: Tool System Base Classes

**Files:**
- Create: `tools/__init__.py`
- Create: `tools/base.py`
- Create: `tools/registry.py`
- Create: `tests/test_tool_system.py`

### Step 1: Write failing test for tool system

Create `tests/test_tool_system.py`:

```python
"""Tests for tool system"""
import pytest
from tools.base import BaseTool, ToolDefinition, ToolParameter
from tools.registry import ToolRegistry


class DummyTool(BaseTool):
    """Dummy tool for testing"""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="dummy_tool",
            description="A dummy tool",
            parameters={
                "text": ToolParameter(
                    type="string",
                    description="Text input",
                    required=True
                )
            }
        )

    async def execute(self, text: str) -> str:
        return f"Processed: {text}"


@pytest.mark.asyncio
async def test_tool_execution():
    """Test tool execution"""
    tool = DummyTool()

    result = await tool.run(text="hello")
    assert result == "Processed: hello"


def test_tool_definition_to_openai_format():
    """Test OpenAI format conversion"""
    tool = DummyTool()
    openai_format = tool.definition.to_openai_format()

    assert openai_format["type"] == "function"
    assert openai_format["function"]["name"] == "dummy_tool"
    assert "text" in openai_format["function"]["parameters"]["properties"]
    assert "text" in openai_format["function"]["parameters"]["required"]


def test_tool_registry():
    """Test tool registry"""
    ToolRegistry._tools.clear()

    tool = DummyTool()
    ToolRegistry.register(tool)

    retrieved = ToolRegistry.get_tool("dummy_tool")
    assert retrieved is not None
    assert retrieved.definition.name == "dummy_tool"

    tools = ToolRegistry.list_tools()
    assert "dummy_tool" in tools
```

### Step 2: Run test to verify it fails

Run:
```bash
.venv/Scripts/python -m pytest tests/test_tool_system.py -v
```

Expected: FAIL with "No module named 'tools'"

### Step 3: Create tool base classes

Create `tools/__init__.py`:

```python
"""Tool system"""
from tools.base import BaseTool, ToolDefinition, ToolParameter
from tools.registry import ToolRegistry

__all__ = ["BaseTool", "ToolDefinition", "ToolParameter", "ToolRegistry"]
```

Create `tools/base.py`:

```python
"""Tool base classes"""
from abc import ABC, abstractmethod
from typing import Any, Dict
from pydantic import BaseModel


class ToolParameter(BaseModel):
    """Tool parameter definition"""
    type: str
    description: str
    required: bool = True
    enum: list[str] | None = None


class ToolDefinition(BaseModel):
    """Tool definition - converts to OpenAI function calling format"""
    name: str
    description: str
    parameters: Dict[str, ToolParameter]

    def to_openai_format(self) -> dict:
        """Convert to OpenAI function definition format"""
        properties = {}
        required = []

        for param_name, param in self.parameters.items():
            properties[param_name] = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                properties[param_name]["enum"] = param.enum

            if param.required:
                required.append(param_name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }


class BaseTool(ABC):
    """Tool base class"""

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Tool definition"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute tool (subclass implements)"""
        pass

    async def validate_params(self, params: dict):
        """Validate parameters (optional override)"""
        pass

    async def run(self, **kwargs) -> Any:
        """Template method: validate → execute → log"""
        await self.validate_params(kwargs)
        result = await self.execute(**kwargs)
        await self._log_execution(kwargs, result)
        return result

    async def _log_execution(self, params: dict, result: Any):
        """Log execution"""
        from loguru import logger
        logger.debug(f"工具执行: {self.definition.name} | 参数: {params}")
```

Create `tools/registry.py`:

```python
"""Tool registry"""
from typing import Dict, List
from loguru import logger

from tools.base import BaseTool


class ToolRegistry:
    """Tool registry"""
    _tools: Dict[str, BaseTool] = {}
    _initialized = False

    @classmethod
    async def initialize(cls, tools_config: dict):
        """Initialize tool system"""
        if cls._initialized:
            return

        # Load built-in tools
        builtin_tools = tools_config.get("builtin", [])
        for tool_name in builtin_tools:
            await cls._load_builtin_tool(tool_name)

        cls._initialized = True
        logger.info(f"工具注册器初始化完成，已注册 {len(cls._tools)} 个工具")

    @classmethod
    async def _load_builtin_tool(cls, tool_name: str):
        """Load built-in tool"""
        try:
            module = __import__(
                f"tools.builtin.{tool_name}",
                fromlist=["Tool"]
            )
            tool_class = getattr(module, "Tool")
            tool_instance = tool_class()

            cls.register(tool_instance)
            logger.debug(f"已加载内置工具: {tool_name}")

        except Exception as e:
            logger.error(f"加载工具失败 {tool_name}: {e}")

    @classmethod
    def register(cls, tool: BaseTool):
        """Register tool"""
        cls._tools[tool.definition.name] = tool

    @classmethod
    def get_tool(cls, name: str) -> BaseTool | None:
        """Get tool"""
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> List[str]:
        """List all tool names"""
        return list(cls._tools.keys())

    @classmethod
    def get_tool_definitions(cls) -> List[dict]:
        """Get all tool definitions (OpenAI format)"""
        return [
            tool.definition.to_openai_format()
            for tool in cls._tools.values()
        ]
```

### Step 4: Run test to verify it passes

Run:
```bash
.venv/Scripts/python -m pytest tests/test_tool_system.py -v
```

Expected: PASS (3 tests)

### Step 5: Commit

```bash
git add tools/ tests/test_tool_system.py
git commit -m "feat: add tool system base classes and registry"
```

---

## Task 5: Built-in Tool - File Operations

**Files:**
- Create: `tools/builtin/__init__.py`
- Create: `tools/builtin/file_operations.py`
- Create: `tests/test_builtin_tools.py`

### Step 1: Write failing test

Create `tests/test_builtin_tools.py`:

```python
"""Tests for built-in tools"""
import pytest
from pathlib import Path
import tempfile
from tools.builtin.file_operations import Tool as FileOpsTool


@pytest.mark.asyncio
async def test_file_read():
    """Test file read operation"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("Hello World")
        temp_path = f.name

    try:
        tool = FileOpsTool()
        result = await tool.run(operation="read", path=temp_path)
        assert "Hello World" in result
    finally:
        Path(temp_path).unlink()


@pytest.mark.asyncio
async def test_file_write():
    """Test file write operation"""
    temp_path = tempfile.mktemp(suffix='.txt')

    try:
        tool = FileOpsTool()
        await tool.run(operation="write", path=temp_path, content="Test Content")

        # Verify file was written
        assert Path(temp_path).exists()
        assert Path(temp_path).read_text() == "Test Content"
    finally:
        if Path(temp_path).exists():
            Path(temp_path).unlink()
```

### Step 2: Run test to verify it fails

Run:
```bash
.venv/Scripts/python -m pytest tests/test_builtin_tools.py::test_file_read -v
```

Expected: FAIL with "No module named 'tools.builtin.file_operations'"

### Step 3: Implement file operations tool

Create `tools/builtin/__init__.py`:

```python
"""Built-in tools"""
```

Create `tools/builtin/file_operations.py`:

```python
"""File operations tool"""
from pathlib import Path
from tools.base import BaseTool, ToolDefinition, ToolParameter


class Tool(BaseTool):
    """File operations tool"""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_operations",
            description="读取或写入文件",
            parameters={
                "operation": ToolParameter(
                    type="string",
                    description="操作类型",
                    required=True,
                    enum=["read", "write", "append", "list"]
                ),
                "path": ToolParameter(
                    type="string",
                    description="文件路径",
                    required=True
                ),
                "content": ToolParameter(
                    type="string",
                    description="写入的内容（write/append时需要）",
                    required=False
                )
            }
        )

    async def execute(
        self,
        operation: str,
        path: str,
        content: str = ""
    ) -> str:
        """Execute file operation"""
        file_path = Path(path)

        try:
            if operation == "read":
                if not file_path.exists():
                    return f"文件不存在: {path}"
                return file_path.read_text(encoding="utf-8")

            elif operation == "write":
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")
                return f"已写入文件: {path}"

            elif operation == "append":
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write(content)
                return f"已追加到文件: {path}"

            elif operation == "list":
                if not file_path.is_dir():
                    return f"不是目录: {path}"
                files = [f.name for f in file_path.iterdir()]
                return "\n".join(files)

            else:
                return f"未知操作: {operation}"

        except Exception as e:
            return f"文件操作失败: {str(e)}"
```

### Step 4: Run test to verify it passes

Run:
```bash
.venv/Scripts/python -m pytest tests/test_builtin_tools.py -v
```

Expected: PASS (2 tests)

### Step 5: Commit

```bash
git add tools/builtin/ tests/test_builtin_tools.py
git commit -m "feat: add file_operations built-in tool"
```

---

## Task 6: Built-in Tool - Execute Shell (placeholder)

**Files:**
- Create: `tools/builtin/execute_shell.py`

### Step 1: Create minimal shell executor

Since shell execution is sensitive and we'll test it manually, create a basic implementation:

Create `tools/builtin/execute_shell.py`:

```python
"""Shell command execution tool (use with caution)"""
import asyncio
from tools.base import BaseTool, ToolDefinition, ToolParameter


class Tool(BaseTool):
    """Shell command execution tool"""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="execute_shell",
            description="执行Shell命令（仅限安全命令）",
            parameters={
                "command": ToolParameter(
                    type="string",
                    description="要执行的Shell命令",
                    required=True
                ),
                "timeout": ToolParameter(
                    type="number",
                    description="超时时间（秒）",
                    required=False
                )
            }
        )

    async def validate_params(self, params: dict):
        """Safety check: block dangerous commands"""
        command = params.get("command", "")

        # Blacklist
        dangerous_commands = [
            "rm -rf", "dd if=", "mkfs", "format",
            "> /dev/sda", ":(){ :|:& };:"
        ]

        for danger in dangerous_commands:
            if danger in command:
                raise ValueError(f"禁止执行危险命令: {danger}")

    async def execute(self, command: str, timeout: int = 30) -> str:
        """Execute shell command"""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            output = stdout.decode() if stdout else ""
            error = stderr.decode() if stderr else ""

            if process.returncode != 0:
                return f"命令执行失败（退出码 {process.returncode}）:\n{error}"

            return output or "命令执行成功（无输出）"

        except asyncio.TimeoutError:
            return f"命令执行超时（{timeout}秒）"

        except Exception as e:
            return f"执行失败: {str(e)}"
```

### Step 2: Commit

```bash
git add tools/builtin/execute_shell.py
git commit -m "feat: add execute_shell built-in tool with safety checks"
```

---

## Task 7: Built-in Tool - Web Search (placeholder)

**Files:**
- Create: `tools/builtin/search_web.py`

### Step 1: Create placeholder web search

Create `tools/builtin/search_web.py`:

```python
"""Web search tool (placeholder implementation)"""
from tools.base import BaseTool, ToolDefinition, ToolParameter


class Tool(BaseTool):
    """Web search tool"""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="search_web",
            description="搜索互联网获取最新信息",
            parameters={
                "query": ToolParameter(
                    type="string",
                    description="搜索关键词",
                    required=True
                ),
                "max_results": ToolParameter(
                    type="number",
                    description="最大结果数量",
                    required=False
                )
            }
        )

    async def execute(self, query: str, max_results: int = 5) -> str:
        """Execute search (placeholder)"""
        # Placeholder: return mock result
        # In production, integrate with DuckDuckGo/Google/Bing API
        return f"搜索结果（模拟）：关于'{query}'的信息暂未实现真实搜索API，这是一个占位符返回。"
```

### Step 2: Commit

```bash
git add tools/builtin/search_web.py
git commit -m "feat: add search_web built-in tool (placeholder)"
```

---

## Task 8: Update Config for Tools and Memory

**Files:**
- Modify: `config/config.yaml`
- Modify: `config/settings.py`

### Step 1: Update config.yaml

Add to `config/config.yaml`:

```yaml
# ... existing config ...

# 工具配置
tools:
  builtin:
    - file_operations
    - execute_shell
    - search_web
  mcp:
    enabled: false
    servers: []

# 记忆系统配置
memory:
  sqlite_path: "data/sessions.db"
  cache_size: 100
  auto_flush_interval: 60
```

### Step 2: Update settings.py

Add to `config/settings.py`:

```python
# Add these classes to existing file

class ToolsConfig(BaseModel):
    """Tools configuration"""
    builtin: list[str] = []
    mcp: dict = {"enabled": False, "servers": []}


class MemoryConfig(BaseModel):
    """Memory configuration"""
    sqlite_path: str = "data/sessions.db"
    cache_size: int = 100
    auto_flush_interval: int = 60


# Update Settings class
class Settings(BaseModel):
    """Application settings"""
    system: dict
    wake_word: dict | None = None
    vad: dict | None = None
    stt: dict | None = None
    llm: dict
    tts: dict | None = None
    audio: dict | None = None
    tools: ToolsConfig  # Add this
    memory: MemoryConfig  # Add this
```

### Step 3: Commit

```bash
git add config/config.yaml config/settings.py
git commit -m "feat: add tools and memory configuration"
```

---

## Task 9: CLI Channel Implementation

**Files:**
- Create: `channels/__init__.py`
- Create: `channels/base.py`
- Create: `channels/text_cli_channel.py`

### Step 1: Create channel base class

Create `channels/__init__.py`:

```python
"""Channels - different input/output interfaces"""
from channels.base import BaseChannel

__all__ = ["BaseChannel"]
```

Create `channels/base.py`:

```python
"""Channel base class"""
from abc import ABC, abstractmethod


class BaseChannel(ABC):
    """Channel abstract base class"""

    @abstractmethod
    async def start(self):
        """Start channel"""
        pass

    @abstractmethod
    async def stop(self):
        """Stop channel"""
        pass
```

### Step 2: Create minimal CLI channel (without AgentCore yet)

Create `channels/text_cli_channel.py`:

```python
"""CLI text channel"""
import asyncio
from loguru import logger
from channels.base import BaseChannel


class TextCLIChannel(BaseChannel):
    """Command line interface channel"""

    def __init__(self, config, session_manager):
        self.config = config
        self.session_manager = session_manager
        self.running = False
        self.current_session = None

    async def start(self):
        """Start CLI loop"""
        self._print_welcome()

        # Create default session
        self.current_session = await self.session_manager.create_session({
            "channel": "cli"
        })

        logger.info(f"会话ID: {self.current_session.session_id}")

        self.running = True

        # Main loop
        while self.running:
            try:
                # Read user input
                user_input = await asyncio.to_thread(
                    input,
                    "\n👤 你: "
                )

                if not user_input.strip():
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    await self._handle_command(user_input)
                    continue

                # Echo for now (will integrate AgentCore later)
                print(f"🤖 助手: [收到消息] {user_input}")

                # Save to session
                await self.session_manager.save_message(
                    self.current_session.session_id,
                    "user",
                    user_input
                )

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"CLI错误: {e}")

    async def stop(self):
        """Stop CLI"""
        self.running = False

    async def _handle_command(self, cmd: str):
        """Handle CLI commands"""
        if cmd == "/new":
            self.current_session = await self.session_manager.create_session({
                "channel": "cli"
            })
            print(f"✅ 新会话: {self.current_session.session_id}")

        elif cmd == "/list":
            sessions = await self.session_manager.list_sessions()
            for s in sessions:
                print(f"- {s.session_id} (最后活跃: {s.last_active})")

        elif cmd.startswith("/switch "):
            session_id = cmd.split()[1]
            self.current_session = await self.session_manager.get_session(session_id)
            if self.current_session:
                print(f"✅ 切换到会话: {session_id}")
            else:
                print(f"❌ 会话不存在: {session_id}")

        elif cmd == "/help":
            self._print_help()

    def _print_welcome(self):
        print("=" * 60)
        print("🏠 ShiYiBot - CLI模式")
        print("命令: /new /list /switch <id> /help")
        print("=" * 60)

    def _print_help(self):
        print("""
可用命令:
  /new          - 创建新会话
  /list         - 列出所有会话
  /switch <id>  - 切换到指定会话
  /help         - 显示帮助
  Ctrl+C        - 退出
        """)
```

### Step 3: Commit

```bash
git add channels/
git commit -m "feat: add CLI channel with basic session commands"
```

---

## Task 10: Minimal Orchestrator

**Files:**
- Create: `core/orchestrator.py`
- Modify: `main.py`

### Step 1: Create orchestrator

Create `core/orchestrator.py`:

```python
"""Orchestrator - manages all channels and core components"""
import asyncio
from loguru import logger
from config.settings import Settings

from core.session_manager import SessionManager
from channels.text_cli_channel import TextCLIChannel
from tools.registry import ToolRegistry


class Orchestrator:
    """Main orchestrator"""

    def __init__(self, config: Settings):
        self.config = config
        self.running = False

        # Initialize core components
        self.session_manager = SessionManager(config.memory)

        # Initialize channels
        self.channels = []

        # For now, only CLI channel
        self.channels.append(
            TextCLIChannel(config, self.session_manager)
        )

    async def start(self):
        """Start all components"""
        logger.info("=" * 60)
        logger.info(f"🚀 {self.config.system['name']} 正在启动...")
        logger.info("=" * 60)

        try:
            # Initialize core
            await self._initialize_core()

            # Start all channels
            self.running = True
            channel_tasks = [
                asyncio.create_task(channel.start(), name=f"channel_{i}")
                for i, channel in enumerate(self.channels)
            ]

            logger.info("✅ 所有通道已启动")
            logger.info("=" * 60)

            # Wait for all channels
            await asyncio.gather(*channel_tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"启动失败: {e}")
            raise

    async def stop(self):
        """Stop all components"""
        logger.info("正在停止所有通道...")
        self.running = False

        for channel in self.channels:
            try:
                await channel.stop()
            except Exception as e:
                logger.error(f"停止通道失败: {e}")

        await self.session_manager.cleanup()

    async def _initialize_core(self):
        """Initialize core components"""
        logger.info("正在初始化核心组件...")

        # Initialize tool registry
        await ToolRegistry.initialize(self.config.tools)
        logger.info(f"已注册 {len(ToolRegistry.list_tools())} 个工具")

        # Initialize session manager
        await self.session_manager.initialize()

        logger.info("核心组件初始化完成")
```

### Step 2: Update main.py to use orchestrator

Modify `main.py`:

```python
"""程序主入口"""
import asyncio
import os
import signal
from pathlib import Path

# ... existing ALSA config code ...

_ensure_alsa_config()
from loguru import logger
from config.settings import load_config
from utils.logger import setup_logger
from core.orchestrator import Orchestrator  # Change this


async def main():
    """程序主函数"""
    # 检查.env文件
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ 错误: 未找到.env文件")
        print("请复制.env.example为.env并填入你的API密钥")
        print("命令: cp .env.example .env")
        return

    try:
        # 加载配置
        config = load_config()

        # 设置日志
        setup_logger(config.system["log_level"])

        # 初始化Orchestrator (instead of AssistantCore)
        orchestrator = Orchestrator(config)

        # 处理退出信号
        loop = asyncio.get_running_loop()
        stop_event = asyncio.Event()

        def _request_stop():
            if not stop_event.is_set():
                stop_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _request_stop)
            except NotImplementedError:
                pass

        # 启动
        run_task = asyncio.create_task(orchestrator.start())

        # 等待退出信号
        await stop_event.wait()
        await orchestrator.stop()
        run_task.cancel()
        await asyncio.gather(run_task, return_exceptions=True)

    except KeyboardInterrupt:
        logger.info("\n👋 接收到退出信号 (Ctrl+C)")

    except Exception as e:
        logger.exception(f"💥 程序异常退出: {e}")

    finally:
        logger.info("=" * 60)
        logger.info("🏠 ShiYiBot已关闭，再见！")
        logger.info("=" * 60)


if __name__ == "__main__":
    # 运行主程序
    asyncio.run(main())
```

### Step 3: Test manually

Run:
```bash
cd ~/.config/superpowers/worktrees/shiyi-bot/feature/text-agent
cp .env.example .env
# Edit .env to add DEEPSEEK_API_KEY

.venv/Scripts/python main.py
```

Expected:
- CLI starts
- Shows welcome message
- Can type messages (echoed back)
- /new creates new session
- /list shows sessions
- Ctrl+C exits cleanly

### Step 4: Commit

```bash
git add core/orchestrator.py main.py
git commit -m "feat: add orchestrator and integrate CLI channel"
```

---

## Summary

Phase 1 is now complete with:

✅ SQLite storage layer with session and message persistence
✅ LRU cache for hot session data
✅ SessionManager integrating storage and cache
✅ Tool system base classes and registry
✅ 3 built-in tools (file_operations, execute_shell, search_web)
✅ CLI channel with session management commands
✅ Orchestrator coordinating all components
✅ Updated config for tools and memory

**Next Steps:** Phase 2 will integrate AgentCore with LLM and implement tool calling.

**Test Coverage:**
- memory/storage.py: ✅ Tested
- memory/cache.py: ✅ Tested
- core/session_manager.py: ✅ Tested
- tools/base.py: ✅ Tested
- tools/registry.py: ✅ Tested
- tools/builtin/file_operations.py: ✅ Tested
- channels/text_cli_channel.py: Manual testing required
- core/orchestrator.py: Integration testing required

**Manual Test Checklist:**
- [ ] CLI starts successfully
- [ ] Can create new sessions with /new
- [ ] Can list sessions with /list
- [ ] Can switch sessions with /switch
- [ ] Sessions persist across restarts
- [ ] Ctrl+C exits cleanly
