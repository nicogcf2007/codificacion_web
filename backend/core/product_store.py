"""Durable product data for projects, catalogs, jobs and human review.

The current coding pipeline still uses temporary session files.  This store adds a
small SQLite persistence boundary around the product features without changing
that pipeline's file format or provider behavior.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional


SPECIAL_CODES = {"77", "88", "99"}
MAX_CATALOG_ENTRIES = 254


class _SQLiteConnection(sqlite3.Connection):
    """Close SQLite handles when the context manager exits (important on Windows)."""

    def __exit__(self, *args: Any) -> Any:
        try:
            return super().__exit__(*args)
        finally:
            self.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _loads(value: Optional[str], default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def validate_catalog_entries(
    entries: Iterable[dict[str, Any]],
    *,
    multi_label: bool,
    max_labels: int,
) -> dict[str, Any]:
    """Validate an arbitrary survey catalog without inventing codes."""
    errors: list[str] = []
    warnings: list[str] = []
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    entries_list = list(entries)

    if not isinstance(max_labels, int) or isinstance(max_labels, bool) or max_labels < 1:
        errors.append("max_labels_must_be_positive")
    if not multi_label and max_labels != 1:
        errors.append("single_label_requires_max_labels_1")
    if len(entries_list) > MAX_CATALOG_ENTRIES:
        errors.append(f"too_many_entries:{MAX_CATALOG_ENTRIES}")

    for index, raw in enumerate(entries_list):
        if not isinstance(raw, dict):
            errors.append(f"entry_must_be_object:{index}")
            continue
        raw_code = raw.get("code")
        code = str(raw_code).strip() if raw_code is not None else ""
        label = str(raw.get("label", "")).strip()
        if not code:
            errors.append(f"empty_code:{index}")
            continue
        if len(code) > 32:
            errors.append(f"code_too_long:{code}")
        if code in seen:
            errors.append(f"duplicate_code:{code}")
        seen.add(code)
        if not label:
            errors.append(f"empty_label:{code}")

        examples = raw.get("examples", [])
        exclusions = raw.get("exclusions", [])
        if isinstance(examples, str):
            examples = [examples] if examples.strip() else []
        if isinstance(exclusions, str):
            exclusions = [exclusions] if exclusions.strip() else []
        if not isinstance(examples, list):
            errors.append(f"examples_must_be_list:{code}")
            examples = []
        if not isinstance(exclusions, list):
            errors.append(f"exclusions_must_be_list:{code}")
            exclusions = []

        normalized.append(
            {
                "code": code,
                "label": label,
                "description": str(raw.get("description", "")).strip(),
                "examples": [str(item).strip() for item in examples if str(item).strip()],
                "exclusions": [str(item).strip() for item in exclusions if str(item).strip()],
                "parent_code": str(raw.get("parent_code", "")).strip() or None,
            }
        )

    if "88" in seen and "99" in seen:
        warnings.append("special_codes_88_99_are_mutually_exclusive_at_decision_time")
    missing_special = sorted(SPECIAL_CODES - seen)
    if missing_special:
        warnings.append("special_codes_not_defined:" + ",".join(missing_special))

    parent_codes = {entry["code"] for entry in normalized}
    for entry in normalized:
        parent = entry["parent_code"]
        if parent and parent not in parent_codes:
            errors.append(f"parent_code_not_found:{entry['code']}:{parent}")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "entries": normalized,
    }


def validate_code_selection(codes: list[str], catalog: dict[str, Any]) -> list[str]:
    """Validate a final human decision against one catalog's modality."""
    normalized = [str(code).strip() for code in codes if str(code).strip()]
    errors: list[str] = []
    allowed = {str(entry.get("code", "")).strip() for entry in catalog.get("entries", [])}
    allowed.update(SPECIAL_CODES)
    unknown = sorted(set(normalized) - allowed)
    if unknown:
        errors.append(f"unknown_code:{','.join(unknown)}")
    if len(normalized) > int(catalog.get("max_labels", 1)):
        errors.append("max_labels_exceeded")
    if len(set(normalized)) != len(normalized):
        errors.append("duplicate_selected_code")
    special = set(normalized) & {"88", "99"}
    if len(special) > 1:
        errors.append("special_codes_88_99_mutually_exclusive")
    if special and len(normalized) > 1:
        errors.append("special_code_cannot_be_combined")
    if "77" in normalized and not bool(catalog.get("multi_label")) and len(normalized) > 1:
        errors.append("other_code_requires_multi_label")
    return errors


