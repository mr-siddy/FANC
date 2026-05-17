import pytest

from tinyvm.data.schema import Row, RowMeta, RenderedPrompt, to_row
from tinyvm.isa import Op, Instruction, Program
from tinyvm.interpreter import ExecutionTrace, StepRecord


def test_rendered_prompt_is_frozen():
    rp = RenderedPrompt(input_ids=[1, 2], target_ids=[3], input_text="hi", target_text="bye")
    with pytest.raises((AttributeError, TypeError)):
        rp.input_ids = [99]  # type: ignore[misc]


def test_rendered_prompt_holds_four_fields():
    rp = RenderedPrompt(
        input_ids=[0, 47, 1],
        target_ids=[0, 39, 1],
        input_text="LOAD R0 5",
        target_text="5",
    )
    assert rp.input_ids == [0, 47, 1]
    assert rp.target_ids == [0, 39, 1]
    assert rp.input_text == "LOAD R0 5"
    assert rp.target_text == "5"


def test_row_meta_is_frozen():
    meta = RowMeta(
        tier="tier1", split="train", bucket=None, seed=42,
        axes={"n": 16, "k": 4}, renders=("direct",),
    )
    with pytest.raises((AttributeError, TypeError)):
        meta.tier = "tier2"  # type: ignore[misc]


def test_row_meta_renders_is_tuple():
    meta = RowMeta(
        tier="tier2", split="train", bucket=None, seed=0,
        axes={}, renders=("direct", "cot"),
    )
    assert meta.renders == ("direct", "cot")
    assert isinstance(meta.renders, tuple)


def test_row_namedtuple_has_four_fields():
    p = Program.build((Instruction(Op.HALT),))
    trace = ExecutionTrace(steps=[], output=[], halted=True)
    meta = RowMeta(tier="tier0", split="train", bucket=None, seed=0,
                   axes={}, renders=("direct",))
    rp = RenderedPrompt(input_ids=[], target_ids=[], input_text="", target_text="")
    row = Row(program=p, trace=trace, meta=meta, renders={"direct": rp})
    assert row.program is p
    assert row.trace is trace
    assert row.meta is meta
    assert row.renders == {"direct": rp}


def test_to_row_serialises_meta_program_trace_renders():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 5)),
        Instruction(Op.PRINT, args=(0,)),
        Instruction(Op.HALT),
    ))
    trace = ExecutionTrace(
        steps=[
            StepRecord(pc=0, regs=(5, 0, 0, 0, 0, 0, 0, 0), stack=(), emitted=None),
            StepRecord(pc=1, regs=(5, 0, 0, 0, 0, 0, 0, 0), stack=(), emitted=5),
            StepRecord(pc=2, regs=(5, 0, 0, 0, 0, 0, 0, 0), stack=(), emitted=None),
        ],
        output=[5],
        halted=True,
    )
    meta = RowMeta(tier="tier0", split="train", bucket=None, seed=42,
                   axes={"n": 3}, renders=("direct",))
    rp = RenderedPrompt(
        input_ids=[0, 47, 1, 5, 13, 1, 15, 56],
        target_ids=[0, 39, 1, 56],
        input_text="LOAD R0 5\nPRINT R0\nHALT",
        target_text="5",
    )
    out = to_row(p, trace, meta, {"direct": rp})
    # Top-level keys.
    assert set(out.keys()) == {"meta", "program", "trace", "renders"}
    # Meta.
    assert out["meta"]["tier"] == "tier0"
    assert out["meta"]["seed"] == 42
    assert out["meta"]["renders"] == ["direct"]      # tuple -> list under json
    # Program: list of instruction dicts; Op serialised by name.
    assert out["program"][0] == {"op": "LOAD", "args": [0, 5], "label": None, "target": None}
    assert out["program"][2] == {"op": "HALT", "args": [], "label": None, "target": None}
    # Trace: per-step record + output + halted.
    assert out["trace"]["output"] == [5]
    assert out["trace"]["halted"] is True
    assert out["trace"]["steps"][1] == {
        "pc": 1, "regs": [5, 0, 0, 0, 0, 0, 0, 0], "stack": [], "emitted": 5,
    }
    # Renders.
    assert out["renders"]["direct"]["input_text"] == "LOAD R0 5\nPRINT R0\nHALT"


