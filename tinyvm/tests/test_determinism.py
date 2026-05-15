"""Determinism layer (spec §10): same seed -> bit-exact program."""
import random

from tinyvm.generators import (
    GenSpec, gen_branched, gen_counter, gen_register_trace, gen_userop_trace,
)
from tinyvm.isa import Op, Instruction


def test_gen_counter_is_seed_deterministic():
    a = gen_counter(n=8, rng=random.Random(42))
    b = gen_counter(n=8, rng=random.Random(42))
    assert a == b


def test_gen_register_trace_is_seed_deterministic():
    a = gen_register_trace(n=16, k=4, rng=random.Random(42))
    b = gen_register_trace(n=16, k=4, rng=random.Random(42))
    assert a == b


def test_gen_branched_is_seed_deterministic():
    spec = GenSpec(n=32, k=4, b=2, l=6, use_stack=True, stack_frames=1)
    a = gen_branched(spec=spec, rng=random.Random(42))
    b = gen_branched(spec=spec, rng=random.Random(42))
    assert a == b


def test_different_seeds_yield_different_programs():
    a = gen_register_trace(n=16, k=4, rng=random.Random(1))
    b = gen_register_trace(n=16, k=4, rng=random.Random(2))
    assert a != b


def test_gen_userop_trace_is_seed_deterministic():
    decomp = [Instruction(Op.ADD, args=(0, 1, 1))]
    a = gen_userop_trace(
        opcode_spec={"name": "DOUBLE", "n_args": 2, "decomposition": decomp},
        k_demos=2, n_target=8, use_stack=False, rng=random.Random(42),
    )
    b = gen_userop_trace(
        opcode_spec={"name": "DOUBLE", "n_args": 2, "decomposition": decomp},
        k_demos=2, n_target=8, use_stack=False, rng=random.Random(42),
    )
    assert a.target.with_symbol == b.target.with_symbol
