import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Ensure models are loaded so Base.metadata knows about them
from .models import Base, ResearchSession, ResearchReport, ResearchSource, AuditLog

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the environment.")

# Create the engine. We handle pooling internally if it's Postgres.
engine = create_engine(
    DATABASE_URL,
    pool_size=5 if DATABASE_URL.startswith("postgresql") else None,
    max_overflow=10 if DATABASE_URL.startswith("postgresql") else None,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """
    Initialize the database by creating all tables.
    Caution: In production, you would use Alembic migrations instead of Base.metadata.create_all()
    """
    print(f"Connecting to database with engine: {engine.name}")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")

def get_session():
    """
    Dependency to get a DB session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_research_session(state: dict):
    """
    Persists the full research state to the database.
    Creates or updates a ResearchSession, ResearchReport, and ResearchSources.
    """
    from .models import ResearchSession, ResearchReport, ResearchSource, SessionStatus
    db = SessionLocal()
    try:
        session_id = state.get("session_id")
        
        # Check if session already exists
        existing = db.query(ResearchSession).filter(ResearchSession.id == session_id).first()
        if existing:
            existing.status = SessionStatus.COMPLETED
            existing.final_quality_score = state.get("quality_score", 0)
        else:
            db_session = ResearchSession(
                id=session_id,
                query=state.get("original_query", ""),
                status=SessionStatus.COMPLETED,
                max_iterations=state.get("max_iterations", 3),
                final_quality_score=state.get("quality_score", 0),
            )
            db.add(db_session)

        # Upsert the report: update if exists, create if not
        existing_report = db.query(ResearchReport).filter(ResearchReport.session_id == session_id).first()
        if existing_report:
            existing_report.title = f"Research on: {state.get('original_query', '')}"
            existing_report.executive_summary = state.get("executive_summary", "")
            existing_report.full_report = state.get("final_report", "")
            existing_report.swot_analysis = state.get("swot_analysis", {})
            existing_report.key_findings = state.get("metrics", [])
        else:
            db_report = ResearchReport(
                session_id=session_id,
                title=f"Research on: {state.get('original_query', '')}",
                executive_summary=state.get("executive_summary", ""),
                full_report=state.get("final_report", ""),
                swot_analysis=state.get("swot_analysis", {}),
                key_findings=state.get("metrics", []),
                data_points={},
            )
            db.add(db_report)

        # Upsert sources: delete old ones and re-insert
        db.query(ResearchSource).filter(ResearchSource.session_id == session_id).delete()
        for source in state.get("sources", []):
            db_source = ResearchSource(
                session_id=session_id,
                url=source.get("url", ""),
                title=source.get("title", ""),
                snippet=source.get("snippet", ""),
            )
            db.add(db_source)

        db.commit()
        print(f"💾 Saved session {session_id} to database.")
        return session_id
    except Exception as e:
        db.rollback()
        print(f"⚠️ Error saving session: {e}")
        return None
    finally:
        db.close()


def load_research_session(session_id: str) -> dict:
    """
    Retrieves a past session from the database as a state dict.
    """
    db = SessionLocal()
    try:
        session = db.query(ResearchSession).filter(ResearchSession.id == session_id).first()
        if not session:
            return None

        report = db.query(ResearchReport).filter(ResearchReport.session_id == session_id).first()
        sources = db.query(ResearchSource).filter(ResearchSource.session_id == session_id).all()

        return {
            "session_id": session.id,
            "original_query": session.query,
            "title": report.title if report else f"Research on: {session.query}",
            "quality_score": session.final_quality_score or 0.0,
            "max_iterations": session.max_iterations,
            "final_report": report.full_report if report else "",
            "executive_summary": report.executive_summary if report else "",
            "swot_analysis": report.swot_analysis if report else {},
            "metrics": report.key_findings if report else [],
            "sources": [{"url": s.url, "title": s.title, "snippet": s.snippet} for s in sources],
            "created_at": str(session.created_at) if session.created_at else "",
        }
    except Exception as e:
        print(f"⚠️ Error loading session: {e}")
        return None
    finally:
        db.close()


def list_sessions(limit: int = 10, offset: int = 0) -> list:
    """
    Returns a paginated list of past research sessions.
    """
    from sqlalchemy import desc
    db = SessionLocal()
    try:
        sessions = (
            db.query(ResearchSession)
            .order_by(desc(ResearchSession.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [
            {
                "id": s.id,
                "query": s.query,
                "status": s.status.value if s.status else "unknown",
                "quality_score": s.final_quality_score,
                "created_at": str(s.created_at),
            }
            for s in sessions
        ]
    except Exception as e:
        print(f"⚠️ Error listing sessions: {e}")
        return []
    finally:
        db.close()
