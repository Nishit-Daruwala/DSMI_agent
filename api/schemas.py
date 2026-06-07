"""
API Schemas — Pydantic models for request/response shapes.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


# ── Auth ──────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    name: str
    email: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    name: str
    username: str

class UserInfo(BaseModel):
    username: str
    name: str
    email: str


# ── Research ──────────────────────────────────────────
class StartResearchRequest(BaseModel):
    query: str = Field(..., min_length=5)
    max_iterations: int = Field(default=3, ge=1, le=5)


# ── Sessions ──────────────────────────────────────────
class SessionSummary(BaseModel):
    id: str
    query: str
    status: str
    quality_score: Optional[float] = None
    created_at: str

class SessionListResponse(BaseModel):
    sessions: List[SessionSummary]
    total: int


# ── Health ────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    database: str
    agents: str
