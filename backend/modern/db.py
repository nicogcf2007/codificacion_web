"""Portable SQLAlchemy schema. Additive, isolated from the legacy database."""
from __future__ import annotations
from pathlib import Path
from sqlalchemy import (MetaData, Table, Column, String, Text, Integer, Float,
                        Boolean, LargeBinary, JSON, ForeignKey, UniqueConstraint,
                        create_engine, event)
from sqlalchemy.pool import StaticPool

metadata = MetaData()
projects = Table("projects", metadata,
    Column("id", String(36), primary_key=True), Column("name", Text, nullable=False),
    Column("client", Text, nullable=False), Column("status", String(20), nullable=False),
    Column("created_at", String(40), nullable=False))
codebooks = Table("codebooks", metadata,
    Column("id", String(36), primary_key=True),
    Column("project_id", ForeignKey("projects.id"), nullable=False),
    Column("name", Text, nullable=False), Column("categories", JSON, nullable=False),
    Column("max_labels", Integer, nullable=False), Column("created_at", String(40), nullable=False))
# Source metadata is additive; manual and historical catalogs have no row here.
codebook_sources = Table("codebook_sources", metadata,
    Column("codebook_id", ForeignKey("codebooks.id"), primary_key=True),
    Column("filename", Text, nullable=False), Column("sheet", Text, nullable=False),
    Column("field_id", Text, nullable=False), Column("question_number", Text, nullable=False),
    Column("question_text", Text, nullable=False), Column("target_columns", JSON, nullable=False),
    Column("groupings", JSON, nullable=False))
surveys = Table("surveys", metadata,
    Column("id", String(36), primary_key=True),
    Column("project_id", ForeignKey("projects.id"), nullable=False),
    Column("filename", Text, nullable=False), Column("original", LargeBinary, nullable=False),
    Column("rows", JSON, nullable=False), Column("columns", JSON, nullable=False),
    Column("total_records", Integer, nullable=False), Column("created_at", String(40), nullable=False))
questions = Table("questions", metadata,
    Column("id", String(36), primary_key=True),
    Column("survey_id", ForeignKey("surveys.id"), nullable=False),
    Column("column_name", Text, nullable=False), Column("question_text", Text, nullable=False),
    Column("codebook_id", ForeignKey("codebooks.id"), nullable=False))
jobs = Table("coding_jobs", metadata,
    Column("id", String(36), primary_key=True),
    Column("project_id", ForeignKey("projects.id"), nullable=False),
    Column("survey_id", ForeignKey("surveys.id"), nullable=False),
    Column("name", Text, nullable=False), Column("status", String(20), nullable=False),
    Column("questions", JSON, nullable=False), Column("total_records", Integer, nullable=False),
    Column("processed_records", Integer, nullable=False, default=0),
    Column("provider_mode", String(20), nullable=False), Column("pause_reason", Text),
    Column("pause_requested", Boolean, nullable=False, default=False),
    Column("metrics", JSON, nullable=False), Column("active_seconds", Float, nullable=False, default=0),
    Column("created_at", String(40), nullable=False), Column("updated_at", String(40), nullable=False))
prototypes = Table("coding_prototypes", metadata,
    Column("id", String(36), primary_key=True),
    Column("ordinal", Integer, nullable=False),
    Column("job_id", ForeignKey("coding_jobs.id"), nullable=False),
    Column("question_id", String(36), nullable=False), Column("text", Text, nullable=False),
    Column("members", JSON, nullable=False), Column("state", String(20), nullable=False),
    Column("result", JSON), Column("attempts", Integer, nullable=False, default=0))
records = Table("coded_records", metadata,
    Column("id", String(36), primary_key=True),
    Column("job_id", ForeignKey("coding_jobs.id"), nullable=False),
    Column("question_id", String(36), nullable=False), Column("response_id", Integer, nullable=False),
    Column("column_name", Text, nullable=False), Column("text_original", Text, nullable=False),
    Column("codes", JSON, nullable=False), Column("confidence", Float),
    Column("was_grouped", Boolean, nullable=False),
    Column("prototype_id", ForeignKey("coding_prototypes.id")),
    Column("review_status", String(20), nullable=False), Column("review_reason", Text),
    UniqueConstraint("job_id", "question_id", "response_id"))
audit = Table("audit_events", metadata,
    Column("id", String(36), primary_key=True),
    Column("job_id", ForeignKey("coding_jobs.id"), nullable=False),
    Column("record_id", String(36)), Column("action", String(40), nullable=False),
    Column("payload", JSON, nullable=False), Column("created_at", String(40), nullable=False))

# Identity/session storage is additive: existing project/job/audit rows are untouched.
users = Table("auth_users", metadata,
    Column("id", String(36), primary_key=True),
    Column("email", String(254), nullable=False, unique=True),
    Column("name", String(240), nullable=False), Column("role", String(20), nullable=False),
    Column("active", Boolean, nullable=False), Column("must_change_password", Boolean, nullable=False),
    Column("password_hash", Text, nullable=False), Column("created_at", String(40), nullable=False))
sessions = Table("auth_sessions", metadata,
    Column("id", String(36), primary_key=True),
    Column("user_id", ForeignKey("auth_users.id"), nullable=False, index=True),
    Column("token_hash", String(64), nullable=False, unique=True),
    Column("csrf_hash", String(64), nullable=False),
    Column("expires_at", Float, nullable=False), Column("revoked", Boolean, nullable=False),
    Column("created_at", String(40), nullable=False))

login_attempts = Table("auth_login_attempts", metadata,
    Column("bucket", String(64), primary_key=True), Column("window_start", Float, nullable=False),
    Column("attempts", Integer, nullable=False))

activity = Table("activity_events", metadata,
    Column("id", String(36), primary_key=True), Column("actor_id", ForeignKey("auth_users.id")),
    Column("action", String(40), nullable=False), Column("resource_type", String(40), nullable=False),
    Column("resource_id", String(36)), Column("project_id", ForeignKey("projects.id")),
    Column("job_id", ForeignKey("coding_jobs.id")), Column("created_at", String(40), nullable=False))
audit_actors = Table("audit_event_actors", metadata,
    Column("event_id", ForeignKey("audit_events.id"), primary_key=True),
    Column("actor_id", ForeignKey("auth_users.id"), nullable=False))
job_actors = Table("job_execution_actors", metadata,
    Column("job_id", ForeignKey("coding_jobs.id"), primary_key=True),
    Column("actor_id", ForeignKey("auth_users.id"), nullable=False))

bootstrap_state = Table("auth_bootstrap_state", metadata,
    Column("id", String(40), primary_key=True))


def database(url: str):
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    kwargs = {"pool_pre_ping": True}
    if url.startswith("sqlite:"):
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
        if url.endswith(":memory:") or url == "sqlite://":
            kwargs["poolclass"] = StaticPool
        else:
            from sqlalchemy.engine import make_url
            Path(make_url(url).database).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, **kwargs)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def sqlite_settings(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")
    metadata.create_all(engine)
    return engine
