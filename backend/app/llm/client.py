from __future__ import annotations

from typing import Any, Protocol


JsonObject = dict[str, Any]


class LLMClient(Protocol):
    def extract_requirements(
        self,
        *,
        implementation_doc: str,
        run_id: str,
        source_artifact_ids: list[str],
    ) -> JsonObject:
        ...
