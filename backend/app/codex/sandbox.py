from __future__ import annotations

import re
from pathlib import PurePosixPath


class UnsafePatchError(ValueError):
    pass


def _safe_path(value: str) -> str:
    if not value or value == "/dev/null" or "\\" in value or value.startswith("/"):
        raise UnsafePatchError("unsafe patch path")
    path = PurePosixPath(value)
    if value in {".", ".."} or any(part in {"", ".", ".."} for part in path.parts):
        raise UnsafePatchError("unsafe patch path")
    normalized = path.as_posix()
    if normalized != value:
        raise UnsafePatchError("patch path is not normalized")
    return normalized


def validate_proposed_diff(diff: str, allowed_paths: tuple[str, ...], max_bytes: int) -> tuple[str, ...]:
    if not isinstance(diff, str) or not diff or not diff.strip():
        raise UnsafePatchError("diff must be nonempty")
    try:
        encoded = diff.encode("utf-8")
    except UnicodeEncodeError as error:
        raise UnsafePatchError("diff must be UTF-8") from error
    if max_bytes <= 0 or len(encoded) > max_bytes:
        raise UnsafePatchError("diff exceeds maximum size")
    forbidden = ("GIT binary patch", "Binary files ", "new file mode ", "deleted file mode ",
                 "rename from ", "rename to ", "copy from ", "copy to ",
                 "old mode ", "new mode ", "similarity index ", "dissimilarity index ")
    lines = diff.splitlines()
    if any(line.startswith(forbidden) for line in lines):
        raise UnsafePatchError("unsupported patch operation")
    header_indexes = [index for index, line in enumerate(lines) if line.startswith("diff --git ")]
    if not header_indexes:
        raise UnsafePatchError("diff must contain at least one file")
    paths: list[str] = []
    for position, header_index in enumerate(header_indexes):
        header = lines[header_index]
        match = re.fullmatch(r"diff --git a/(\S+) b/(\S+)", header)
        if match is None:
            raise UnsafePatchError("invalid diff header")
        old_path, new_path = (_safe_path(item) for item in match.groups())
        if old_path != new_path:
            raise UnsafePatchError("old and new paths must match")
        if old_path not in allowed_paths:
            raise UnsafePatchError("patch path is outside the allowlist")
        section_end = header_indexes[position + 1] if position + 1 < len(header_indexes) else len(lines)
        section = lines[header_index + 1:section_end]
        old_markers = [line[4:] for line in section if line.startswith("--- ")]
        new_markers = [line[4:] for line in section if line.startswith("+++ ")]
        if old_markers != [f"a/{old_path}"] or new_markers != [f"b/{new_path}"]:
            raise UnsafePatchError("diff file markers do not match header")
        if old_path not in paths:
            paths.append(old_path)
    for line in lines:
        if re.fullmatch(r"(?:old|new) mode 120000", line):
            raise UnsafePatchError("symlink patches are forbidden")
    return tuple(paths)
