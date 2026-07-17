from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.llm.client import JsonObject

_FORMATS = {"run_id": re.compile(r"^RUN-[0-9]{3}$"), "patch_id": re.compile(r"^PATCH-[0-9]{3}$"),
            "failure_id": re.compile(r"^FAIL-[0-9]{3}$"), "artifact_id": re.compile(r"^ART-[0-9]{3}$")}


@dataclass(frozen=True)
class CodexProposalRequest:
    repo_path: Path
    run_id: str
    patch_id: str
    failure_ids: tuple[str, ...]
    allowed_paths: tuple[str, ...]
    source_artifact_ids: tuple[str, ...]
    schema_version: str
    created_at: str
    task_context: str
    attempt: int = 1

    def __post_init__(self) -> None:
        if self.attempt <= 0:
            raise ValueError("attempt must be positive")
        values = (("run_id", (self.run_id,)), ("patch_id", (self.patch_id,)),
                  ("failure_id", self.failure_ids), ("artifact_id", self.source_artifact_ids))
        for kind, identifiers in values:
            if any(_FORMATS[kind].fullmatch(identifier) is None for identifier in identifiers):
                raise ValueError(f"invalid {kind}")


class CodexClient(Protocol):
    def propose_patch(self, request: CodexProposalRequest) -> JsonObject:
        ...
