import pytest

from app.codex.sandbox import UnsafePatchError, validate_proposed_diff

DIFF = "diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-old\n+new\n"


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