def test_to_row_output_is_json_serialisable():
    import json
    p = Program.build((Instruction(Op.HALT),))
    trace = ExecutionTrace(steps=[
        StepRecord(pc=0, regs=(0,) * 8, stack=(), emitted=None),
    ], output=[], halted=True)
    meta = RowMeta(tier="tier0", split="train", bucket=None, seed=0,
                   axes={}, renders=())
    out = to_row(p, trace, meta, {})
    # json.dumps must not raise.
    s = json.dumps(out)
    assert isinstance(s, str)


import random
from tinyvm.data.schema import from_row


def test_from_row_inverts_to_row_on_simple_case():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 5)),
        Instruction(Op.HALT),
    ))
    trace = ExecutionTrace(steps=[
        StepRecord(pc=0, regs=(5,) + (0,) * 7, stack=(), emitted=None),
        StepRecord(pc=1, regs=(5,) + (0,) * 7, stack=(), emitted=None),
    ], output=[], halted=True)
    meta = RowMeta(tier="tier0", split="train", bucket=None, seed=0,
                   axes={"n": 2}, renders=("direct",))
    rp = RenderedPrompt(input_ids=[1, 2], target_ids=[3], input_text="x", target_text="y")

    out = to_row(p, trace, meta, {"direct": rp})
    recovered = from_row(out)

    assert recovered.program == p
    assert recovered.trace.output == trace.output
    assert recovered.trace.steps == trace.steps
    assert recovered.trace.halted == trace.halted
    assert recovered.meta == meta
    assert recovered.renders == {"direct": rp}


def test_from_row_handles_labels_and_jumps():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 0), label="ENTRY"),
        Instruction(Op.JZ, args=(0,), target="ENTRY"),
        Instruction(Op.HALT),
    ))
    trace = ExecutionTrace(steps=[
        StepRecord(pc=0, regs=(0,) * 8, stack=(), emitted=None),
    ], output=[], halted=True)
    meta = RowMeta(tier="tier1", split="eval", bucket="len_8", seed=99,
                   axes={"n": 3, "k": 1}, renders=())
    out = to_row(p, trace, meta, {})
    recovered = from_row(out)
    assert recovered.program == p
    assert recovered.program.instructions[0].label == "ENTRY"
    assert recovered.program.instructions[1].target == "ENTRY"


def test_round_trip_on_generated_programs():
    """Round-trip property: from_row(to_row(...)) reconstructs everything bit-exactly."""
    from tinyvm.generators import gen_register_trace, gen_counter, gen_branched, GenSpec
    from tinyvm.interpreter import run

    cases = []
    for seed in range(20):
        for gen in [
            lambda s: gen_counter(n=6, rng=random.Random(s)),
            lambda s: gen_register_trace(n=12, k=3, rng=random.Random(s)),
            lambda s: gen_branched(
                spec=GenSpec(n=16, k=4, b=1, l=0, use_stack=False, stack_frames=0),
                rng=random.Random(s),
            ),
        ]:
            p = gen(seed)
            trace = run(p)
            cases.append(p)

    for p in cases:
        trace = run(p)
        meta = RowMeta(tier="tier0", split="train", bucket=None, seed=0,
                       axes={}, renders=())
        out = to_row(p, trace, meta, {})
        recovered = from_row(out)
        assert recovered.program == p
        assert recovered.trace.steps == trace.steps
        assert recovered.trace.output == trace.output
        assert recovered.trace.halted == trace.halted
