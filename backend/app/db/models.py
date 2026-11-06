"""Run history persistence (SQLite, JSON payloads)."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.db.session import Database

@dataclass
class RunRecord:
    """One stored simulation run."""

    id: str
    created_at: str
    kind: str
    label: str
    T_metal_C: float
    Q_platen_MW: float
    m_tph: float
    T_in_C: float
    T_out_C: float
    warnings: list[str]
    payload: dict[str, Any]

    def summary(self) -> dict[str, Any]:
        """Summary fields exposed by the history endpoints."""
        return {
            "id": self.id,
            "created_at": self.created_at,
            "kind": self.kind,
            "label": self.label,
            "T_metal_C": self.T_metal_C,
            "Q_platen_MW": self.Q_platen_MW,
            "m_tph": self.m_tph,
            "T_in_C": self.T_in_C,
            "T_out_C": self.T_out_C,
            "warnings": self.warnings,
        }

    def detail(self) -> dict[str, Any]:
        """Summary plus the full payload."""
        return {**self.summary(), "payload": self.payload}


class RunStore:
    """Persistence facade for simulation runs."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def save(
        self,
        kind: str,
        label: str,
        summary: dict[str, Any],
        payload: dict[str, Any],
    ) -> RunRecord:
        """Store a run and return the persisted record."""
        run_id = uuid.uuid4().hex
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        warnings = list(summary.get("warnings") or [])
        record = RunRecord(
            id=run_id,
            created_at=created_at,
            kind=kind,
            label=label,
            T_metal_C=float(summary.get("T_metal_C", 0.0)),
            Q_platen_MW=float(summary.get("Q_platen_MW", 0.0)),
            m_tph=float(summary.get("m_tph", 0.0)),
            T_in_C=float(summary.get("T_in_C", 0.0)),
            T_out_C=float(summary.get("T_out_C", 0.0)),
            warnings=warnings,
            payload=payload,
        )
        with self.database.connection() as connection:
            connection.execute(
                """
                INSERT INTO runs (id, created_at, kind, label, T_metal_C, Q_platen_MW,
                                  m_tph, T_in_C, T_out_C, warnings, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.created_at,
                    record.kind,
                    record.label,
                    record.T_metal_C,
                    record.Q_platen_MW,
                    record.m_tph,
                    record.T_in_C,
                    record.T_out_C,
                    json.dumps(record.warnings, ensure_ascii=False),
                    json.dumps(record.payload, ensure_ascii=False),
                ),
            )
        return record

    def get(self, run_id: str) -> RunRecord | None:
        """Fetch one run by id."""
        with self.database.connection() as connection:
            row = connection.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return self._from_row(row) if row else None

    def list(self, limit: int = 50) -> list[RunRecord]:
        """Most recent runs first."""
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def delete(self, run_id: str) -> bool:
        """Delete a stored run; returns False when it did not exist."""
        with self.database.connection() as connection:
            cursor = connection.execute("DELETE FROM runs WHERE id = ?", (run_id,))
        return cursor.rowcount > 0

    def count(self) -> int:
        """Number of stored runs."""
        with self.database.connection() as connection:
            row = connection.execute("SELECT COUNT(*) AS n FROM runs").fetchone()
        return int(row["n"]) if row else 0

    def ensure_baseline(self) -> None:
        """Seed a design baseline so the previous_run mode works on a fresh install."""
        if self.count() > 0:
            return
        self.save(
            kind="baseline",
            label="Design baseline (1000 t/h, 167 bar, 540 \u00b0C)",
            summary={
                "T_metal_C": 572.5,
                "Q_platen_MW": 60.0,
                "m_tph": 1000.0,
                "T_in_C": 490.0,
                "T_out_C": 540.0,
                "warnings": [
                    "Seeded design baseline: replace it with a commissioned measurement when available."
                ],
            },
            payload={
                "note": "baseline",
                "P_bar": 167.0,
                "T_main_C": 540.0,
                "m_spray_tph": 0.0,
                "T_metal_C": 572.5,
                "Q_platen_MW": 60.0,
            },
        )

    @staticmethod
    def _from_row(row: Any) -> RunRecord:
        return RunRecord(
            id=row["id"],
            created_at=row["created_at"],
            kind=row["kind"],
            label=row["label"],
            T_metal_C=float(row["T_metal_C"]),
            Q_platen_MW=float(row["Q_platen_MW"]),
            m_tph=float(row["m_tph"]),
            T_in_C=float(row["T_in_C"]),
            T_out_C=float(row["T_out_C"]),
            warnings=json.loads(row["warnings"] or "[]"),
            payload=json.loads(row["payload"] or "{}"),
        )
