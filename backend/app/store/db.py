from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Callable

from app import config
from app.store.models import (
    ArtifactRow,
    FailureRow,
    PatchRow,
    RequirementRow,
    RunMode,
    RunRow,
    RunState,
    StateTransitionRow,
    TestRow,
)

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def _json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _validate_provenance(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError("provenance must be a dict[str, Any]")
    if not all(isinstance(key, str) for key in value):
        raise TypeError("provenance keys must be strings")
    return value


def _validate_failure_ids(value: object) -> list[str]:
    if not isinstance(value, list):
        raise TypeError("failure_ids must be a list[str]")
    if not all(isinstance(item, str) for item in value):
        raise TypeError("failure_ids items must be strings")
    return value


def _json_loads(value: str) -> Any:
    return json.loads(value)


class Store:
    def __init__(
        self,
        db_path: Path | str | None = None,
        clock: Callable[[], str] = config.default_clock,
        id_generator: Callable[[str], str] | None = None,
    ):
        self.db_path = Path(db_path) if db_path is not None else config.DB_PATH
        self.clock = clock
        self.id_generator = id_generator or config.make_sequential_id_generator()

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(_SCHEMA_PATH.read_text())

    def insert_run(self, row: RunRow) -> RunRow:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO runs (run_id, state, mode, schema_version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (row.run_id, row.state, row.mode, row.schema_version, row.created_at, row.updated_at),
            )
        return row

    def create_run(
        self,
        mode: RunMode,
        schema_version: str,
        state: RunState = "CREATED",
        run_id: str | None = None,
    ) -> RunRow:
        at = self.clock()
        row = RunRow(
            run_id=run_id or self.id_generator("RUN"),
            state=state,
            mode=mode,
            schema_version=schema_version,
            created_at=at,
            updated_at=at,
        )
        return self.insert_run(row)

    def get_run(self, run_id: str) -> RunRow | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return self._run(row) if row else None

    def list_runs(self) -> list[RunRow]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM runs ORDER BY run_id").fetchall()
        return [self._run(row) for row in rows]

    def insert_state_transition(
        self, run_id: str, from_state: RunState | None, to_state: RunState, actor: str
    ) -> StateTransitionRow:
        at = self.clock()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO state_transitions (run_id, from_state, to_state, actor, at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, from_state, to_state, actor, at),
            )
            conn.execute(
                "UPDATE runs SET state = ?, updated_at = ? WHERE run_id = ?",
                (to_state, at, run_id),
            )
            row = conn.execute(
                "SELECT * FROM state_transitions WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
        return self._state_transition(row)

    def list_state_transitions(self, run_id: str) -> list[StateTransitionRow]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM state_transitions WHERE run_id = ? ORDER BY id", (run_id,)
            ).fetchall()
        return [self._state_transition(row) for row in rows]

    def insert_requirement(self, row: RequirementRow) -> RequirementRow:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO requirements (requirement_id, run_id, text, rule_type, tolerance, provenance)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (row.requirement_id, row.run_id, row.text, row.rule_type, row.tolerance, _json_dumps(_validate_provenance(row.provenance))),
            )
        return row

    def get_requirement(self, requirement_id: str) -> RequirementRow | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM requirements WHERE requirement_id = ?", (requirement_id,)).fetchone()
        return self._requirement(row) if row else None

    def list_requirements(self, run_id: str) -> list[RequirementRow]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM requirements WHERE run_id = ? ORDER BY requirement_id", (run_id,)).fetchall()
        return [self._requirement(row) for row in rows]

    def insert_test(self, row: TestRow) -> TestRow:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO tests (test_id, run_id, requirement_id, name, status, output_ref, provenance)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (row.test_id, row.run_id, row.requirement_id, row.name, row.status, row.output_ref, _json_dumps(_validate_provenance(row.provenance))),
            )
        return row

    def get_test(self, test_id: str) -> TestRow | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM tests WHERE test_id = ?", (test_id,)).fetchone()
        return self._test(row) if row else None

    def list_tests(self, run_id: str) -> list[TestRow]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM tests WHERE run_id = ? ORDER BY test_id", (run_id,)).fetchall()
        return [self._test(row) for row in rows]

    def insert_failure(self, row: FailureRow) -> FailureRow:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO failures (failure_id, run_id, requirement_id, test_id, record_id, field, expected, actual, severity, record_hash, provenance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (row.failure_id, row.run_id, row.requirement_id, row.test_id, row.record_id, row.field, row.expected, row.actual, row.severity, row.record_hash, _json_dumps(_validate_provenance(row.provenance))),
            )
        return row

    def get_failure(self, failure_id: str) -> FailureRow | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM failures WHERE failure_id = ?", (failure_id,)).fetchone()
        return self._failure(row) if row else None

    def list_failures(self, run_id: str) -> list[FailureRow]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM failures WHERE run_id = ? ORDER BY failure_id", (run_id,)).fetchall()
        return [self._failure(row) for row in rows]

    def insert_patch(self, row: PatchRow) -> PatchRow:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO patches (patch_id, run_id, failure_ids, diff, status, approved_by, approved_at, applied_at, provenance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (row.patch_id, row.run_id, _json_dumps(_validate_failure_ids(row.failure_ids)), row.diff, row.status, row.approved_by, row.approved_at, row.applied_at, _json_dumps(_validate_provenance(row.provenance))),
            )
        return row

    def get_patch(self, patch_id: str) -> PatchRow | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM patches WHERE patch_id = ?", (patch_id,)).fetchone()
        return self._patch(row) if row else None

    def list_patches(self, run_id: str) -> list[PatchRow]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM patches WHERE run_id = ? ORDER BY patch_id", (run_id,)).fetchall()
        return [self._patch(row) for row in rows]

    def insert_artifact(self, row: ArtifactRow) -> ArtifactRow:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO artifacts (artifact_id, run_id, kind, path, sha256, producer, mode, client, validation_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (row.artifact_id, row.run_id, row.kind, row.path, row.sha256, row.producer, row.mode, row.client, row.validation_status, row.created_at),
            )
        return row

    def get_artifact(self, artifact_id: str) -> ArtifactRow | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM artifacts WHERE artifact_id = ?", (artifact_id,)).fetchone()
        return self._artifact(row) if row else None

    def list_artifacts(self, run_id: str | None = None) -> list[ArtifactRow]:
        with self.connect() as conn:
            if run_id is None:
                rows = conn.execute("SELECT * FROM artifacts ORDER BY artifact_id").fetchall()
            else:
                rows = conn.execute("SELECT * FROM artifacts WHERE run_id = ? ORDER BY artifact_id", (run_id,)).fetchall()
        return [self._artifact(row) for row in rows]

    @staticmethod
    def _run(row: sqlite3.Row) -> RunRow:
        return RunRow(**dict(row))

    @staticmethod
    def _state_transition(row: sqlite3.Row) -> StateTransitionRow:
        return StateTransitionRow(**dict(row))

    @staticmethod
    def _requirement(row: sqlite3.Row) -> RequirementRow:
        data = dict(row)
        data["provenance"] = _json_loads(data["provenance"])
        return RequirementRow(**data)

    @staticmethod
    def _test(row: sqlite3.Row) -> TestRow:
        data = dict(row)
        data["provenance"] = _json_loads(data["provenance"])
        return TestRow(**data)

    @staticmethod
    def _failure(row: sqlite3.Row) -> FailureRow:
        data = dict(row)
        data["provenance"] = _json_loads(data["provenance"])
        return FailureRow(**data)

    @staticmethod
    def _patch(row: sqlite3.Row) -> PatchRow:
        data = dict(row)
        data["failure_ids"] = _json_loads(data["failure_ids"])
        data["provenance"] = _json_loads(data["provenance"])
        return PatchRow(**data)

    @staticmethod
    def _artifact(row: sqlite3.Row) -> ArtifactRow:
        return ArtifactRow(**dict(row))
