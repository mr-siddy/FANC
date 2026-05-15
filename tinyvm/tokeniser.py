"""Tokeniser: 64-token vocab + encode/decode + renderers (spec §8)."""
from __future__ import annotations

from tinyvm.isa import NUM_REGS, Op, Instruction, Program
from tinyvm.interpreter import ExecutionTrace


# 1. Build the vocab as an ordered list of tokens. ID = list position.
OPCODE_TOKENS: list[str] = [op.name for op in Op if not op.is_userop()]   # 16
REGISTER_TOKENS: list[str] = [f"R{i}" for i in range(NUM_REGS)]            # 8
DIGIT_TOKENS: list[str] = [str(i) for i in range(10)]                      # 10

MINUS: str = "MINUS"
L_MARKER: str = "L"
COLON: str = "COLON"
EQUALS: str = "EQUALS"
DECOMP: str = "DECOMP"
NEWLINE: str = "NEWLINE"
BOS: str = "BOS"
EOS: str = "EOS"
PAD: str = "PAD"
QUERY: str = "?"

USEROP_TOKENS: list[str] = ["DOUBLE", "MAX", "ABS", "MOD", "SIGN"]
# Default 5 userop symbols. Parent §9.2 names XOR as the fifth; spec §12 swaps
# SIGN in by default due to XOR's decomposition cost. The token list is what's
# emitted in surface text; the underlying Op slot (USEROP_0..USEROP_4) is
# fixed regardless of which symbol is bound to which slot.

_FIXED_TOKENS: list[str] = (
    OPCODE_TOKENS
    + REGISTER_TOKENS
    + DIGIT_TOKENS
    + [MINUS, L_MARKER, COLON, EQUALS, DECOMP, NEWLINE, BOS, EOS, PAD, QUERY]
    + USEROP_TOKENS
)
# Pad the vocab to 64 with placeholder reserved tokens.
_RESERVED_TOKENS: list[str] = [f"RESERVED_{i}" for i in range(64 - len(_FIXED_TOKENS))]

_ALL_TOKENS: list[str] = _FIXED_TOKENS + _RESERVED_TOKENS

VOCAB_SIZE: int = len(_ALL_TOKENS)
assert VOCAB_SIZE == 64, f"vocab size is {VOCAB_SIZE}, expected 64"

TOKEN_TO_ID: dict[str, int] = {tok: i for i, tok in enumerate(_ALL_TOKENS)}
ID_TO_TOKEN: dict[int, str] = {i: tok for tok, i in TOKEN_TO_ID.items()}


# Userop slot -> default symbol (matches USEROP_TOKENS order).
USEROP_SLOT_TO_SYMBOL: dict[Op, str] = {
    Op.USEROP_0: USEROP_TOKENS[0],
    Op.USEROP_1: USEROP_TOKENS[1],
    Op.USEROP_2: USEROP_TOKENS[2],
    Op.USEROP_3: USEROP_TOKENS[3],
    Op.USEROP_4: USEROP_TOKENS[4],
}


def _opcode_token(op: Op) -> str:
    if op.is_userop():
        return USEROP_SLOT_TO_SYMBOL[op]
    return op.name


# Per-opcode argument schema: (n_register_args, n_literal_args, has_label_target).
_OP_ARG_SCHEMA: dict[Op, tuple[int, int, bool]] = {
    Op.LOAD: (1, 1, False),
    Op.MOV: (2, 0, False),
    Op.ADD: (3, 0, False),
    Op.SUB: (3, 0, False),
    Op.MUL: (3, 0, False),
    Op.DIV: (3, 0, False),
    Op.NEG: (2, 0, False),
    Op.EQ: (3, 0, False),
    Op.LT: (3, 0, False),
    Op.JZ: (1, 0, True),
    Op.JMP: (0, 0, True),
    Op.PUSH: (1, 0, False),
    Op.POP: (1, 0, False),
    Op.PRINT: (1, 0, False),
    Op.NOP: (0, 0, False),
    Op.HALT: (0, 0, False),
    # Userops (default symbol bindings):
    Op.USEROP_0: (2, 0, False),   # DOUBLE Ri Rj
    Op.USEROP_1: (3, 0, False),   # MAX Ri Rj Rk
    Op.USEROP_2: (2, 0, False),   # ABS Ri Rj
    Op.USEROP_3: (3, 0, False),   # MOD Ri Rj Rk
    Op.USEROP_4: (2, 0, False),   # SIGN Ri Rj
}


