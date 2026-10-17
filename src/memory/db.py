"""SQLite Database for persistent session history.

Saves full ResearchReport outputs so they can be loaded later.
"""
import os
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

DB_PATH = "research_history.db"
Base = declarative_base()

class ReportHistory(Base):
    __tablename__ = 'reports'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, index=True, default="anonymous")
    topic = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    report_text = Column(Text, nullable=False)
    full_json = Column(Text, nullable=False) # Contains the raw Pydantic serialization of ResearchReport

engine = create_engine(f"sqlite:///{DB_PATH}")
Base.metadata.create_all(engine)

# Graceful SQLite migration check to ensure user_id column exists
try:
    with engine.connect() as conn:
        from sqlalchemy import text
        conn.execute(text("ALTER TABLE reports ADD COLUMN user_id VARCHAR DEFAULT 'anonymous'"))
        conn.commit()
except Exception:
    pass

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def save_report(topic: str, report_text: str, full_report_object: dict, user_id: str = "anonymous"):
    """Save a final report to the SQLite database with user attribution."""
    db = SessionLocal()
    try:
        new_report = ReportHistory(
            user_id=user_id or "anonymous",
            topic=topic,
            report_text=report_text,
            full_json=json.dumps(full_report_object)
        )
        db.add(new_report)
        db.commit()
    except Exception as e:
        print(f"⚠️ Failed to save report to DB: {e}")
        db.rollback()
    finally:
        db.close()

def get_recent_reports(user_id: str | None = None, limit: int = 20) -> list[dict]:
    """Retrieve the most recent reports, optionally filtered by user_id for multi-tenant isolation."""
    db = SessionLocal()
    try:
        query = db.query(ReportHistory)
        if user_id:
            query = query.filter(ReportHistory.user_id == user_id)
        results = query.order_by(ReportHistory.created_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "user_id": getattr(r, 'user_id', 'anonymous'),
                "topic": r.topic,
                "created_at": r.created_at.isoformat(),
                "report_text": r.report_text,
                "data": json.loads(r.full_json)
            }
            for r in results
        ]
    finally:
        db.close()
