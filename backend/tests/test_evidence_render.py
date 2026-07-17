from app.evidence import render_evidence_html
from app.store.models import FailureRow, PatchRow, RequirementRow, RunRow, StateTransitionRow, TestRow


def rows(patch_status="pending"):
    run = RunRow("RUN-001", "PATCH_PENDING", "fixture", "2026-07-12.1", "t0", "t1")
    provenance = {
        "producer": "fixture",
        "client": "FixtureLLMClient",
        "mode": "fixture",
        "validation_status": "validated",
        "schema_version": "2026-07-12.1",
        "source_artifact_ids": ["ART-001"],
        "created_at": "t0",
    }
    requirements = [RequirementRow("REQ-001", "RUN-001", "Must escape <script>", "balancing_rule", None, provenance)]
    tests = [TestRow("TEST-001", "RUN-001", "REQ-001", "test", "failed", "ART-006", provenance)]
    failures = [FailureRow("FAIL-001", "RUN-001", "REQ-001", "TEST-001", "REC-001", None, "100", "<b>bad</b>", "blocking", None, provenance)]
    patch = PatchRow(
        "PATCH-001",
        "RUN-001",
        ["FAIL-001"],
        "diff --git\n+<script>alert(1)</script>",
        patch_status,
        "melinda.emerson" if patch_status != "pending" else None,
        "t2" if patch_status != "pending" else None,
        "t3" if patch_status == "applied" else None,
        provenance,
    )
    matrix = [{"requirement_id": "REQ-001", "test_id": "TEST-001", "row_status": "patch_pending", "failure_ids": ["FAIL-001"], "patch_id": "PATCH-001", "evidence_refs": ["ART-006"]}]
    transitions = [StateTransitionRow(1, "RUN-001", None, "PATCH_PENDING", "api", "t1")]
    return dict(run=run, requirements=requirements, tests=tests, failures=failures, patch=patch, matrix=matrix, transitions=transitions)


def render(**overrides):
    data = rows()
    data.update(overrides)
    return render_evidence_html(**data)


def test_identical_input_objects_produce_byte_identical_html():
    assert render() == render()


def test_required_sections_are_present_and_ordered():
    html = render()
    sections = [
        "Release Assurance Evidence Pack",
        "Run provenance",
        "Summary",
        "Traceability matrix",
        "Failure evidence",
        "Proposed patch",
        "Decision record",
        "State transition audit trail",
    ]
    positions = [html.index(section) for section in sections]
    assert positions == sorted(positions)


def test_dynamic_html_characters_are_escaped():
    html = render()
    assert "&lt;script&gt;" in html
    assert "&lt;b&gt;bad&lt;/b&gt;" in html
    assert "<script>alert(1)</script>" not in html
    assert "<b>bad</b>" not in html


def test_pending_patch_renders_exact_pending_sentence():
    assert "Awaiting human decision. The proposed patch has not been applied and no rerun has occurred." in render()


def test_applied_patch_renders_decision_actor_time_and_applied_time():
    html = render(**rows("applied"))
    assert "Decision actor: melinda.emerson" in html
    assert "Decision time: t2" in html
    assert "Applied at: t3" in html


def test_transition_null_from_state_renders_none_and_fixture_sentence_present():
    html = render()
    assert "<td>none</td>" in html
    assert "Fixture evidence, no live model calls" in html


def test_live_evidence_is_not_labeled_as_fixture():
    data = rows()
    data["run"] = RunRow("RUN-002", "PATCH_PENDING", "live", "2026-07-12.1", "t0", "t1")
    html = render_evidence_html(**data)
    assert "Live evidence generated from validated GPT and Codex outputs" in html
    assert "Fixture evidence, no live model calls" not in html