def _digits_of(n: int) -> list[str]:
    """Encode a signed integer as MINUS? digit sequence."""
    out: list[str] = []
    if n < 0:
        out.append(MINUS)
        n = -n
    for c in str(n):
        out.append(c)
    return out


# Labels emitted by generators are 'L<n>' where n is an integer; non-numeric
# labels (e.g. "END" used in some test programs) are mapped through a registry
# so encode/decode stays bijective. Generator-produced label ids live in
# [0, 9999]; the registry assigns 10_000+.
_LABEL_REGISTRY: dict[str, int] = {}
_LABEL_ID_COUNTER: list[int] = [10_000]


def _next_label_id() -> int:
    _LABEL_ID_COUNTER[0] += 1
    return _LABEL_ID_COUNTER[0]


def _label_to_int(label: str) -> int:
    if label.startswith("L") and label[1:].isdigit():
        return int(label[1:])
    return _LABEL_REGISTRY.setdefault(label, _next_label_id())


def _encode_instruction(inst: Instruction) -> list[str]:
    tokens: list[str] = []
    if inst.label is not None:
        tokens.append(L_MARKER)
        tokens.extend(c for c in str(_label_to_int(inst.label)))
        tokens.append(COLON)
    tokens.append(_opcode_token(inst.op))
    n_regs, n_lits, has_target = _OP_ARG_SCHEMA[inst.op]
    args = list(inst.args)
    for _ in range(n_regs):
        ri = args.pop(0)
        tokens.append(REGISTER_TOKENS[ri])
    for _ in range(n_lits):
        lit = args.pop(0)
        tokens.extend(_digits_of(lit))
    if has_target:
        assert inst.target is not None
        tokens.append(L_MARKER)
        tokens.extend(c for c in str(_label_to_int(inst.target)))
    tokens.append(NEWLINE)
    return tokens


def encode(program: Program) -> list[int]:
    """Encode a Program to a flat list of token IDs."""
    flat: list[str] = []
    for inst in program.instructions:
        flat.extend(_encode_instruction(inst))
    return [TOKEN_TO_ID[t] for t in flat]


_TOKEN_NAME_TO_OP: dict[str, Op] = {op.name: op for op in Op if not op.is_userop()}
_SYMBOL_TO_USEROP: dict[str, Op] = {
    sym: slot for slot, sym in USEROP_SLOT_TO_SYMBOL.items()
}


def _read_int(tokens: list[str], pos: int) -> tuple[int, int]:
    """Read a (possibly negative) integer literal at `tokens[pos]`. Returns (value, new_pos)."""
    sign = 1
    if tokens[pos] == MINUS:
        sign = -1
        pos += 1
    digits = ""
    while pos < len(tokens) and tokens[pos] in DIGIT_TOKENS:
        digits += tokens[pos]
        pos += 1
    assert digits, "expected digit sequence"
    return sign * int(digits), pos


def _read_label(tokens: list[str], pos: int) -> tuple[str, int]:
    """Read an L<digits> label at `tokens[pos]`. Returns (label, new_pos)."""
    assert tokens[pos] == L_MARKER
    pos += 1
    digits = ""
    while pos < len(tokens) and tokens[pos] in DIGIT_TOKENS:
        digits += tokens[pos]
        pos += 1
    assert digits, "expected digit sequence after L marker"
    return f"L{int(digits)}", pos


