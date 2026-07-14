from __future__ import annotations

from reconcile.heuristic import propose_mapping


def test_exact_normalized_match_maps_to_same_field():
    schema = {"fields": {"email": {"type": "email", "required": True}}}
    assert propose_mapping(sample=[{"E-Mail": "jane@example.com"}], target_schema=schema) == {
        "email": {"source": "E-Mail", "type": "email"}
    }


def test_supported_synonym_match_maps_using_existing_synonym():
    schema = {"fields": {"amount": {"type": "number", "required": False}}}
    assert propose_mapping(sample=[{"amt": "10"}], target_schema=schema) == {
        "amount": {"source": "amt", "type": "number"}
    }


def test_unknown_fields_are_not_hallucinated_into_unrelated_required_targets():
    schema = {"fields": {"email": {"type": "email", "required": True}}}
    assert propose_mapping(sample=[{"favorite_color": "blue"}], target_schema=schema) == {
        "email": {"source": None, "type": "email"}
    }


def test_short_source_fields_do_not_match_email_by_generic_substring():
    schema = {"fields": {"email": {"type": "email", "required": True}}}
    assert propose_mapping(sample=[{"e": "jane@example.com"}], target_schema=schema) == {
        "email": {"source": None, "type": "email"}
    }
    assert propose_mapping(sample=[{"em": "jane@example.com"}], target_schema=schema) == {
        "email": {"source": None, "type": "email"}
    }


def test_environment_api_keys_do_not_change_deterministic_mapping(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-anthropic-key")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-openai-key")
    schema = {
        "fields": {
            "email": {"type": "email", "required": True},
            "amount": {"type": "number", "required": False},
            "active": {"type": "boolean", "required": False},
        }
    }
    sample = [{"contactemail": "jane@example.com", "amt": "12", "enabled": "yes"}]
    expected = {
        "email": {"source": "contactemail", "type": "email"},
        "amount": {"source": "amt", "type": "number"},
        "active": {"source": "enabled", "type": "boolean"},
    }

    first = propose_mapping(sample=sample, target_schema=schema)
    second = propose_mapping(sample=sample, target_schema=schema)

    assert first == expected
    assert second == expected
    assert first == second
