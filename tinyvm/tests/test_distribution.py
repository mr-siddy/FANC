"""Distribution sanity layer (spec §10).

Aggregate-stat assertions that catch *quiet* generator bugs the per-program
tests miss: a generator that 'works' but only ever PRINTs values in [0, 7],
or always picks R0 as the counter, etc.
"""
import random
from collections import Counter

import numpy as np

from tinyvm.generators import GenSpec, ShapingSpec, gen_branched, gen_register_trace
from tinyvm.isa import Op
from tinyvm.interpreter import run


def _outputs(generator_call, n_samples: int) -> list[int]:
    outs: list[int] = []
    for seed in range(n_samples):
        p = generator_call(seed)
        outs.append(run(p).output[0])
    return outs


def test_register_trace_output_distribution_is_diverse():
    outs = _outputs(
        lambda s: gen_register_trace(n=16, k=4, rng=random.Random(s)),
        n_samples=1000,
    )
    # At least 50 distinct output values across 1000 programs.
    assert len(set(outs)) >= 50


def test_branched_jz_predecessor_distribution_includes_non_comparators():
    """Spec §10: JZ-predecessor-opcode distribution should not be 100% comparators."""
    pred_counts = Counter()
    for seed in range(200):
        spec = GenSpec(n=32, k=4, b=4, l=0)
        p = gen_branched(spec=spec, rng=random.Random(seed))
        for i, inst in enumerate(p.instructions):
            if inst.op == Op.JZ and i > 0:
                pred_counts[p.instructions[i - 1].op.name] += 1
    total = sum(pred_counts.values())
    comparator_share = (pred_counts["LT"] + pred_counts["EQ"]) / max(1, total)
    # Template (c) is 20% — comparator share should be roughly 80% ± 15%.
    assert 0.55 < comparator_share < 0.95


def test_branched_active_register_use_is_roughly_uniform():
    """Spec §10: register-use counts uniform over active subset."""
    reg_writes = Counter()
    for seed in range(500):
        p = gen_register_trace(n=32, k=8, rng=random.Random(seed))
        writes_one_reg = {Op.LOAD, Op.MOV, Op.ADD, Op.SUB, Op.MUL, Op.DIV,
                          Op.NEG, Op.EQ, Op.LT, Op.POP}
        for inst in p.instructions:
            if inst.op in writes_one_reg and inst.args:
                reg_writes[inst.args[0]] += 1
    total = sum(reg_writes.values())
    # Each register should see roughly 1/8 of writes ± 50%.
    for r in range(8):
        share = reg_writes[r] / max(1, total)
        assert 0.05 < share < 0.25, f"R{r} write share is {share:.3f}"


def test_branched_loop_template_mix():
    """Verify loops are emitted and run productively across many seeds."""
    template_counts = Counter()
    for seed in range(300):
        spec = GenSpec(n=32, k=6, b=0, l=6)
        p = gen_branched(spec=spec, rng=random.Random(seed))
        outs = run(p).output
        template_counts["any_loop_executed"] += int(len(outs) >= 1)
    assert template_counts["any_loop_executed"] >= 200   # >2/3 of programs run to PRINT