def decode(ids: list[int]) -> Program:
    """Inverse of encode. Reconstructs a Program from token IDs."""
    tokens = [ID_TO_TOKEN[i] for i in ids]
    insts: list[Instruction] = []
    pos = 0
    while pos < len(tokens):
        label: str | None = None
        # Optional label definition: L <digits> COLON <opcode> ...
        if tokens[pos] == L_MARKER and (pos + 1) < len(tokens) and tokens[pos + 1] in DIGIT_TOKENS:
            scan = pos + 1
            while scan < len(tokens) and tokens[scan] in DIGIT_TOKENS:
                scan += 1
            if scan < len(tokens) and tokens[scan] == COLON:
                label, pos = _read_label(tokens, pos)
                pos += 1  # consume COLON
        # Opcode (base name or userop symbol).
        op_tok = tokens[pos]
        pos += 1
        if op_tok in _TOKEN_NAME_TO_OP:
            op = _TOKEN_NAME_TO_OP[op_tok]
        elif op_tok in _SYMBOL_TO_USEROP:
            op = _SYMBOL_TO_USEROP[op_tok]
        else:
            raise ValueError(f"unexpected opcode token: {op_tok}")
        n_regs, n_lits, has_target = _OP_ARG_SCHEMA[op]
        args: list[int] = []
        for _ in range(n_regs):
            reg_tok = tokens[pos]
            pos += 1
            args.append(REGISTER_TOKENS.index(reg_tok))
        for _ in range(n_lits):
            v, pos = _read_int(tokens, pos)
            args.append(v)
        target: str | None = None
        if has_target:
            target, pos = _read_label(tokens, pos)
        assert tokens[pos] == NEWLINE, f"expected NEWLINE, got {tokens[pos]}"
        pos += 1
        insts.append(Instruction(op=op, args=tuple(args), label=label, target=target))
    return Program.build(tuple(insts))


def render_direct(program: Program, trace: ExecutionTrace) -> tuple[list[int], list[int]]:
    """Spec §8.3 render_direct: input=BOS+program+EOS, target=BOS+output stream+EOS."""
    inp = [TOKEN_TO_ID[BOS]] + encode(program) + [TOKEN_TO_ID[EOS]]
    target_tokens: list[str] = [BOS]
    for v in trace.output:
        target_tokens.extend(_digits_of(v))
        target_tokens.append(NEWLINE)
    target_tokens.append(EOS)
    return inp, [TOKEN_TO_ID[t] for t in target_tokens]


def _register_file_tokens(regs: tuple[int, ...], prev_regs: tuple[int, ...] | None, mode: str) -> list[str]:
    """Format a register file as 'R0 EQUALS <digits> R1 EQUALS <digits> ...'.

    mode='full' emits all NUM_REGS; 'modified' emits only registers whose value
    differs from prev_regs (or from 0 on first step). Returns tokens (no trailing NEWLINE — caller appends).
    """
    out: list[str] = []
    # On first step, prev_regs is None; treat initial state as all zeros.
    reference = prev_regs if prev_regs is not None else tuple(0 for _ in range(NUM_REGS))
    for i in range(NUM_REGS):
        if mode == "modified" and regs[i] == reference[i]:
            continue
        out.append(REGISTER_TOKENS[i])
        out.append(EQUALS)
        out.extend(_digits_of(regs[i]))
    return out


def render_cot(
    program: Program,
    trace: ExecutionTrace,
    mode: str = "full",
) -> tuple[list[int], list[int]]:
    """Spec §8.3 render_cot. mode in {'full', 'modified'}."""
    if mode not in ("full", "modified"):
        raise ValueError(f"mode must be 'full' or 'modified', got {mode!r}")
    inp = [TOKEN_TO_ID[BOS]] + encode(program) + [TOKEN_TO_ID[EOS]]
    target_tokens: list[str] = [BOS]
    prev_regs: tuple[int, ...] | None = None
    for s in trace.steps:
        inst = program.instructions[s.pc]
        target_tokens.extend(_encode_instruction(inst))
        rf = _register_file_tokens(s.regs, prev_regs, mode)
        target_tokens.extend(rf)
        target_tokens.append(NEWLINE)
        prev_regs = s.regs
    for v in trace.output:
        target_tokens.extend(_digits_of(v))
        target_tokens.append(NEWLINE)
    target_tokens.append(EOS)
    return inp, [TOKEN_TO_ID[t] for t in target_tokens]


