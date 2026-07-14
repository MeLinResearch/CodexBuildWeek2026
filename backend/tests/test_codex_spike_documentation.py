from pathlib import Path
import re


SPIKE_DOC = Path(__file__).resolve().parents[1] / "app" / "codex" / "live_spike.md"

REQUIRED_CHECKS = [
    "codex exec runs non-interactively",
    "read-only inspection can be forced",
    "task context can be resumed or persisted",
    "structured output or artifact path is capturable",
    "can generate tests",
    "can run tests",
    "can propose a patch as a diff",
    "can switch to workspace-write only after approval",
]

REQUIRED_SECTIONS = [
    "Decision",
    "Fallback if blocked",
    "Commands attempted",
    "Do not implement LiveCodexClient until this spike is reviewed",
]

PLACEHOLDERS = ["TODO", "TBD", "fill in later", "lorem"]
STATUSES = {"PASS", "FAIL", "BLOCKED"}


def test_codex_spike_doc_exists_and_covers_architecture_checks():
    assert SPIKE_DOC.exists()

    text = SPIKE_DOC.read_text(encoding="utf-8")

    for required in REQUIRED_SECTIONS:
        assert required in text

    for check_number, check in enumerate(REQUIRED_CHECKS, start=1):
        assert f"### {check_number}. {check}" in text


def test_each_spike_check_has_exactly_one_status_marker():
    text = SPIKE_DOC.read_text(encoding="utf-8")

    check_pattern = re.compile(
        r"^### (?P<number>\d+)\. (?P<title>.+?)$"
        r"(?P<body>.*?)(?=^### \d+\. |^## Review notes\b)",
        re.MULTILINE | re.DOTALL,
    )
    sections = list(check_pattern.finditer(text))

    assert len(sections) == len(REQUIRED_CHECKS)

    for index, section in enumerate(sections, start=1):
        assert int(section.group("number")) == index
        assert section.group("title") == REQUIRED_CHECKS[index - 1]

        statuses = re.findall(r"^Status: (PASS|FAIL|BLOCKED)$", section.group("body"), re.MULTILINE)
        assert len(statuses) == 1
        assert statuses[0] in STATUSES


def test_codex_spike_doc_has_no_placeholders():
    text = SPIKE_DOC.read_text(encoding="utf-8")
    normalized = text.lower()

    for placeholder in PLACEHOLDERS:
        assert placeholder.lower() not in normalized
