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