def render_probe_query(
    program: Program,
    trace: ExecutionTrace,
    step_t: int,
) -> tuple[list[int], list[int]]:
    """Spec §8.3 render_probe_query."""
    # Input: BOS + program text up to and including instruction at executed step_t + ? + EOS
    executed_idx = trace.steps[step_t].pc
    inp_tokens: list[str] = [BOS]
    for i in range(executed_idx + 1):
        inp_tokens.extend(_encode_instruction(program.instructions[i]))
    inp_tokens.append(QUERY)
    inp_tokens.append(EOS)
    # Target: register file at step_t (full).
    tgt_tokens: list[str] = [BOS]
    tgt_tokens.extend(_register_file_tokens(trace.steps[step_t].regs, prev_regs=None, mode="full"))
    tgt_tokens.append(NEWLINE)
    tgt_tokens.append(EOS)
    return [TOKEN_TO_ID[t] for t in inp_tokens], [TOKEN_TO_ID[t] for t in tgt_tokens]


def probe_targets(program: Program, trace: ExecutionTrace) -> list[tuple[int, ...]]:
    """Spec §8.4 non-text probe mode: register files per step as plain tuples."""
    return [s.regs for s in trace.steps]


def _tokens_to_text(tokens: list[str]) -> str:
    """Render a list of vocab tokens to a human-readable string.

    Surface rules: spaces between tokens, except no space before COLON or
    NEWLINE. MINUS attaches to the following digit. EQUALS attaches to
    the digit sequence on both sides (R0=5 not R0 = 5). NEWLINE -> '\\n'.
    BOS, EOS, PAD are omitted from output.
    """
    out: list[str] = []
    for i, t in enumerate(tokens):
        if t in (BOS, EOS, PAD):
            # Skip control tokens that frame the sequence
            continue
        elif t == NEWLINE:
            out.append("\n")
        elif t == COLON:
            if out and out[-1] == " ":
                out.pop()
            out.append(":")
        elif t == EQUALS:
            if out and out[-1] == " ":
                out.pop()
            out.append("=")
        elif t == MINUS:
            if out and out[-1] == " ":
                out.pop()
            out.append("-")
        elif t == L_MARKER:
            out.append("L")
        elif t in (QUERY, DECOMP):
            out.append(t if t != QUERY else "?")
            out.append(" ")
        elif t in DIGIT_TOKENS:
            if out and out[-1] in {*DIGIT_TOKENS, "L", "-"}:
                out.append(t)
            else:
                out.append(t)
        else:
            out.append(t)
            out.append(" ")
    return "".join(out)


def render_direct_text(program: Program, trace: ExecutionTrace) -> tuple[str, str]:
    """Text-level render for Qwen tokeniser hand-off (spec §8.6)."""
    inp_ids, tgt_ids = render_direct(program, trace)
    inp_text = _tokens_to_text([ID_TO_TOKEN[i] for i in inp_ids])
    tgt_text = _tokens_to_text([ID_TO_TOKEN[i] for i in tgt_ids])
    return inp_text, tgt_text


def render_cot_text(program: Program, trace: ExecutionTrace, mode: str = "full") -> tuple[str, str]:
    """Text-level CoT render for Qwen tokeniser hand-off."""
    inp_ids, tgt_ids = render_cot(program, trace, mode=mode)
    return (
        _tokens_to_text([ID_TO_TOKEN[i] for i in inp_ids]),
        _tokens_to_text([ID_TO_TOKEN[i] for i in tgt_ids]),
    )


def render_probe_query_text(
    program: Program,
    trace: ExecutionTrace,
    step_t: int,
) -> tuple[str, str]:
    """Text-level render_probe_query for Qwen tokeniser hand-off (spec §8.6)."""
    inp_ids, tgt_ids = render_probe_query(program, trace, step_t)
    return (
        _tokens_to_text([ID_TO_TOKEN[i] for i in inp_ids]),
        _tokens_to_text([ID_TO_TOKEN[i] for i in tgt_ids]),
    )


