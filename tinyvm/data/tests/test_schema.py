import pytest

from tinyvm.data.schema import Row, RowMeta, RenderedPrompt
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
