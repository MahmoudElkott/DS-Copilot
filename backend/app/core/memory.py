# backend/app/core/memory.py
from sqlalchemy import create_engine, Column, String, Text, DateTime, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import List, Dict, Optional
import json
import uuid

from app.config import settings

Base = declarative_base()


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, index=True, nullable=False)
    role = Column(String, nullable=False)  # user, assistant, system, agent
    content = Column(Text, nullable=False)
    agent_name = Column(String, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class ProjectState(Base):
    __tablename__ = "project_states"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, index=True, nullable=False)
    step_name = Column(String, nullable=False)
    status = Column(String, default="pending")
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    code_generated = Column(Text, nullable=True)
    execution_result = Column(JSON, nullable=True)
    error_log = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)


class MemoryManager:
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent_name: str = None,
        metadata: dict = None,
    ):
        session = self.Session()
        try:
            msg = ConversationMessage(
                session_id=session_id,
                role=role,
                content=content,
                agent_name=agent_name,
                metadata_=metadata,
            )
            session.add(msg)
            session.commit()
            return msg.id
        finally:
            session.close()

    def get_conversation(
        self, session_id: str, limit: int = 50
    ) -> List[Dict]:
        session = self.Session()
        try:
            messages = (
                session.query(ConversationMessage)
                .filter_by(session_id=session_id)
                .order_by(ConversationMessage.timestamp.asc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "agent_name": m.agent_name,
                    "metadata": m.metadata_,
                    "timestamp": m.timestamp.isoformat(),
                }
                for m in messages
            ]
        finally:
            session.close()

    def save_project_state(
        self,
        session_id: str,
        step_name: str,
        status: str = "running",
        **kwargs,
    ):
        session = self.Session()
        try:
            state = ProjectState(
                session_id=session_id,
                step_name=step_name,
                status=status,
                **kwargs,
            )
            session.add(state)
            session.commit()
            return state.id
        finally:
            session.close()

    def update_project_state(self, state_id: str, **kwargs):
        session = self.Session()
        try:
            state = session.query(ProjectState).get(state_id)
            if state:
                for key, value in kwargs.items():
                    if hasattr(state, key):
                        setattr(state, key, value)
                session.commit()
        finally:
            session.close()

    def get_project_history(self, session_id: str) -> List[Dict]:
        session = self.Session()
        try:
            states = (
                session.query(ProjectState)
                .filter_by(session_id=session_id)
                .order_by(ProjectState.timestamp.asc())
                .all()
            )
            return [
                {
                    "id": s.id,
                    "step": s.step_name,
                    "status": s.status,
                    "code": s.code_generated,
                    "result": s.execution_result,
                    "error": s.error_log,
                    "retries": s.retry_count,
                    "timestamp": s.timestamp.isoformat(),
                }
                for s in states
            ]
        finally:
            session.close()

    def get_all_sessions(self) -> List[str]:
        session = self.Session()
        try:
            results = (
                session.query(ConversationMessage.session_id)
                .distinct()
                .all()
            )
            return [r[0] for r in results]
        finally:
            session.close()


memory = MemoryManager()
