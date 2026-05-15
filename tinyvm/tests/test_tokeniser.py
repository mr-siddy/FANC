from tinyvm.tokeniser import (
    VOCAB_SIZE, TOKEN_TO_ID, ID_TO_TOKEN, OPCODE_TOKENS, REGISTER_TOKENS,
    DIGIT_TOKENS, MINUS, L_MARKER, COLON, EQUALS, DECOMP, NEWLINE,
    BOS, EOS, PAD, QUERY, USEROP_TOKENS, encode, render_direct,
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
