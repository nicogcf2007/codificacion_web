"""Repository boundary; all SQL is parameterized via SQLAlchemy expressions."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Protocol, Any
from uuid import uuid4
from sqlalchemy import select, insert, update, func, union_all, case, literal
from contextlib import contextmanager
from fastapi import HTTPException
from . import db


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def identity():
    return str(uuid4())


def record_activity(conn, actor_id, action, resource_type, resource_id=None, project_id=None, job_id=None):
    # Explicit identifier-only allowlist; never persist request bodies or PII.
    conn.execute(insert(db.activity).values(id=identity(), actor_id=actor_id, action=action,
        resource_type=resource_type, resource_id=resource_id, project_id=project_id,
        job_id=job_id, created_at=now()))


class _TransactionEngine:
    """Reuse an outer transaction without changing results.py or global state."""
    def __init__(self, connection):
        self.connection = connection

    @contextmanager
    def begin(self):
        yield self.connection

    connect = begin


class IProjectRepository(Protocol):
    def list_projects(self) -> list[dict[str, Any]]: ...
    def create_project(self, name: str, client: str) -> dict[str, Any]: ...


class ICodingJobRepository(Protocol):
    def get_job(self, job_id: str) -> dict[str, Any]: ...
    def list_jobs(self, project_id: str | None = None) -> list[dict[str, Any]]: ...


class Repository:
    def __init__(self, engine):
        self.engine = engine

    def require(self, table, id, connection=None):
        if connection is None:
            with self.engine.connect() as conn:
                return self.require(table, id, conn)
        row = connection.execute(select(table).where(table.c.id == id)).mappings().first()
        if row is None:
            raise KeyError("Recurso no encontrado")
        return dict(row)

    def list_projects(self):
        with self.engine.connect() as conn:
            result = []
            for row in conn.execute(select(db.projects).order_by(db.projects.c.created_at.desc())).mappings():
                item = dict(row)
                item["survey_count"] = conn.scalar(select(func.count()).select_from(db.surveys).where(db.surveys.c.project_id == item["id"]))
                item["job_count"] = conn.scalar(select(func.count()).select_from(db.jobs).where(db.jobs.c.project_id == item["id"]))
                result.append(item)
            return result

    def create_project(self, name, client, actor_id=None):
        item = dict(id=identity(), name=name, client=client, status="ACTIVE", created_at=now())
        with self.engine.begin() as conn:
            conn.execute(insert(db.projects).values(**item))
            record_activity(conn, actor_id, 'project_created', 'project', item['id'], item['id'])
        return {**item, "survey_count": 0, "job_count": 0}


    def execution_actor(self, job_id, connection=None):
        if connection is None:
            with self.engine.connect() as conn:
                return self.execution_actor(job_id, conn)
        return connection.scalar(select(db.job_actors.c.actor_id).where(db.job_actors.c.job_id == job_id))

    def audited_review(self, actor_id, job_id, operation, *args):
        with self.engine.begin() as conn:
            # Serialize with other reviews/start before capturing the exact
            # new legacy audit IDs. SQLite and PostgreSQL both lock on UPDATE.
            changed = conn.execute(update(db.jobs).where(db.jobs.c.id == job_id,
                db.jobs.c.status != 'RUNNING').values(updated_at=db.jobs.c.updated_at)).rowcount
            if not changed:
                self.require(db.jobs, job_id, conn)
                raise HTTPException(409, 'Pause el trabajo antes de revisar')
            before = set(conn.scalars(select(db.audit.c.id).where(db.audit.c.job_id == job_id)))
            result = operation(Repository(_TransactionEngine(conn)), job_id, *args)
            after = set(conn.scalars(select(db.audit.c.id).where(db.audit.c.job_id == job_id)))
            new_ids = after - before
            # Minimize only the newly authored legacy decisions in this same
            # transaction. Historical payloads remain intact and unattributed.
            for event_id in new_ids:
                event = self.require(db.audit, event_id, conn)
                safe = {key: [code for code in event['payload'].get(key, [])
                              if isinstance(code, str) and len(code) == 2 and code.isascii() and code.isdigit()]
                        for key in ('before', 'after')}
                conn.execute(update(db.audit).where(db.audit.c.id == event_id).values(payload=safe))
            links = [{'event_id': event_id, 'actor_id': actor_id} for event_id in new_ids]
            if links:
                conn.execute(insert(db.audit_actors), links)
            return result

    def audit_events(self, limit=50, offset=0):
        current = select(db.activity.c.id, db.activity.c.actor_id,
            db.users.c.name.label('actor_name'), db.users.c.email.label('actor_email'),
            db.activity.c.action, db.activity.c.resource_type, db.activity.c.resource_id,
            db.activity.c.project_id, db.activity.c.job_id, db.activity.c.created_at).select_from(
                db.activity.outerjoin(db.users, db.activity.c.actor_id == db.users.c.id))
        legacy = select(db.audit.c.id, db.audit_actors.c.actor_id,
            db.users.c.name.label('actor_name'), db.users.c.email.label('actor_email'), db.audit.c.action,
            case((db.audit.c.record_id.is_not(None), literal('record')), else_=literal('job')).label('resource_type'),
            func.coalesce(db.audit.c.record_id, db.audit.c.job_id).label('resource_id'),
            db.jobs.c.project_id, db.audit.c.job_id, db.audit.c.created_at).select_from(
                db.audit.join(db.jobs, db.audit.c.job_id == db.jobs.c.id)
                .outerjoin(db.audit_actors, db.audit.c.id == db.audit_actors.c.event_id)
                .outerjoin(db.users, db.audit_actors.c.actor_id == db.users.c.id))
        events = union_all(current, legacy).subquery()
        with self.engine.connect() as conn:
            total = conn.scalar(select(func.count()).select_from(events))
            rows = conn.execute(select(events).order_by(events.c.created_at.desc(), events.c.id.desc()).offset(offset).limit(limit)).mappings()
            return {'events': [dict(row) for row in rows], 'total': total}

    def overview(self):
        with self.engine.connect() as conn:
            counts = {key: conn.scalar(select(func.count()).select_from(table))
                      for key, table in [('projects', db.projects), ('jobs', db.jobs), ('users', db.users)]}
            counts['active_jobs'] = conn.scalar(select(func.count()).select_from(db.jobs).where(db.jobs.c.status == 'RUNNING'))
            counts['completed_jobs'] = conn.scalar(select(func.count()).select_from(db.jobs).where(db.jobs.c.status == 'COMPLETED'))
            return counts
