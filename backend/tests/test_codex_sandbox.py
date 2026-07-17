import json
from pathlib import Path

import pytest

from app.codex.sandbox import UnsafePatchError, validate_proposed_diff

DIFF = "diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-old\n+new\n"
ROOT = Path(__file__).resolve().parents[2]


def test_valid_diff_returns_paths_once():
    assert validate_proposed_diff(DIFF + DIFF, ("app.py",), 10000) == ("app.py",)


@pytest.mark.parametrize("diff", [
    "diff --git a/app.py b/other.py\n", "diff --git a/../app.py b/../app.py\n",
    "diff --git a/app.py b/app.py\nGIT binary patch\n",
    "diff --git a/app.py b/app.py\nrename from app.py\nrename to other.py\n",
    "diff --git a/app.py b/app.py\nnew file mode 100644\n",
    "diff --git a/app.py b/app.py\ndeleted file mode 100644\n",
    "diff --git a/app.py b/app.py\nold mode 100644\nnew mode 100755\n",
    "diff --git a/app.py b/app.py\nold mode 120000\n",
])
def test_rejects_unsafe_operations(diff):
    with pytest.raises(UnsafePatchError):
        validate_proposed_diff(diff, ("app.py",), 10000)


def test_rejects_outside_allowlist_and_oversize():
    with pytest.raises(UnsafePatchError):
        validate_proposed_diff(DIFF, ("other.py",), 10000)
    with pytest.raises(UnsafePatchError):
        validate_proposed_diff(DIFF, ("app.py",), 2)


def test_rejects_file_markers_that_do_not_match_header():
    disguised = DIFF.replace("--- a/app.py", "--- a/secrets.txt").replace(
        "+++ b/app.py", "+++ b/secrets.txt"
    )
    with pytest.raises(UnsafePatchError, match="file markers"):
        validate_proposed_diff(disguised, ("app.py",), 10000)


@pytest.mark.parametrize("prefix", [
    "--- /dev/null\n+++ b/hidden.py\n@@ -0,0 +1 @@\n+import os\n",
    "From abc123\n",
    "\n",
])
def test_rejects_content_before_first_diff_header(prefix):
    migration_diff = (
        "diff --git a/migration.py b/migration.py\n"
        "--- a/migration.py\n"
        "+++ b/migration.py\n"
        "@@ -1 +1 @@\n"
        "-x = 1\n"
        "+x = 2\n"
    )

    with pytest.raises(UnsafePatchError, match="diff must begin with a file header"):
        validate_proposed_diff(prefix + migration_diff, ("migration.py",), 10000)


def test_canonical_fixture_patch_still_validates_unchanged():
    fixture_path = ROOT / "fixtures/api/patch_PATCH-001.fixture.json"
    fixture = json.loads(fixture_path.read_text())

    assert validate_proposed_diff(
        fixture["diff"], ("reconcile/migration.py",), 100000
    ) == ("reconcile/migration.py",)
