import json
from pathlib import Path
from tinyvm.scripts.export_comparison_bundle import build_bundle, write_bundle


def test_build_bundle_emits_v1_schema():
    bundle = build_bundle(
        generator="gen_counter",
        seed=0,
        generator_kwargs={"n": 4},
        prediction_output=[7],
    )
    assert bundle["schema"] == "tinyvm-viz/comparison/v1"
    assert bundle["meta"]["seed"] == 0
    assert "source" in bundle
    assert bundle["groundTruth"]["trace"]["halted"] is True
    assert bundle["prediction"]["output"] == [7]


def test_write_bundle_roundtrips_json(tmp_path: Path):
    out = tmp_path / "b.json"
    write_bundle(out, generator="gen_counter", seed=0, generator_kwargs={"n": 4}, prediction_output=[1])
    data = json.loads(out.read_text())
    assert data["schema"] == "tinyvm-viz/comparison/v1"
