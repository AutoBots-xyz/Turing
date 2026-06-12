"""
database/models.py — SQLAlchemy ORM Models

Fixes Error 8 (Batch 4): This file was completely empty.
Defines the SQLAlchemy table models for persisting Run sessions and their results.
"""
import json
from datetime import datetime

from sqlalchemy import Column, String, Float, DateTime, Text, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base — imported by database.py to create all tables."""
    pass


class RunModel(Base):
    """
    Persists a single analysis session.

    Mirrors the Pydantic `Run` schema in schemas/run.py but is stored in
    SQLite (default) or PostgreSQL (production).

    JSON blobs (causal_graph, top_bridges) are serialised as TEXT so the
    schema works with any SQL backend without requiring JSONB.
    """
    __tablename__ = "runs"

    id            = Column(String(36),  primary_key=True, index=True)
    status        = Column(SAEnum("PENDING", "RUNNING", "COMPLETE", "FAILED", name="run_status"),
                           default="PENDING", nullable=False)
    input_file    = Column(String(512), nullable=False)
    input_type    = Column(String(32),  nullable=False)   # "csv" | "text"
    created_at    = Column(DateTime,    default=datetime.utcnow, nullable=False)
    updated_at    = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    causal_graph  = Column(Text,        nullable=True)    # JSON-serialised CausalGraph
    top_bridges   = Column(Text,        nullable=True)    # JSON-serialised List[RankedBridge]
    error_message = Column(Text,        nullable=True)

    def set_causal_graph(self, graph_dict: dict):
        self.causal_graph = json.dumps(graph_dict)

    def get_causal_graph(self) -> dict | None:
        return json.loads(self.causal_graph) if self.causal_graph else None

    def set_top_bridges(self, bridges: list):
        self.top_bridges = json.dumps(bridges)

    def get_top_bridges(self) -> list | None:
        return json.loads(self.top_bridges) if self.top_bridges else None

    def __repr__(self):
        return f"<RunModel id={self.id} status={self.status} file={self.input_file}>"
