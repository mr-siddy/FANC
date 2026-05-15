import random
from collections import Counter
from tinyvm.generators import GenSpec, ShapingSpec, gen_counter, _allocate_registers
from tinyvm.interpreter import run
from tinyvm.verifier import validate


def test_shaping_spec_defaults_off():
    s = ShapingSpec()
    assert s.flat_output_histogram is False
    assert s.distractor_regs == 0
    assert s.randomize_print_target is False
    assert s.decorrelate_length is False


def test_gen_spec_holds_axis_dials_and_shaping():
    s = GenSpec(
        n=16, k=4, b=2, l=8, use_stack=True, stack_frames=1,
        shaping=ShapingSpec(distractor_regs=2),
    )
    assert s.n == 16 and s.k == 4 and s.b == 2 and s.l == 8
    assert s.use_stack is True and s.stack_frames == 1
    assert s.shaping.distractor_regs == 2


def test_gen_counter_program_has_correct_length():
    p = gen_counter(n=8, rng=random.Random(0))
    # n linear ops + 1 PRINT + 1 HALT.
    assert len(p.instructions) == 8 + 2


def test_gen_counter_uses_only_r0():
    p = gen_counter(n=8, rng=random.Random(0))
    for inst in p.instructions:
        for arg_idx, arg in enumerate(inst.args):
            # For LOAD the second arg is a literal; for ADD/SUB/NEG/MOV args
            # are register indices (except LOAD's second).
            if inst.op.name == "LOAD" and arg_idx == 1:
                continue
            assert arg == 0, f"{inst.op.name} uses non-R0 register: {inst.args}"


def test_gen_counter_property_validates_and_runs():
    for seed in range(50):
        p = gen_counter(n=8, rng=random.Random(seed))
        assert validate(p)
        trace = run(p)
        assert len(trace.output) == 1


def test_allocate_returns_k_distinct_registers():
    rng = random.Random(0)
    active = _allocate_registers(k=4, rng=rng)
    assert len(active) == 4
    assert len(set(active)) == 4
    assert all(0 <= r < 8 for r in active)


def test_allocate_is_uniformly_random_across_seeds():
    counts = Counter()
    for seed in range(2000):
        rng = random.Random(seed)
        for r in _allocate_registers(k=4, rng=rng):
            counts[r] += 1
    # Expected ~1000 occurrences per register if uniform; allow ±30%.
    for r in range(8):
        assert 700 < counts[r] < 1300, f"R{r}: {counts[r]} (non-uniform)"