class ProductStore:
    """SQLite repository for the product-facing features."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30, factory=_SQLiteConnection)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS catalogs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    multi_label INTEGER NOT NULL DEFAULT 0,
                    max_labels INTEGER NOT NULL DEFAULT 1,
                    entries_json TEXT NOT NULL,
                    validation_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
                    session_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL DEFAULT 'CODING',
                    status TEXT NOT NULL,
                    progress REAL NOT NULL DEFAULT 0,
                    processed_records INTEGER NOT NULL DEFAULT 0,
                    total_records INTEGER NOT NULL DEFAULT 0,
                    config_json TEXT NOT NULL,
                    error TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS review_items (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                    source_row INTEGER NOT NULL,
                    source_column TEXT NOT NULL,
                    question TEXT NOT NULL DEFAULT '',
                    response TEXT NOT NULL DEFAULT '',
                    suggested_codes_json TEXT NOT NULL,
                    final_codes_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED',
                    confidence REAL,
                    reason TEXT NOT NULL DEFAULT '',
                    reviewer TEXT NOT NULL DEFAULT '',
                    comment TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(job_id, source_row, source_column)
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
                    job_id TEXT REFERENCES jobs(id) ON DELETE SET NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_catalogs_project ON catalogs(project_id, version DESC);
                CREATE INDEX IF NOT EXISTS idx_jobs_project ON jobs(project_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_review_items_job ON review_items(job_id, status, source_row);
                CREATE INDEX IF NOT EXISTS idx_audit_events_job ON audit_events(job_id, created_at);
                """
            )

    @staticmethod
    def _project(row: sqlite3.Row) -> dict[str, Any]:
        return dict(row)

    @staticmethod
    def _catalog(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["multi_label"] = bool(item["multi_label"])
        item["entries"] = _loads(item.pop("entries_json"), [])
        item["validation"] = _loads(item.pop("validation_json"), {})
        return item

    @staticmethod
    def _job(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["config"] = _loads(item.pop("config_json"), {})
        return item

    @staticmethod
    def _review_item(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["suggested_codes"] = _loads(item.pop("suggested_codes_json"), [])
        item["final_codes"] = _loads(item.pop("final_codes_json"), [])
        return item

    def _audit(
        self,
        connection: sqlite3.Connection,
        *,
        action: str,
        entity_type: str,
        entity_id: str,
        payload: dict[str, Any],
        project_id: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> None:
        connection.execute(
            """INSERT INTO audit_events
            (id, project_id, job_id, entity_type, entity_id, action, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), project_id, job_id, entity_type, entity_id, action, _json(payload), _now()),
        )

    def create_project(self, name: str, description: str = "") -> dict[str, Any]:
        name = name.strip()
        if not name:
            raise ValueError("project_name_required")
        project_id = str(uuid.uuid4())
        timestamp = _now()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO projects (id, name, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (project_id, name, description.strip(), timestamp, timestamp),
            )
            self._audit(
                connection,
                action="project_created",
                entity_type="project",
                entity_id=project_id,
                payload={"name": name},
                project_id=project_id,
            )
        return self.get_project(project_id)  # type: ignore[return-value]

    def list_projects(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT p.*, COUNT(DISTINCT c.id) AS catalog_count,
                       COUNT(DISTINCT j.id) AS job_count
                FROM projects p
                LEFT JOIN catalogs c ON c.project_id = p.id
                LEFT JOIN jobs j ON j.project_id = p.id
                GROUP BY p.id
                ORDER BY p.updated_at DESC
                """
            ).fetchall()
        return [self._project(row) for row in rows]

    def get_project(self, project_id: str) -> Optional[dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return self._project(row) if row else None

    def update_project(self, project_id: str, *, name: str, description: str = "") -> dict[str, Any]:
        name = name.strip()
        if not name:
            raise ValueError("project_name_required")
        timestamp = _now()
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE projects SET name = ?, description = ?, updated_at = ? WHERE id = ?",
                (name, description.strip(), timestamp, project_id),
            )
            if cursor.rowcount == 0:
                raise KeyError("project_not_found")
            self._audit(
                connection,
                action="project_updated",
                entity_type="project",
                entity_id=project_id,
                payload={"name": name},
                project_id=project_id,
            )
        return self.get_project(project_id)  # type: ignore[return-value]

    def delete_project(self, project_id: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            if cursor.rowcount == 0:
                raise KeyError("project_not_found")

    def create_catalog(
        self,
        project_id: str,
        name: str,
        entries: Iterable[dict[str, Any]],
        *,
        multi_label: bool = False,
        max_labels: int = 1,
    ) -> dict[str, Any]:
        if not self.get_project(project_id):
            raise KeyError("project_not_found")
        name = name.strip()
        if not name:
            raise ValueError("catalog_name_required")
        validation = validate_catalog_entries(entries, multi_label=multi_label, max_labels=max_labels)
        if not validation["valid"]:
            raise ValueError(_json(validation["errors"]))
        catalog_id = str(uuid.uuid4())
        timestamp = _now()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(version), 0) AS version FROM catalogs WHERE project_id = ? AND name = ?",
                (project_id, name),
            ).fetchone()
            version = int(row["version"]) + 1
            connection.execute(
                """INSERT INTO catalogs
                (id, project_id, name, version, multi_label, max_labels, entries_json,
                 validation_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    catalog_id,
                    project_id,
                    name,
                    version,
                    int(multi_label),
                    max_labels,
                    _json(validation["entries"]),
                    _json(validation),
                    timestamp,
                    timestamp,
                ),
            )
            connection.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (timestamp, project_id))
            self._audit(
                connection,
                action="catalog_created",
                entity_type="catalog",
                entity_id=catalog_id,
                payload={"name": name, "version": version, "entry_count": len(validation["entries"])},
                project_id=project_id,
            )
        return self.get_catalog(catalog_id)  # type: ignore[return-value]

    def list_catalogs(self, project_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM catalogs WHERE project_id = ? ORDER BY name, version DESC",
                (project_id,),
            ).fetchall()
        return [self._catalog(row) for row in rows]

    def get_catalog(self, catalog_id: str) -> Optional[dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM catalogs WHERE id = ?", (catalog_id,)).fetchone()
        return self._catalog(row) if row else None

    def update_catalog(
        self,
        catalog_id: str,
        *,
        name: str,
        entries: Iterable[dict[str, Any]],
        multi_label: bool,
        max_labels: int,
    ) -> dict[str, Any]:
        catalog = self.get_catalog(catalog_id)
        if not catalog:
            raise KeyError("catalog_not_found")
        name = name.strip()
        if not name:
            raise ValueError("catalog_name_required")
        validation = validate_catalog_entries(entries, multi_label=multi_label, max_labels=max_labels)
        if not validation["valid"]:
            raise ValueError(_json(validation["errors"]))
        timestamp = _now()
        new_catalog_id = str(uuid.uuid4())
        with self._connect() as connection:
            next_version = catalog["version"] + 1 if name.strip() == catalog["name"] else 1
            if name.strip() != catalog["name"]:
                row = connection.execute(
                    "SELECT COALESCE(MAX(version), 0) AS version FROM catalogs WHERE project_id = ? AND name = ?",
                    (catalog["project_id"], name.strip()),
                ).fetchone()
                next_version = int(row["version"]) + 1
            connection.execute(
                """INSERT INTO catalogs
                (id, project_id, name, version, multi_label, max_labels, entries_json,
                 validation_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    new_catalog_id,
                    catalog["project_id"],
                    name.strip(),
                    next_version,
                    int(multi_label),
                    max_labels,
                    _json(validation["entries"]),
                    _json(validation),
                    timestamp,
                    timestamp,
                ),
            )
            connection.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (timestamp, catalog["project_id"]))
            self._audit(
                connection,
                action="catalog_revision_created",
                entity_type="catalog",
                entity_id=new_catalog_id,
                payload={"name": name.strip(), "version": next_version, "previous_catalog_id": catalog_id, "entry_count": len(validation["entries"])},
                project_id=catalog["project_id"],
            )
        return self.get_catalog(new_catalog_id)  # type: ignore[return-value]

    def create_job(
        self,
        project_id: Optional[str],
        session_id: str,
        name: str,
        config: dict[str, Any],
        *,
        kind: str = "CODING",
        status: str = "QUEUED",
        total_records: int = 0,
    ) -> dict[str, Any]:
        if project_id and not self.get_project(project_id):
            raise KeyError("project_not_found")
        job_id = str(uuid.uuid4())
        timestamp = _now()
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO jobs
                (id, project_id, session_id, name, kind, status, progress,
                 processed_records, total_records, config_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?, ?, ?, ?)""",
                (job_id, project_id, session_id, name.strip() or "Trabajo sin nombre", kind, status, total_records, _json(config), timestamp, timestamp),
            )
            self._audit(
                connection,
                action="job_created",
                entity_type="job",
                entity_id=job_id,
                payload={"name": name, "kind": kind},
                project_id=project_id,
                job_id=job_id,
            )
        return self.get_job(job_id)  # type: ignore[return-value]

    def get_job(self, job_id: str) -> Optional[dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT j.*,
                   (SELECT COUNT(*) FROM review_items r WHERE r.job_id = j.id) AS review_count,
                   (SELECT COUNT(*) FROM review_items r WHERE r.job_id = j.id AND r.status = 'REVIEW_REQUIRED') AS pending_review_count
                   FROM jobs j WHERE j.id = ?""",
                (job_id,),
            ).fetchone()
        return self._job(row) if row else None

    def get_job_by_session(self, session_id: str) -> Optional[dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id FROM jobs WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
                (session_id,),
            ).fetchone()
        return self.get_job(row["id"]) if row else None

    def list_jobs(self, project_id: Optional[str] = None) -> list[dict[str, Any]]:
        query = """SELECT j.*,
                   (SELECT COUNT(*) FROM review_items r WHERE r.job_id = j.id) AS review_count,
                   (SELECT COUNT(*) FROM review_items r WHERE r.job_id = j.id AND r.status = 'REVIEW_REQUIRED') AS pending_review_count
                   FROM jobs j"""
        params: list[Any] = []
        if project_id:
            query += " WHERE j.project_id = ?"
            params.append(project_id)
        query += " ORDER BY j.created_at DESC"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._job(row) for row in rows]

    def update_job(self, job_id: str, **changes: Any) -> dict[str, Any]:
        allowed = {
            "status", "progress", "processed_records", "total_records", "error",
            "started_at", "completed_at", "name",
        }
        changes = {key: value for key, value in changes.items() if key in allowed}
        if not changes:
            job = self.get_job(job_id)
            if not job:
                raise KeyError("job_not_found")
            return job
        if "progress" in changes:
            changes["progress"] = max(0.0, min(1.0, float(changes["progress"])))
        changes["updated_at"] = _now()
        assignments = ", ".join(f"{key} = ?" for key in changes)
        job = self.get_job(job_id)
        if not job:
            raise KeyError("job_not_found")
        with self._connect() as connection:
            connection.execute(
                f"UPDATE jobs SET {assignments} WHERE id = ?",
                (*changes.values(), job_id),
            )
            self._audit(
                connection,
                action="job_updated",
                entity_type="job",
                entity_id=job_id,
                payload=changes,
                project_id=job.get("project_id"),
                job_id=job_id,
            )
        return self.get_job(job_id)  # type: ignore[return-value]

    def create_review_item(
        self,
        job_id: str,
        *,
        source_row: int,
        source_column: str,
        question: str,
        response: str,
        suggested_codes: list[str],
        reason: str,
        confidence: Optional[float] = None,
    ) -> dict[str, Any]:
        if not self.get_job(job_id):
            raise KeyError("job_not_found")
        item_id = str(uuid.uuid4())
        timestamp = _now()
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO review_items
                (id, job_id, source_row, source_column, question, response,
                 suggested_codes_json, final_codes_json, status, confidence, reason,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'REVIEW_REQUIRED', ?, ?, ?, ?)""",
                (
                    item_id,
                    job_id,
                    source_row,
                    source_column,
                    question,
                    response,
                    _json(suggested_codes),
                    _json(suggested_codes),
                    confidence,
                    reason,
                    timestamp,
                    timestamp,
                ),
            )
        return self.get_review_item(item_id)  # type: ignore[return-value]

    def get_review_item(self, item_id: str) -> Optional[dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM review_items WHERE id = ?", (item_id,)).fetchone()
        return self._review_item(row) if row else None

    def list_review_items(self, job_id: str, status: Optional[str] = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM review_items WHERE job_id = ?"
        params: list[Any] = [job_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY source_row, source_column"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._review_item(row) for row in rows]

    def update_review_item(
        self,
        item_id: str,
        *,
        status: str,
        final_codes: list[str],
        reviewer: str = "",
        comment: str = "",
    ) -> dict[str, Any]:
        allowed_statuses = {"ACCEPTED", "EDITED", "REJECTED", "REVIEW_REQUIRED"}
        if status not in allowed_statuses:
            raise ValueError("invalid_review_status")
        item = self.get_review_item(item_id)
        if not item:
            raise KeyError("review_item_not_found")
        job = self.get_job(item["job_id"])
        timestamp = _now()
        with self._connect() as connection:
            connection.execute(
                """UPDATE review_items SET status = ?, final_codes_json = ?, reviewer = ?,
                comment = ?, updated_at = ? WHERE id = ?""",
                (status, _json(final_codes), reviewer.strip(), comment.strip(), timestamp, item_id),
            )
            self._audit(
                connection,
                action="review_item_updated",
                entity_type="review_item",
                entity_id=item_id,
                payload={"status": status, "final_codes": final_codes, "reviewer": reviewer.strip()},
                project_id=job.get("project_id") if job else None,
                job_id=item["job_id"],
            )
        return self.get_review_item(item_id)  # type: ignore[return-value]

    def list_audit_events(
        self,
        *,
        project_id: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM audit_events"
        clauses: list[str] = []
        params: list[Any] = []
        if project_id:
            clauses.append("project_id = ?")
            params.append(project_id)
        if job_id:
            clauses.append("job_id = ?")
            params.append(job_id)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]
