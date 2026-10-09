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
    topic = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    report_text = Column(Text, nullable=False)
    full_json = Column(Text, nullable=False) # Contains the raw Pydantic serialization of ResearchReport

engine = create_engine(f"sqlite:///{DB_PATH}")
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def save_report(topic: str, report_text: str, full_report_object: dict):
    """Save a final report to the SQLite database."""
    db = SessionLocal()
    try:
        new_report = ReportHistory(
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

def get_recent_reports(limit: int = 20) -> list[dict]:
    """Retrieve the most recent reports."""
    db = SessionLocal()
    try:
        results = db.query(ReportHistory).order_by(ReportHistory.created_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "topic": r.topic,
                "created_at": r.created_at.isoformat(),
                "report_text": r.report_text,
                "data": json.loads(r.full_json)
            }
            for r in results
        ]
    finally:
        db.close()
