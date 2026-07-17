from pathlib import Path
import pytest
from app.pipeline.live_pipeline import LiveInputError, LiveRunInputs, validate_inputs


def test_live_inputs_reject_traversal_before_a_run_is_created():
    with pytest.raises(LiveInputError):
        validate_inputs(LiveRunInputs(Path("../implementation.md"), Path("fixtures/a.csv"), Path("fixtures/a.json")))
