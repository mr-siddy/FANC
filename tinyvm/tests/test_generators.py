import random
from collections import Counter
from tinyvm.generators import GenSpec, ShapingSpec, gen_counter, gen_register_trace, _allocate_registers, _emit_branch_if, _emit_branch_ifelse, _emit_branch_arith_zero, _LabelGen
from tinyvm.interpreter import run
from tinyvm.verifier import validate
from tinyvm.isa import Op, Instruction, Program


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


_OP_SCHEMA_FOR_FILL = {
    # Mirror of tokeniser._OP_ARG_SCHEMA for the ops fill_block can emit.
    Op.LOAD: (1, 1, False),
    Op.MOV: (2, 0, False),
    Op.ADD: (3, 0, False),
    Op.SUB: (3, 0, False),
    Op.MUL: (3, 0, False),
    Op.DIV: (3, 0, False),
    Op.NEG: (2, 0, False),
    Op.EQ: (3, 0, False),
    Op.LT: (3, 0, False),
}


def test_fill_block_produces_n_instructions_all_in_active_set():
    from tinyvm.generators import _fill_block

    active = [1, 3, 5, 7]
    insts = _fill_block(n=10, active=active, rng=random.Random(0))
    assert len(insts) == 10
    for inst in insts:
        # All register args must be in active.
        n_regs, n_lits, _has_target = _OP_SCHEMA_FOR_FILL[inst.op]
        for ri in inst.args[:n_regs]:
            assert ri in active, f"{inst.op.name} uses non-active reg {ri}"


def test_fill_block_excludes_reserved_registers():
    from tinyvm.generators import _fill_block

    active = [0, 1, 2]
    reserved = {1}
    insts = _fill_block(n=20, active=active, rng=random.Random(0), exclude=reserved)
    for inst in insts:
        n_regs, _, _ = _OP_SCHEMA_FOR_FILL[inst.op]
        # Destination register must NOT be in reserved.
        if n_regs >= 1:
            assert inst.args[0] not in reserved


def test_gen_register_trace_validates_and_outputs_one_value():
    for seed in range(20):
        for n in (8, 16, 32):
            for k in (2, 4, 8):
                p = gen_register_trace(n=n, k=k, rng=random.Random(seed))
                assert validate(p)
                trace = run(p)
                assert len(trace.output) == 1


def test_gen_register_trace_has_no_branches_or_loops():
    p = gen_register_trace(n=32, k=4, rng=random.Random(0))
    for inst in p.instructions:
        assert inst.op not in (Op.JZ, Op.JMP)


def test_loop_countdown_terminates_after_k_iterations():
    from tinyvm.generators import _emit_loop_countdown, _LabelGen

    label_gen = _LabelGen()
    counter, r_one = 0, 1
    body = [Instruction(Op.ADD, args=(2, 2, 2))]  # arbitrary body
    insts = _emit_loop_countdown(
        counter=counter, r_one=r_one, k=3, body=body, label_gen=label_gen,
    )
    prologue = [Instruction(Op.LOAD, args=(r_one, 1))]
    p = Program.build(tuple(prologue + insts + [Instruction(Op.HALT)]))
    trace = run(p)
    final_regs = trace.steps[-1].regs
    assert final_regs[counter] == 0


def test_loop_countup_executes_k_iterations():
    from tinyvm.generators import _emit_loop_countup, _LabelGen

    label_gen = _LabelGen()
    insts = _emit_loop_countup(
        counter=0, r_k=1, r_diff=2, r_one=3, k=4,
        body=[Instruction(Op.ADD, args=(4, 4, 3))],
        label_gen=label_gen,
    )
    prologue = [Instruction(Op.LOAD, args=(3, 1))]
    p = Program.build(tuple(prologue + insts + [Instruction(Op.HALT)]))
    trace = run(p)
    assert trace.steps[-1].regs[4] == 4


