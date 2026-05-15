from tinyvm.tokeniser import (
    VOCAB_SIZE, TOKEN_TO_ID, ID_TO_TOKEN, OPCODE_TOKENS, REGISTER_TOKENS,
    DIGIT_TOKENS, MINUS, L_MARKER, COLON, EQUALS, DECOMP, NEWLINE,
    BOS, EOS, PAD, QUERY, USEROP_TOKENS, encode, render_direct, render_cot,
)
from tinyvm.isa import Op, Instruction, Program


def test_vocab_size_is_64():
    assert VOCAB_SIZE == 64


def test_token_id_round_trip():
    for tok, tid in TOKEN_TO_ID.items():
        assert ID_TO_TOKEN[tid] == tok


def test_token_id_assignments_are_dense():
    ids = sorted(TOKEN_TO_ID.values())
    assert ids == list(range(len(TOKEN_TO_ID)))


def test_opcode_tokens_cover_16_base_ops():
    base_ops = [op for op in Op if not op.is_userop()]
    assert len(base_ops) == 16
    for op in base_ops:
        assert op.name in OPCODE_TOKENS


def test_register_tokens_R0_through_R7():
    assert REGISTER_TOKENS == [f"R{i}" for i in range(8)]


def test_digit_tokens_0_through_9():
    assert DIGIT_TOKENS == [str(i) for i in range(10)]


def test_userop_tokens_have_five_reserved():
    assert len(USEROP_TOKENS) == 5


def test_special_tokens_exist():
    for tok in (MINUS, L_MARKER, COLON, EQUALS, DECOMP, NEWLINE, BOS, EOS, PAD, QUERY):
        assert tok in TOKEN_TO_ID


def _ids(*tokens: str) -> list[int]:
    return [TOKEN_TO_ID[t] for t in tokens]


def test_encode_load_with_negative_literal():
    p = Program.build((Instruction(Op.LOAD, args=(3, -42)),))
    ids = encode(p)
    assert ids == _ids("LOAD", "R3", "MINUS", "4", "2", "NEWLINE")


def test_encode_three_arg_arithmetic():
    p = Program.build((Instruction(Op.ADD, args=(0, 1, 2)),))
    assert encode(p) == _ids("ADD", "R0", "R1", "R2", "NEWLINE")


def test_encode_jz_with_label_reference():
    p = Program.build((Instruction(Op.JZ, args=(1,), target="L7"),))
    assert encode(p) == _ids("JZ", "R1", "L", "7", "NEWLINE")


def test_encode_label_definition_inline():
    p = Program.build((
        Instruction(Op.ADD, args=(0, 1, 2), label="L3"),
    ))
    assert encode(p) == _ids("L", "3", "COLON", "ADD", "R0", "R1", "R2", "NEWLINE")


def test_encode_print():
    p = Program.build((Instruction(Op.PRINT, args=(0,)),))
    assert encode(p) == _ids("PRINT", "R0", "NEWLINE")


def test_encode_userop_instruction_uses_symbol():
    p = Program.build((Instruction(Op.USEROP_0, args=(1, 0)),))
    assert encode(p) == _ids("DOUBLE", "R1", "R0", "NEWLINE")


import random
from tinyvm.tokeniser import decode
from tinyvm.interpreter import run


def test_decode_simple_load():
    ids = _ids("LOAD", "R3", "MINUS", "4", "2", "NEWLINE")
    p = decode(ids)
    assert len(p.instructions) == 1
    assert p.instructions[0] == Instruction(Op.LOAD, args=(3, -42))


def test_decode_labeled_jmp():
    ids = _ids("L", "3", "COLON", "JMP", "L", "3", "NEWLINE")
    p = decode(ids)
    assert p.instructions[0].label == "L3"
    assert p.instructions[0].op == Op.JMP
    assert p.instructions[0].target == "L3"


