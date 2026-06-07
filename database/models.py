import os
from datetime import datetime
import json
from sqlalchemy import Column, String, Float, Integer, DateTime, Text, JSON, ForeignKey, Enum, create_engine
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID
import uuid

import enum

Base = declarative_base()

# Utility to output JSON seamlessly between Postgres (JSONB) and SQLite (JSON)
# For max portability, we use JSON here, but can easily be JSONB for Supabase.
JsonType = JSONB if os.getenv("DATABASE_URL", "").startswith("postgresql") else JSON

class SessionStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class ResearchSession(Base):
    __tablename__ = "research_session"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    query = Column(String, nullable=False)
    status = Column(Enum(SessionStatus), default=SessionStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    max_iterations = Column(Integer, default=3)
    final_quality_score = Column(Float, nullable=True)

    # Relationships
    reports = relationship("ResearchReport", back_populates="session", cascade="all, delete-orphan")
    sources = relationship("ResearchSource", back_populates="session", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="session", cascade="all, delete-orphan")

class ResearchReport(Base):
    __tablename__ = "research_report"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("research_session.id"), nullable=False)
    title = Column(String, nullable=False)
    executive_summary = Column(Text, nullable=True)
    full_report = Column(Text, nullable=True)
    swot_analysis = Column(JsonType, nullable=True)
    key_findings = Column(JsonType, nullable=True)
    data_points = Column(JsonType, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ResearchSession", back_populates="reports")

class ResearchSource(Base):
    __tablename__ = "research_source"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("research_session.id"), nullable=False)
    url = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content_hash = Column(String, nullable=True) # for deduplication
    snippet = Column(Text, nullable=True)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    reliability_score = Column(Float, nullable=True)

    session = relationship("ResearchSession", back_populates="sources")

class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("research_session.id"), nullable=False)
    agent_name = Column(String, nullable=False)
    action = Column(String, nullable=False)
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    tokens_used = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("ResearchSession", back_populates="audit_logs")
