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
    session_metadata = Column(JSON, default=dict)
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
    message_metadata = Column(JSON, default=dict)


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
                session_metadata=metadata,
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
                message_metadata=metadata or {}
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
