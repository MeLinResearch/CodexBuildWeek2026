# Planted Defects

1. Leading-zero truncation: REQ-001 / TEST-001 / FAIL-001 detects account IDs int-coerced instead of preserving account identifiers verbatim.
2. Branch-level sign inversion: REQ-002 / TEST-002 / FAIL-002 detects Branch 101 debits 1,250.00, credits 1,200.00, Difference 50.00.
3. Silent date default: REQ-003 / TEST-003 / FAIL-003 detects unparseable dates coerced to 1900-01-01 instead of rejected.