def test_loop_test_at_top_zero_iterations_skips_body():
    from tinyvm.generators import _emit_loop_test_at_top, _LabelGen

    label_gen = _LabelGen()
    insts = _emit_loop_test_at_top(
        counter=0, r_one=1, k=0,
        body=[Instruction(Op.ADD, args=(2, 2, 1))],
        label_gen=label_gen,
    )
    prologue = [Instruction(Op.LOAD, args=(1, 1))]
    p = Program.build(tuple(prologue + insts + [Instruction(Op.HALT)]))
    trace = run(p)
    assert trace.steps[-1].regs[2] == 0


def test_branch_if_executes_body_on_nonzero_condition():
    label_gen = _LabelGen()
    insts = _emit_branch_if(
        cmp_op=Op.LT, ri=0, rj=1, rc=2,
        then_block=[Instruction(Op.LOAD, args=(3, 99))],
        label_gen=label_gen,
    )
    prologue = [
        Instruction(Op.LOAD, args=(0, 1)),    # Ri=1
        Instruction(Op.LOAD, args=(1, 5)),    # Rj=5 -> Ri<Rj true -> Rc=1
    ]
    p = Program.build(tuple(prologue + insts + [Instruction(Op.HALT)]))
    trace = run(p)
    assert trace.steps[-1].regs[3] == 99


def test_branch_ifelse_executes_correct_arm():
    label_gen = _LabelGen()
    insts = _emit_branch_ifelse(
        cmp_op=Op.LT, ri=0, rj=1, rc=2,
        then_block=[Instruction(Op.LOAD, args=(3, 1))],
        else_block=[Instruction(Op.LOAD, args=(3, 2))],
        label_gen=label_gen,
    )
    prologue = [
        Instruction(Op.LOAD, args=(0, 5)),
        Instruction(Op.LOAD, args=(1, 1)),
    ]
    p = Program.build(tuple(prologue + insts + [Instruction(Op.HALT)]))
    trace = run(p)
    assert trace.steps[-1].regs[3] == 2


def test_branch_arith_zero_uses_sub_to_produce_zero():
    label_gen = _LabelGen()
    insts = _emit_branch_arith_zero(
        arith_op=Op.SUB, ri=0, rj=1, rc=2,
        then_block=[Instruction(Op.LOAD, args=(3, 7))],
        label_gen=label_gen,
    )
    prologue = [
        Instruction(Op.LOAD, args=(0, 5)),
        Instruction(Op.LOAD, args=(1, 5)),
    ]
    p = Program.build(tuple(prologue + insts + [Instruction(Op.HALT)]))
    trace = run(p)
    assert trace.steps[-1].regs[3] == 0  # then_block did not execute


def test_stack_pair_round_trips_value():
    from tinyvm.generators import _emit_stack_pair

    insts = _emit_stack_pair(
        save=0, load_back=1,
        body=[Instruction(Op.LOAD, args=(0, 99))],  # clobber R0
    )
    prologue = [Instruction(Op.LOAD, args=(0, 42))]
    p = Program.build(tuple(prologue + insts + [Instruction(Op.HALT)]))
    trace = run(p)
    assert trace.steps[-1].regs[1] == 42


def test_stack_nested_round_trips_in_lifo_order():
    from tinyvm.generators import _emit_stack_nested

    insts = _emit_stack_nested(
        saves=[0, 1], pops=[3, 2],
        body=[Instruction(Op.LOAD, args=(0, 0)), Instruction(Op.LOAD, args=(1, 0))],
    )
    prologue = [
        Instruction(Op.LOAD, args=(0, 5)),
        Instruction(Op.LOAD, args=(1, 7)),
    ]
    p = Program.build(tuple(prologue + insts + [Instruction(Op.HALT)]))
    trace = run(p)
    # LIFO: first POP gets R1's saved value (7), second POP gets R0's (5).
    assert trace.steps[-1].regs[3] == 7
    assert trace.steps[-1].regs[2] == 5