def render_userop_direct_text(utrace: "UseropTrace") -> tuple[str, str]:
    """Text-level render_userop_direct for Qwen tokeniser hand-off (spec §8.6)."""
    inp_ids, tgt_ids = render_userop_direct(utrace)
    return (
        _tokens_to_text([ID_TO_TOKEN[i] for i in inp_ids]),
        _tokens_to_text([ID_TO_TOKEN[i] for i in tgt_ids]),
    )


def render_userop_with_decomposition_text(utrace: "UseropTrace") -> tuple[str, str]:
    """Text-level render_userop_with_decomposition for Qwen tokeniser hand-off (spec §8.6)."""
    inp_ids, tgt_ids = render_userop_with_decomposition(utrace)
    return (
        _tokens_to_text([ID_TO_TOKEN[i] for i in inp_ids]),
        _tokens_to_text([ID_TO_TOKEN[i] for i in tgt_ids]),
    )


# Deferred import to avoid circular dependency with generators.py
from tinyvm.generators import UseropTrace


def render_userop_direct(utrace: UseropTrace) -> tuple[list[int], list[int]]:
    """Spec §8.3, Tier 4 condition 1. No decomposition scaffolding."""
    inp_tokens: list[str] = [BOS]
    for pair in utrace.demos:
        for inst in pair.with_symbol.instructions:
            inp_tokens.extend(_encode_instruction(inst))
        # Demo output stream as supervision context.
        for v in pair.trace.output:
            inp_tokens.extend(_digits_of(v))
            inp_tokens.append(NEWLINE)
    # Target program (with userop symbol).
    for inst in utrace.target.with_symbol.instructions:
        inp_tokens.extend(_encode_instruction(inst))
    inp_tokens.append(EOS)
    # Target supervision = target program's output (via decomposition).
    tgt_tokens: list[str] = [BOS]
    for v in utrace.target.trace.output:
        tgt_tokens.extend(_digits_of(v))
        tgt_tokens.append(NEWLINE)
    tgt_tokens.append(EOS)
    return [TOKEN_TO_ID[t] for t in inp_tokens], [TOKEN_TO_ID[t] for t in tgt_tokens]


def render_userop_with_decomposition(utrace: UseropTrace) -> tuple[list[int], list[int]]:
    """Spec §8.3, Tier 4 condition 2. Demos carry DECOMP lines after each userop.

    For each demo instruction whose op is a userop, emit the instruction followed
    by `DECOMP` + the base-opcode template (with placeholder indices remapped to
    the concrete register operands) + NEWLINE. The target program is rendered
    without DECOMP annotations.
    """
    inp_tokens: list[str] = [BOS]
    for pair in utrace.demos:
        for inst in pair.with_symbol.instructions:
            inp_tokens.extend(_encode_instruction(inst))
            if inst.op.is_userop():
                sym = USEROP_SLOT_TO_SYMBOL[inst.op]
                template = utrace.decomposition[sym]
                inp_tokens.append(DECOMP)
                for t_inst in template:
                    # Remap placeholder indices to concrete register indices.
                    n_regs, n_lits, _has_target = _OP_ARG_SCHEMA[t_inst.op]
                    mapped: list[int] = []
                    for k in range(n_regs):
                        mapped.append(inst.args[t_inst.args[k]])
                    for k in range(n_lits):
                        mapped.append(t_inst.args[n_regs + k])
                    concrete = Instruction(
                        op=t_inst.op, args=tuple(mapped), target=t_inst.target,
                    )
                    inp_tokens.extend(_encode_instruction(concrete))
        for v in pair.trace.output:
            inp_tokens.extend(_digits_of(v))
            inp_tokens.append(NEWLINE)
    # Target — no decomposition annotations.
    for inst in utrace.target.with_symbol.instructions:
        inp_tokens.extend(_encode_instruction(inst))
    inp_tokens.append(EOS)
    # Target supervision.
    tgt_tokens: list[str] = [BOS]
    for v in utrace.target.trace.output:
        tgt_tokens.extend(_digits_of(v))
        tgt_tokens.append(NEWLINE)
    tgt_tokens.append(EOS)
    return [TOKEN_TO_ID[t] for t in inp_tokens], [TOKEN_TO_ID[t] for t in tgt_tokens]
