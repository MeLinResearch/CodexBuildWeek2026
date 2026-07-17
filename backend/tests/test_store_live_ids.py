from app.store.db import Store


def test_persisted_id_allocation_advances_across_instances(tmp_path):
    path = tmp_path / "store.sqlite"
    first = Store(path); first.init_schema()
    first.create_run("live", "v", run_id="RUN-002")
    second = Store(path); second.init_schema()
    assert second.allocate_id("RUN", start=2) == "RUN-003"


def test_id_allocation_rejects_invalid_requests(tmp_path):
    store = Store(tmp_path / "store.sqlite"); store.init_schema()
    for prefix, count in (("NOPE", 1), ("RUN", 0)):
        try: store.allocate_ids(prefix, count)
        except ValueError: pass
        else: raise AssertionError("invalid allocation accepted")
