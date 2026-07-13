PRAGMA foreign_keys = ON;

CREATE TABLE runs (
  run_id TEXT PRIMARY KEY,
  state TEXT NOT NULL CHECK (state IN (
    'CREATED','INGESTED','MANIFEST_READY','TESTS_GENERATED','EXECUTED',
    'TRIAGED','PATCH_PENDING','PATCH_APPROVED','PATCH_REJECTED',
    'RERUNNING','EVIDENCE_READY','DONE','FAILED'
  )),
  mode TEXT NOT NULL CHECK (mode IN ('live','fixture')),
  schema_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE state_transitions (
  id INTEGER PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  from_state TEXT CHECK (
    from_state IS NULL OR from_state IN (
      'CREATED','INGESTED','MANIFEST_READY','TESTS_GENERATED','EXECUTED',
      'TRIAGED','PATCH_PENDING','PATCH_APPROVED','PATCH_REJECTED',
      'RERUNNING','EVIDENCE_READY','DONE','FAILED'
    )
  ),
  to_state TEXT NOT NULL CHECK (to_state IN (
    'CREATED','INGESTED','MANIFEST_READY','TESTS_GENERATED','EXECUTED',
    'TRIAGED','PATCH_PENDING','PATCH_APPROVED','PATCH_REJECTED',
    'RERUNNING','EVIDENCE_READY','DONE','FAILED'
  )),
  actor TEXT NOT NULL,
  at TEXT NOT NULL
);

CREATE TABLE requirements (
  requirement_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  text TEXT NOT NULL,
  rule_type TEXT NOT NULL CHECK (rule_type IN (
    'field_validation','balancing_rule','exception_handling','mapping_rule','tolerance_rule'
  )),
  tolerance TEXT,
  provenance TEXT NOT NULL CHECK (json_valid(provenance))
);

CREATE TABLE tests (
  test_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  requirement_id TEXT NOT NULL REFERENCES requirements(requirement_id),
  name TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending','passed','failed','skipped')),
  output_ref TEXT,
  provenance TEXT NOT NULL CHECK (json_valid(provenance))
);

CREATE TABLE failures (
  failure_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  requirement_id TEXT NOT NULL REFERENCES requirements(requirement_id),
  test_id TEXT NOT NULL REFERENCES tests(test_id),
  record_id TEXT NOT NULL,
  field TEXT,
  expected TEXT NOT NULL,
  actual TEXT,
  severity TEXT NOT NULL CHECK (severity IN ('blocking','warning','info')),
  record_hash TEXT,
  provenance TEXT NOT NULL CHECK (json_valid(provenance))
);

CREATE TABLE patches (
  patch_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  failure_ids TEXT NOT NULL CHECK (json_valid(failure_ids)),
  diff TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending','approved','rejected','applied','apply_failed')),
  approved_by TEXT,
  approved_at TEXT,
  applied_at TEXT,
  provenance TEXT NOT NULL CHECK (json_valid(provenance))
);

CREATE TABLE artifacts (
  artifact_id TEXT PRIMARY KEY,
  run_id TEXT REFERENCES runs(run_id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK (kind IN (
    'input','raw_model_output','validated_model_output','test_output',
    'patch_diff','evidence_html','evidence_pdf','log'
  )),
  path TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  producer TEXT NOT NULL CHECK (producer IN ('gpt-5.6','codex','deterministic','fixture')),
  mode TEXT NOT NULL CHECK (mode IN ('live','fixture')),
  client TEXT NOT NULL,
  validation_status TEXT NOT NULL CHECK (validation_status IN (
    'not_required','quarantined','validated','rejected'
  )),
  created_at TEXT NOT NULL
);

CREATE INDEX idx_requirements_run_id ON requirements(run_id);
CREATE INDEX idx_tests_run_id ON tests(run_id);
CREATE INDEX idx_failures_run_id ON failures(run_id);
CREATE INDEX idx_patches_run_id ON patches(run_id);
CREATE INDEX idx_artifacts_run_id ON artifacts(run_id);
