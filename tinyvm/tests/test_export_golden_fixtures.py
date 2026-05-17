import json
from pathlib import Path

from tinyvm.scripts.export_golden_fixtures import build_fixtures, write_fixtures


def test_build_fixtures_is_idempotent_on_seed_sweep():
    a = build_fixtures()
    b = build_fixtures()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_build_fixtures_covers_each_generator():
    fixtures = build_fixtures()
    generators = {f["generator"] for f in fixtures}
    assert generators == {"gen_counter", "gen_register_trace", "gen_branched"}


def test_each_fixture_has_required_keys():
    for f in build_fixtures():
        assert {"seed", "generator", "spec", "source_text", "program_ir", "expected_trace"} <= f.keys()
        assert f["expected_trace"]["halted"] is True


def test_write_fixtures_writes_stable_json(tmp_path: Path):
    out = tmp_path / "golden.json"
    write_fixtures(out)
    a = out.read_text()
    write_fixtures(out)
    b = out.read_text()
    assert a == b


def test_branched_sweep_covers_combinations():
    by_bucket = {"sb": 0, "sl": 0, "bl": 0, "sbl": 0}
    for f in build_fixtures():
        if f["generator"] != "gen_branched":
            continue
        s = f["spec"]
        if s["use_stack"] and s["b"] > 0:
            by_bucket["sb"] += 1
        if s["use_stack"] and s["l"] > 0:
            by_bucket["sl"] += 1
        if s["b"] > 0 and s["l"] > 0:
            by_bucket["bl"] += 1
        if s["use_stack"] and s["b"] > 0 and s["l"] > 0:
            by_bucket["sbl"] += 1
    for bucket, n in by_bucket.items():
        assert n >= 1, f"no gen_branched fixture in bucket {bucket}"


def test_total_fixture_count_at_least_fifty():
    fixtures = build_fixtures()
    assert len(fixtures) >= 50, f"expected ~50 fixtures, got {len(fixtures)}"
