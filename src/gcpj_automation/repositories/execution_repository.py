"""SQLite audit trail for local executions."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from ..models import ExecutionMode, ItemResult


class ExecutionRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS executions (
                    execution_id TEXT PRIMARY KEY,
                    mode TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    total_items INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    report_path TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS execution_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT NOT NULL,
                    row_number INTEGER NOT NULL,
                    npc TEXT NOT NULL,
                    ato TEXT NOT NULL,
                    gcpj_reason TEXT NOT NULL,
                    item_status TEXT NOT NULL,
                    message TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL,
                    evidence_path TEXT,
                    result_json TEXT NOT NULL,
                    FOREIGN KEY (execution_id) REFERENCES executions(execution_id)
                );
                CREATE INDEX IF NOT EXISTS idx_execution_items_execution
                    ON execution_items(execution_id);
                CREATE INDEX IF NOT EXISTS idx_execution_items_npc
                    ON execution_items(npc);
                """
            )

    def start_execution(
        self,
        execution_id: str,
        mode: ExecutionMode,
        started_at: datetime,
        total_items: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO executions
                    (execution_id, mode, started_at, total_items, status, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    execution_id,
                    mode.value,
                    started_at.isoformat(timespec="seconds"),
                    total_items,
                    "EM_EXECUCAO",
                    json.dumps(metadata or {}, ensure_ascii=False, default=str),
                ),
            )

    def save_item(self, execution_id: str, result: ItemResult) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO execution_items
                    (execution_id, row_number, npc, ato, gcpj_reason, item_status,
                     message, started_at, finished_at, evidence_path, result_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    execution_id,
                    result.row_number,
                    result.npc,
                    result.ato,
                    result.gcpj_reason,
                    result.status.value,
                    result.message,
                    result.started_at.isoformat(timespec="seconds"),
                    result.finished_at.isoformat(timespec="seconds"),
                    result.evidence_path,
                    json.dumps(result.to_record(), ensure_ascii=False, default=str),
                ),
            )

    def finish_execution(
        self,
        execution_id: str,
        finished_at: datetime,
        status: str,
        report_path: str = "",
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE executions
                SET finished_at = ?, status = ?, report_path = ?
                WHERE execution_id = ?
                """,
                (finished_at.isoformat(timespec="seconds"), status, report_path, execution_id),
            )

    def recent_executions(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT execution_id, mode, started_at, finished_at, total_items,
                       status, report_path
                FROM executions
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