def test_round_trip_random_programs():
    """decode(encode(p)) == p for any well-formed generator output."""
    rng = random.Random(0)
    for _ in range(200):
        n = rng.randint(1, 10)
        insts: list[Instruction] = []
        for _ in range(n):
            choice = rng.choice([
                Instruction(Op.LOAD, args=(rng.randint(0, 7), rng.randint(-127, 127))),
                Instruction(Op.ADD, args=(rng.randint(0, 7), rng.randint(0, 7), rng.randint(0, 7))),
                Instruction(Op.MOV, args=(rng.randint(0, 7), rng.randint(0, 7))),
                Instruction(Op.PRINT, args=(rng.randint(0, 7),)),
                Instruction(Op.NOP),
                Instruction(Op.HALT),
            ])
            insts.append(choice)
        p = Program.build(tuple(insts))
        assert decode(encode(p)) == p


def test_render_direct_input_is_bos_program_eos():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 3)),
        Instruction(Op.PRINT, args=(0,)),
        Instruction(Op.HALT),
    ))
    trace = run(p)
    inp, tgt = render_direct(p, trace)
    assert inp[0] == TOKEN_TO_ID[BOS]
    assert inp[-1] == TOKEN_TO_ID[EOS]
    assert inp[1:-1] == encode(p)


def test_render_direct_target_is_print_value_stream():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 3)),
        Instruction(Op.PRINT, args=(0,)),
        Instruction(Op.LOAD, args=(0, -5)),
        Instruction(Op.PRINT, args=(0,)),
        Instruction(Op.HALT),
    ))
    trace = run(p)
    _, tgt = render_direct(p, trace)
    expected = [TOKEN_TO_ID[BOS]] + _ids("3", "NEWLINE", "MINUS", "5", "NEWLINE") + [TOKEN_TO_ID[EOS]]
    assert tgt == expected


def test_render_cot_full_emits_all_8_registers_per_step():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 5)),
        Instruction(Op.PRINT, args=(0,)),
        Instruction(Op.HALT),
    ))
    trace = run(p)
    inp, tgt = render_cot(p, trace, mode="full")
    tgt_toks = [ID_TO_TOKEN[i] for i in tgt]
    assert tgt_toks.count(EQUALS) == 8 * len(trace.steps)


def test_render_cot_modified_emits_only_changed_registers():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 5)),    # changes R0
        Instruction(Op.NOP),                  # changes nothing
        Instruction(Op.HALT),                 # changes nothing
    ))
    trace = run(p)
    inp, tgt = render_cot(p, trace, mode="modified")
    tgt_toks = [ID_TO_TOKEN[i] for i in tgt]
    assert tgt_toks.count(EQUALS) == 1


def test_render_cot_input_matches_render_direct_input():
    p = Program.build((Instruction(Op.LOAD, args=(0, 1)), Instruction(Op.HALT)))
    trace = run(p)
    inp_cot, _ = render_cot(p, trace)
    inp_direct, _ = render_direct(p, trace)
    assert inp_cot == inp_direct


from tinyvm.tokeniser import render_probe_query, probe_targets


def test_render_probe_query_input_truncates_to_step_t_plus_query_token():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 5)),
        Instruction(Op.LOAD, args=(1, 7)),
        Instruction(Op.HALT),
    ))
    trace = run(p)
    inp, _ = render_probe_query(p, trace, step_t=1)
    inp_toks = [ID_TO_TOKEN[i] for i in inp]
    assert inp_toks[0] == BOS
    assert inp_toks[-1] == EOS
    assert QUERY in inp_toks
    # The query token must appear AFTER instruction[1].
    assert inp_toks.index(QUERY) > inp_toks.index("LOAD")


def test_render_probe_query_target_is_register_file_at_step_t():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 5)),
        Instruction(Op.LOAD, args=(1, 7)),
        Instruction(Op.HALT),
    ))
    trace = run(p)
    _, tgt = render_probe_query(p, trace, step_t=1)
    tgt_toks = [ID_TO_TOKEN[i] for i in tgt]
    # After step 1, R0=5 and R1=7 (and others are 0). Expect 8 EQUALS tokens.
    assert tgt_toks.count(EQUALS) == 8


