from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from app import config
from app.codex.sandbox import validate_proposed_diff
from app.store.db import Store
from app.store.models import ArtifactRow, PatchRow


class LiveRerunError(RuntimeError):
    pass


def _run(command: list[str], cwd: Path, *, timeout: int = 60,
         env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False,
                                shell=False, timeout=timeout, env=env)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise LiveRerunError("disposable rerun command could not complete") from error
    if result.returncode != 0:
        raise LiveRerunError(result.stderr.strip() or "disposable rerun command failed")
    return result


def _tree(workspace: Path) -> str:
    _run(["git", "add", "reconcile/migration.py"], workspace)
    return _run(["git", "write-tree"], workspace).stdout.strip()


def _source_for_rerun(store: Store, run_id: str, mode: str) -> Path:
    if mode == "fixture":
        source = config.REPO_ROOT / "fixtures/source_data/accounts.csv"
        missing_message = "fixture source artifact is missing"
    else:
        artifacts = store.list_artifacts(run_id)
        source_artifact = next(
            (row for row in artifacts if row.kind == "input" and row.path.endswith(".csv")),
            None,
        )
        source = config.REPO_ROOT / source_artifact.path if source_artifact is not None else None
        missing_message = "live source artifact is missing"

    if source is None or source.is_symlink() or not source.is_file():
        raise LiveRerunError(missing_message)
    try:
        source.resolve().relative_to(config.REPO_ROOT.resolve())
    except ValueError as error:
        raise LiveRerunError(f"{mode} source artifact is outside the repository") from error

    if mode == "live":
        assert source_artifact is not None
        if hashlib.sha256(source.read_bytes()).hexdigest() != source_artifact.sha256:
            raise LiveRerunError("live source artifact hash does not match")
    return source


def apply_and_verify_patch(store: Store, patch: PatchRow) -> dict[str, object]:
    run = store.get_run(patch.run_id)
    if run is None or run.state != "PATCH_APPROVED" or patch.status != "approved":
        raise LiveRerunError("patch is not approved for rerun")
    try:
        validate_proposed_diff(patch.diff, ("reconcile/migration.py",), config.CODEX_MAX_DIFF_BYTES)
    except ValueError as error:
        raise LiveRerunError("approved patch failed safety validation") from error
    source = _source_for_rerun(store, run.run_id, run.mode)
    original = config.REPO_ROOT / "reconcile/migration.py"
    original_hash = hashlib.sha256(original.read_bytes()).hexdigest()

    try:
        with tempfile.TemporaryDirectory(prefix=f"release-assurance-{run.run_id}-") as temporary:
            workspace = Path(temporary)
            target = workspace / "reconcile/migration.py"
            target.parent.mkdir(parents=True)
            shutil.copy2(original, target)
            _run(["git", "init", "--quiet"], workspace)
            pre_tree = _tree(workspace)
            patch_path = workspace / f"{patch.patch_id}.diff"
            patch_path.write_text(patch.diff, encoding="utf-8")
            _run(["git", "apply", "--check", patch_path.name], workspace)
            _run(["git", "apply", patch_path.name], workspace)
            post_tree = _tree(workspace)
            verifier = Path(__file__).with_name("repair_verifier.py")
            verifier_env = {"PATH": os.defpath, "PYTHONIOENCODING": "utf-8"}
            verified = _run(
                [sys.executable, "-I", str(verifier), str(target), str(source)],
                workspace,
                env=verifier_env,
            )
            try:
                result = json.loads(verified.stdout)
            except json.JSONDecodeError as error:
                raise LiveRerunError("repair verifier returned invalid output") from error
    finally:
        if hashlib.sha256(original.read_bytes()).hexdigest() != original_hash:
            raise LiveRerunError("repository migration target changed during disposable rerun")

    artifact_id = store.allocate_id("ART", start=10)
    report = {
        "run_id": run.run_id,
        "patch_id": patch.patch_id,
        "artifact_id": artifact_id,
        "status": "passed",
        "pre_apply_tree": pre_tree,
        "post_apply_tree": post_tree,
        **result,
    }
    report_path = config.LIVE_RUNS_DIR / run.run_id / "rerun_result.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    store.insert_artifact(ArtifactRow(artifact_id, run.run_id, "test_output",
        report_path.relative_to(config.REPO_ROOT).as_posix(), hashlib.sha256(report_path.read_bytes()).hexdigest(),
        "deterministic", run.mode, "none", "not_required", store.clock()))
    for test in store.list_tests(run.run_id):
        store.set_test_result(test.test_id, "passed", artifact_id)
    provenance = {**patch.provenance,
                  "source_artifact_ids": [*patch.provenance.get("source_artifact_ids", []), artifact_id]}
    store.set_patch_application(patch.patch_id, "applied", provenance)
    return report
