"""
FastAPI Server — Thin API layer wrapping existing DSMI backend functions.

This file contains NO new business logic. It only:
1. Exposes existing Python functions as REST endpoints
2. Streams LangGraph events via Server-Sent Events (SSE)
3. Serves PDF/MD downloads

All agent orchestration, database operations, and report generation
remain in their original locations and are imported directly.
"""
import sys
import os
import json
import time
import asyncio
from typing import Optional

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from dotenv import load_dotenv

load_dotenv()

# ── Import existing backend functions (unchanged) ────
from database.db import init_db, list_sessions, load_research_session, save_research_session
from graph.state import create_initial_state
from graph.agent_graph import build_research_graph
# from ui.pdf_export import generate_pdf_report

# ── Import API modules ───────────────────────────────
from api.schemas import (
    LoginRequest, RegisterRequest, TokenResponse,
    StartResearchRequest, SessionSummary, SessionListResponse,
    HealthResponse,
)
from api.auth import (
    authenticate_user, register_user, create_access_token, get_current_user,
)


# ── App Setup ─────────────────────────────────────────
app = FastAPI(
    title="DSMI Agent API",
    description="Deep Strategic Market Intelligence — Backend API",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup ───────────────────────────────────────────
@app.on_event("startup")
def startup():
    init_db()


# ══════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ══════════════════════════════════════════════════════

@app.post("/api/auth/login", response_model=TokenResponse)
def login(req: LoginRequest):
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(data={"sub": user["username"]})
    return TokenResponse(
        access_token=token,
        name=user["name"],
        username=user["username"],
    )


@app.post("/api/auth/register", response_model=TokenResponse)
def register(req: RegisterRequest):
    user = register_user(req.username, req.password, req.name, req.email)
    token = create_access_token(data={"sub": user["username"]})
    return TokenResponse(
        access_token=token,
        name=user["name"],
        username=user["username"],
    )


@app.get("/api/auth/me")
def me(user: dict = Depends(get_current_user)):
    return user


# ══════════════════════════════════════════════════════
# SESSION ENDPOINTS
# ══════════════════════════════════════════════════════

@app.get("/api/sessions", response_model=SessionListResponse)
def get_sessions(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
):
    sessions = list_sessions(limit=limit, offset=offset)
    return SessionListResponse(
        sessions=[SessionSummary(**s) for s in sessions],
        total=len(sessions),
    )


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str, user: dict = Depends(get_current_user)):
    data = load_research_session(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    return data


# ══════════════════════════════════════════════════════
# RESEARCH ENDPOINT (SSE streaming)
# ══════════════════════════════════════════════════════

@app.post("/api/research/start")
def start_research(req: StartResearchRequest, user: dict = Depends(get_current_user)):
    """
    Start a research run and stream agent events via Server-Sent Events.
    
    The frontend receives a stream of JSON events like:
        data: {"node": "planner", "status": "...", "state": {...}}
        data: {"node": "researcher", "status": "...", "state": {...}}
        ...
        data: {"node": "__done__", "session_id": "...", "quality_score": 0.85}
    """
    def event_stream():
        try:
            graph = build_research_graph()
            config = {"recursion_limit": 50}
            state = create_initial_state(req.query, max_iterations=req.max_iterations)
            full_state = dict(state)

            for event in graph.stream(state, config):
                for node_name, output in event.items():
                    # Merge updates into full_state
                    for key, val in output.items():
                        if key in ["error_log", "warnings"] and val:
                            full_state[key] = (full_state.get(key) or []) + list(val)
                        else:
                            full_state[key] = val

                    # Build SSE payload
                    payload = {
                        "node": node_name,
                        "status": output.get("status", f"{node_name} completed"),
                        "timestamp": time.strftime('%H:%M:%S'),
                        "metrics_count": len(full_state.get("metrics", [])),
                        "sources_count": len(full_state.get("sources", [])),
                        "quality_score": full_state.get("quality_score", 0),
                        "iteration": full_state.get("current_iteration", 0),
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

            # Save to database
            try:
                save_research_session(full_state)
            except Exception as db_err:
                yield f"data: {json.dumps({'node': '__error__', 'detail': f'DB save failed: {db_err}'})}\n\n"

            # Final event
            done_payload = {
                "node": "__done__",
                "session_id": full_state.get("session_id"),
                "quality_score": full_state.get("quality_score", 0),
                "sources_count": len(full_state.get("sources", [])),
                "metrics_count": len(full_state.get("metrics", [])),
            }
            yield f"data: {json.dumps(done_payload)}\n\n"

        except Exception as e:
            error_payload = {"node": "__error__", "detail": str(e)}
            yield f"data: {json.dumps(error_payload)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ══════════════════════════════════════════════════════
# DOWNLOAD ENDPOINTS
# ══════════════════════════════════════════════════════

@app.get("/api/sessions/{session_id}/pdf")
def download_pdf(session_id: str, user: dict = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="PDF export functionality is currently unavailable.")


@app.get("/api/sessions/{session_id}/md")
def download_md(session_id: str, user: dict = Depends(get_current_user)):
    data = load_research_session(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    report_md = data.get("final_report", "")
    if not report_md:
        raise HTTPException(status_code=404, detail="No report content available")
    return Response(
        content=report_md.encode("utf-8"),
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=DSMI_Report_{session_id[:8]}.md"},
    )


# ══════════════════════════════════════════════════════
# HEALTH
# ══════════════════════════════════════════════════════

@app.get("/api/health", response_model=HealthResponse)
def health_check():
    db_status = "ok"
    try:
        list_sessions(limit=1)
    except Exception:
        db_status = "error"

    return HealthResponse(
        status="ok",
        database=db_status,
        agents="ready",
    )