def test_probe_targets_returns_register_tuples_per_step():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 5)),
        Instruction(Op.LOAD, args=(1, 7)),
        Instruction(Op.HALT),
    ))
    trace = run(p)
    targets = probe_targets(p, trace)
    assert len(targets) == len(trace.steps)
    assert targets[0][0] == 5
    assert targets[1][0] == 5 and targets[1][1] == 7


from tinyvm.tokeniser import render_direct_text, render_cot_text


def test_render_direct_text_produces_human_readable_string():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 3)),
        Instruction(Op.PRINT, args=(0,)),
        Instruction(Op.HALT),
    ))
    trace = run(p)
    inp_text, tgt_text = render_direct_text(p, trace)
    assert "LOAD R0 3" in inp_text
    assert "PRINT R0" in inp_text
    assert tgt_text.strip() == "3"


def test_render_cot_text_includes_register_file_strings():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 1)),
        Instruction(Op.HALT),
    ))
    trace = run(p)
    _, tgt_text = render_cot_text(p, trace, mode="full")
    assert "R0=1" in tgt_text
    assert "R7=0" in tgt_text


from tinyvm.generators import gen_userop_trace
from tinyvm.tokeniser import render_userop_direct


def test_render_userop_direct_concatenates_demos_and_target():
    decomp = [Instruction(Op.ADD, args=(0, 1, 1))]   # DOUBLE: dst = src + src (placeholder)
    ut = gen_userop_trace(
        opcode_spec={"name": "DOUBLE", "n_args": 2, "decomposition": decomp},
        k_demos=2, n_target=6, use_stack=False, rng=random.Random(0),
    )
    inp, tgt = render_userop_direct(ut)
    inp_toks = [ID_TO_TOKEN[i] for i in inp]
    tgt_toks = [ID_TO_TOKEN[i] for i in tgt]
    # Input must contain the userop symbol (default binding for USEROP_0 == "DOUBLE").
    assert "DOUBLE" in inp_toks
    # Target must end with EOS.
    assert tgt_toks[-1] == EOS


def test_render_userop_direct_has_no_decomp_tokens():
    decomp = [Instruction(Op.ADD, args=(0, 1, 1))]
    ut = gen_userop_trace(
        opcode_spec={"name": "DOUBLE", "n_args": 2, "decomposition": decomp},
        k_demos=1, n_target=6, use_stack=False, rng=random.Random(0),
    )
    inp, _ = render_userop_direct(ut)
    inp_toks = [ID_TO_TOKEN[i] for i in inp]
    assert DECOMP not in inp_toks   # this is the *no-scaffold* condition


from tinyvm.tokeniser import render_userop_with_decomposition


def test_render_userop_with_decomposition_emits_decomp_lines_in_demos():
    decomp = [Instruction(Op.ADD, args=(0, 1, 1))]
    ut = gen_userop_trace(
        opcode_spec={"name": "DOUBLE", "n_args": 2, "decomposition": decomp},
        k_demos=1, n_target=6, use_stack=False, rng=random.Random(0),
    )
    inp, _ = render_userop_with_decomposition(ut)
    inp_toks = [ID_TO_TOKEN[i] for i in inp]
    # At least one DECOMP token per userop call in demos.
    n_demo_userops = sum(
        1 for inst in ut.demos[0].with_symbol.instructions if inst.op.is_userop()
    )
    assert inp_toks.count(DECOMP) == n_demo_userops


def test_render_userop_with_decomposition_target_has_no_decomp():
    """The TARGET portion (after demos) must NOT carry decomposition annotations."""
    decomp = [Instruction(Op.ADD, args=(0, 1, 1))]
    ut = gen_userop_trace(
        opcode_spec={"name": "DOUBLE", "n_args": 2, "decomposition": decomp},
        k_demos=1, n_target=6, use_stack=False, rng=random.Random(0),
    )
    inp, _ = render_userop_with_decomposition(ut)
    inp_toks = [ID_TO_TOKEN[i] for i in inp]
    n_demo_userops = sum(
        1 for inst in ut.demos[0].with_symbol.instructions if inst.op.is_userop()
    )
    assert inp_toks.count(DECOMP) == n_demo_userops
