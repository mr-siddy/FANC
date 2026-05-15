# Tiny-VM Module — Design Spec

**Date:** 2026-05-15
**Authors:** Siddhant (@sidgraph), Claude (@claudeai)
**Status:** Approved for implementation planning
**Source:** `Latent_State_as_Computer.docx` §3 (Tiny-VM), §11 (Datasets), §17 (Week 1 plan)

## 1. Purpose

Tiny-VM is the **data generation engine** for the entire experimental program described in `Latent_State_as_Computer.docx`. Every dataset in Tiers 0–5 is produced by this module; no recorded data is used anywhere in the program. The module's central design property — inherited from the parent doc — is that **the generator and the interpreter are the same code**: producing a program and producing its ground-truth output are one operation, which makes supervision essentially free.

This spec covers the **Day 1–2 deliverable** from §17: the Tiny-VM IR + interpreter, the four generators (counter / register-trace / branched / userop), the custom 64-token tokeniser, and the verifier. JSONL data pipeline, model code, and training loops are out of scope (Day 3+).

## 2. Scope

In scope:

- **`isa`** — instruction dataclasses, opcode enum, ISA constants.
- **`interpreter`** — pure function from `Program` IR to `ExecutionTrace`.
- **`generators`** — four entry points covering Tiers 0, 1, 2, 4.
- **`tokeniser`** — 64-token vocab + three target renderers (direct / CoT / probe-query) + bidirectional encode/decode.
- **`verifier`** — output exact-match scorer (= RLVR reward) + IR well-formedness validator.
- **Test suite** — five layers (unit-interpreter, unit-tokeniser, property-generator, distribution sanity, determinism).

Out of scope (Day 3+):

- JSONL on-disk dataset format.
- HuggingFace `Dataset` / `DataLoader` wrappers.
- Multi-process generation.
- Anything model-specific (architectures, training loops, tokeniser swap for Qwen).

## 3. Key design decisions

| # | Decision | Rationale |
|---|---|---|
| 1 | **IR-first architecture.** `Program` is the canonical form; text and tokens are projections. | Each sub-module testable in isolation; one execution feeds all three renderers. |
| 2 | **Hybrid program generation.** Constructive control-flow skeleton (exact branch/loop counts by construction), random fill within basic blocks. | Difficulty axes (§3.2 of parent doc) are *exact*, not statistical; sample yield is 100%; local diversity preserved. |
| 3 | **Generate-only-valid.** Generator guarantees termination and that every `PRINT` reads a defined register. Interpreter assumes well-formed input. | Pristine supervision signal; difficulty axes stay honest. Step-cap exists only as a paranoia backstop. |
| 4 | **Digit-encoded labels.** One `L` marker token + reused digits (`L`, `1`, `2` for `L12`) + `COLON` for definitions. | Scales past Tier 4's 16-branch requirement; leaves ~20 vocab slots free. |
| 5 | **Configurable anti-shortcut shaping.** Generator is neutral by default; shaping knobs (flat output histogram, distractor regs, randomised PRINT target, length decorrelation) enabled per-tier. | Tier 0/1 stays simple for clean baselines; shaping is available without retrofitting when Tier 2/3 detection flags shortcuts. |
| 6 | **Multiple loop and branch templates.** 3 loop shapes (count-down, count-up, test-at-top) and 2 branch shapes (if, if-else). All termination-guaranteed by construction. | Defeats "learn the surface shape" shortcut; the model must learn the control-flow *semantics*, not one canonical template. |
| 7 | **CoT renderer emits all 8 registers per step (configurable, default full).** | Matches parent doc §7.1 condition 2 literally; sparse mode available for long-trajectory experiments. |

## 4. Module structure

```
tinyvm/
├── isa.py          # ~60 LOC  — Op enum, Instruction, Program, constants
├── interpreter.py  # ~80 LOC  — run(Program) -> ExecutionTrace
├── generators.py   # ~200 LOC — 4 generators + skeleton-builder + block-filler
├── tokeniser.py    # ~100 LOC — encode/decode + 3 renderers
├── verifier.py     # ~40 LOC  — score_output + validate
└── tests/          # ~200 LOC — 5 test layers
```

Total: ~480 LOC excluding tests, ~680 including. The parent doc estimates ~500 LOC for this deliverable.

## 5. ISA (`isa.py`)

Pure data; no logic.

```python
class Op(IntEnum):
    LOAD = 0; MOV = 1; ADD = 2; SUB = 3; MUL = 4; DIV = 5
    NEG = 6; EQ = 7; LT = 8
    JZ = 9; JMP = 10
    PUSH = 11; POP = 12
    PRINT = 13; NOP = 14; HALT = 15

@dataclass(frozen=True)
class Instruction:
    op: Op
    args: tuple[int, ...]       # register indices and/or integer literals
    label: str | None = None    # label *defined* at this line (e.g. "L3")
    target: str | None = None   # label *referenced* by JZ/JMP

@dataclass(frozen=True)
class Program:
    instructions: tuple[Instruction, ...]
    label_index: dict[str, int]  # label -> instruction index, precomputed at construction
```

Constants (single source of truth, imported everywhere):

| Name | Value | Source |
|---|---|---|
| `NUM_REGS` | 8 | §3.1 |
| `VAL_MIN`, `VAL_MAX` | −1024, 1023 | §3.1 |
| `LITERAL_MIN`, `LITERAL_MAX` | −127, 127 | §3.1 |
| `STACK_DEPTH` | 16 | §3.1 |
| `DEFAULT_STEP_CAP` | 1_000_000 | this spec; loose paranoia bound, see §6 |

## 6. Interpreter (`interpreter.py`)

Pure function:

```python
def run(program: Program, step_cap: int | None = DEFAULT_STEP_CAP) -> ExecutionTrace: ...
```

`step_cap` is a paranoia parameter. Pass `None` to disable. The default (`1_000_000`) is set loose enough that it cannot fire on any program a generator emits under the Tier 0–4 difficulty axes — worst-case dynamic step count for Tier 4 (256 static instructions × 32-iter loops × 2-level nesting) is ~260K, well under the cap. If the cap ever fires in production, it indicates a generator bug, not a tunable.

```python
@dataclass
class ExecutionTrace:
    steps: list[StepRecord]   # one per executed instruction (incl. loop repeats)
    output: list[int]         # the PRINT stream — the SFT-direct supervision target
    halted: bool              # True iff HALT or fell off end

@dataclass(frozen=True)
class StepRecord:
    pc: int                   # instruction index executed at this step
    regs: tuple[int, ...]     # register file *after* the instruction (len NUM_REGS)
    stack: tuple[int, ...]    # stack *after* the instruction (len ≤ STACK_DEPTH)
    emitted: int | None       # value PRINTed at this step, if any
```

Semantics (all in one place; no fallback semantics scattered through callers):

- All registers initialise to `0`.
- All arithmetic results clamp to `[VAL_MIN, VAL_MAX]` (parent §3.1).
- `DIV` by zero → result `0`, no error flag (parent §3.1).
- `JZ Ri L`: if `regs[i] == 0`, set `pc = label_index[L]`; else `pc += 1`.
- `JMP L`: `pc = label_index[L]`.
- Fall off end of instruction list ⇒ implicit `HALT`.
- **Step-cap** (see signature above): if `step_cap is not None` and execution exceeds it, raise `InterpreterError`. Under generate-only-valid this never fires on legitimate data; if it does, it's a generator bug and we want it loud.
- `PUSH` on full stack → `InterpreterError`. `POP` on empty stack → `InterpreterError`. Same logic.

## 7. Generators (`generators.py`)

### 7.1 Common procedure (hybrid)

```python
def generate(spec: GenSpec, rng: Random) -> Program:
    # 1. Build control-flow skeleton from axis dials.
    cfg = build_cfg(num_blocks=..., branches=spec.b, loops=spec.l, rng=rng)
    # 2. Allocate registers; designate loop counters and PRINT target(s).
    alloc = allocate_registers(cfg, k=spec.k, rng=rng)
    # 3. Fill each basic block with random straight-line ops over alloc.active,
    #    excluding any register currently serving as a live loop counter.
    blocks = [fill_block(b, alloc, rng, spec.shaping) for b in cfg.blocks]
    # 4. Stitch blocks + control-flow edges into a flat Instruction list.
    program = lower_to_program(cfg, blocks, alloc)
    # 5. Generator self-test: validate() must pass.
    assert verifier.validate(program)
    return program
```

### 7.2 Loop templates (all termination-guaranteed)

Three shapes, sampled uniformly when the CFG needs a loop unless the `GenSpec` pins one:

**(a) count-down**
```
    LOAD Rc K              ; K ∈ [1, max_iters]
L_top:
    <body>
    SUB  Rc Rc R_one
    JZ   Rc L_done
    JMP  L_top
L_done:
```

**(b) count-up**
```
    LOAD Rc 0
    LOAD Rk K
L_top:
    <body>
    ADD  Rc Rc R_one
    SUB  Rd Rk Rc          ; Rd = K - Rc
    JZ   Rd L_done
    JMP  L_top
L_done:
```

**(c) test-at-top** (do-while → do-until-zero with test before body)
```
    LOAD Rc K
L_top:
    JZ   Rc L_done
    <body>
    SUB  Rc Rc R_one
    JMP  L_top
L_done:
```

In all three, `R_one` is a register pre-loaded with `1` in the prologue. The counter register is allocated uniquely from `alloc.active` and is excluded from `fill_block`'s pool while the loop is live. Nested loops use distinct counters; `validate` enforces this.

### 7.3 Branch templates

**(a) if (skip-or-execute)**
```
    LT/EQ Rc Ri Rj
    JZ    Rc L_after
    <then block>
L_after:
```

**(b) if-else**
```
    LT/EQ Rc Ri Rj
    JZ    Rc L_else
    <then block>
    JMP   L_after
L_else:
    <else block>
L_after:
```

The comparator opcode varies (`LT` or `EQ`) and its inputs are randomised from `alloc.active` so both arms are reachable across the dataset.

### 7.4 The four generators

| Generator | Signature | Skeleton | Notes |
|---|---|---|---|
| `gen_counter` | `(n, rng)` | 1 block, 0 branches, 0 loops | Tier 0. `k=1`, only `R0`, only `ADD/SUB/NEG/MOV` from the arithmetic set. Trivial. |
| `gen_register_trace` | `(n, k, rng, shaping)` | 1 block, 0 branches, 0 loops | Tier 1. `k` active regs from `[2, 8]`; full arithmetic vocabulary; single terminal `PRINT`. |
| `gen_branched` | `(n, k, b, l, rng, shaping)` | `b` branches + `l` loops | Tier 2 / 4. All templates above. May emit multiple `PRINT`s. |
| `gen_userop_trace` | `(opcode_spec, k_demos, n_target, rng)` | uses `gen_branched` internally | Tier 4. Generates `k_demos` (input → output) example programs **using the base-opcode decomposition**, then one *target* program that uses the userop symbol directly. CoT-scaffolded version is produced by the tokeniser's CoT renderer, not a separate generator. |

### 7.5 Shaping knobs (`GenSpec.shaping`)

A flat dataclass, each field independently togglable. Off by default in Tiers 0 and 1.

| Knob | Effect | Defeats |
|---|---|---|
| `flat_output_histogram` | Rejection-sample so final `PRINT` values are roughly uniform over a target bin set | "Guess the modal answer" |
| `distractor_regs: int` | N of `k`'s active regs are written to but never feed `PRINT` | "Look at last write" |
| `randomize_print_target` | Pick `PRINT` register uniformly over active regs, not the most-recently-written one | "PRINT is always the last touched reg" |
| `decorrelate_length` | Within a length bucket, scramble pad/contract so length doesn't leak answer magnitude | Length-based shortcuts |

### 7.6 Reproducibility

Every generator takes a `Random` instance (or seed `int`). Same seed → bit-exact program. Dataset-level reproducibility is via `(seed_base, indices)`: `program_i = generate(spec, Random(seed_base ^ i))`. Parent §11.2 requires fresh re-generation per seed to avoid memorisation artefacts; this scheme satisfies that.

## 8. Tokeniser (`tokeniser.py`)

### 8.1 Vocabulary (64 tokens)

| Bucket | Count | Tokens |
|---|---|---|
| Opcodes | 16 | `LOAD MOV ADD SUB MUL DIV NEG EQ LT JZ JMP PUSH POP PRINT NOP HALT` |
| Registers | 8 | `R0..R7` |
| Digits | 10 | `0..9` |
| Sign | 1 | `MINUS` |
| Label marker | 1 | `L` |
| Colon | 1 | `COLON` (label definitions) |
| Equals | 1 | `EQUALS` (register-file printout format) |
| Newline | 1 | `NEWLINE` |
| Special | 4 | `BOS EOS PAD ?` |
| **Fixed total** | **43** | |
| Reserved | 21 | Future opcodes; Tier 4 userop symbols (`DOUBLE MAX ABS MOD XOR` = 5 of 21) |

### 8.2 Encoding format

Surface syntax → tokens, by example:

| Surface | Tokens |
|---|---|
| `LOAD R3 -42` | `LOAD R3 MINUS 4 2 NEWLINE` |
| `ADD R0 R1 R2` | `ADD R0 R1 R2 NEWLINE` |
| `JZ R1 L7` | `JZ R1 L 7 NEWLINE` |
| `L3: ADD R0 R1 R2` | `L 3 COLON ADD R0 R1 R2 NEWLINE` |
| `PRINT R0` | `PRINT R0 NEWLINE` |

Integers are variable-length digit sequences terminated by the first non-digit token. No left-padding.

### 8.3 Renderers

All three operate over the same `(Program, ExecutionTrace)`:

**`render_direct(program, trace) → (input_tokens, target_tokens)`**
- input: `BOS` + program text + `EOS`
- target: `BOS` + digit-encoded values from `trace.output`, `NEWLINE`-separated + `EOS`

**`render_cot(program, trace, mode='full') → (input_tokens, target_tokens)`**
- input: `BOS` + program text + `EOS`
- target: `BOS` + for each step `s`: instruction tokens for `program.instructions[trace.steps[s].pc]`, then the register-file printout `R0 EQUALS <digits> R1 EQUALS <digits> ... R7 EQUALS <digits> NEWLINE`; finally the output stream + `EOS`
- `mode='full'` emits all 8 registers per step (default, matches parent §7.1 cond. 2). `mode='modified'` emits only registers changed at that step.

**`render_probe_query(program, trace, step_t) → (input_tokens, target_tokens)`**
- input: `BOS` + program text up to and including instruction `t` + `?` + `EOS`
- target: register-file printout at step `t`, same format as the CoT renderer's per-step state.

### 8.4 Non-text probe mode

For Tier 3 linear probes on activations, the helper `probe_targets(program, trace) → list[tuple[int, ...]]` returns ground-truth register files per step as plain Python tuples. No tokens — the consumer reads model hidden states directly.

### 8.5 Decode

`decode(tokens) → Program` is the inverse of program-text encoding. Used by (a) round-trip property tests and (b) value-level scoring in the verifier.

### 8.6 Tier 5 / Qwen tokeniser hand-off

Each renderer also exposes its underlying surface text via `render_*_text(...) → str`. For Tier 5, training code feeds these strings into Qwen's tokeniser unchanged. Only the encode-to-IDs step differs; the rendering logic is identical.

## 9. Verifier (`verifier.py`)

Two responsibilities:

**`score_output(predicted_tokens, target_tokens) → float`** — the RLVR reward function used in parent §7.1 conditions 3/4 and §10 Tier 5.
- Decode both sides to integer value sequences via `tokeniser.decode_value_stream`.
- Return `1.0` iff the value sequences are exactly equal; else `0.0`.
- Decode-then-compare is more robust than byte-equality to harmless surface variation, and surfaces decode-side bugs loudly.

**`validate(program: Program) → bool`** — IR well-formedness, called as the post-construct assertion in every generator (§7.1 step 5). Checks:

- Every label referenced by `JZ`/`JMP` exists in `label_index`.
- No duplicate label definitions.
- Every `PRINT Ri` is preceded on every reachable path by at least one write to `Ri`, unless `Ri` is intentionally the initial-zero path (must be flagged in the generator config).
- Stack-balance: every `POP` on every reachable path is preceded by a matching `PUSH`.
- Stack-depth: no reachable path exceeds `STACK_DEPTH` between matched `PUSH`/`POP`.
- Loop-counter uniqueness: no two simultaneously-live loop counters share a register.

The validator is structurally redundant with a correctly-constructed generator. That redundancy is the safety net: if the generator ever drifts, `validate` fails before the bug ships into a 200K-example dataset.

## 10. Testing strategy

Five layers, runnable as a single `pytest` invocation:

| Layer | What it checks | How |
|---|---|---|
| **Unit (interpreter)** | One semantic per test: clamping, DIV/0→0, JZ taken/not-taken, JMP, PUSH/POP, fall-off-end implicit HALT, step-cap raises, PUSH-overflow raises, POP-underflow raises | Hand-written 5–10 line programs, golden trace output |
| **Unit (tokeniser)** | `decode(encode(p)) == p` on every legal IR; renderers produce well-formed token sequences | 1K generator outputs per generator config |
| **Property (generators)** | For each generator at each tier's difficulty: `validate(p)` passes, interpreter terminates without raising, output stream is non-empty | 1K seeds per generator config |
| **Distribution (sanity)** | Histograms aren't pathological: register-use counts, output-value distribution, control-flow-template mix, program-length distribution all within expected ranges | Numpy assertions on aggregate stats over 10K samples |
| **Determinism** | Same seed → bit-exact program; different seeds → different programs | Pair-call structural comparison |

The distribution layer catches *quiet* bugs that the others miss — a generator that "works" but only ever PRINTs values in `[0, 7]`, or always picks `R0` as the counter.

## 11. Risks and mitigations

| Risk | Mitigation |
|---|---|
| **Generator drift** introduces invalid programs that the interpreter then handles "permissively," leaking garbage supervision into a 200K dataset | `validate` runs at end of every generator call; the distribution layer flags drift early via histogram changes |
| **Shortcut learning** on uniform surface patterns (one loop shape, modal output, length-correlated answer) | Multiple loop & branch templates (§7.2, §7.3); configurable shaping knobs (§7.5); Tier 2/3 detection (parent §15 Risk A) backstops |
| **Vocab overflow** if future tiers need more opcode-like symbols than the 21-slot reserve allows | Reserve is sized for Tier 4's 5 userops + 16 of headroom; if exceeded, label encoding can switch to a more compact scheme without changing the rest |
| **CoT target length blows up the context window** at long trajectories | Configurable CoT mode (`full` vs `modified`); training code can pick per experiment |

## 12. Open questions deferred to implementation

- Exact distribution of basic-block sizes within a CFG (target average to be calibrated against §3.2 axis values during implementation).
- Whether the `?`-state-query training data should be mixed into the supervised set or held strictly for probing (parent §3.1 leans toward "only in probe data"; we'll follow that unless probe results are noisy).
- The precise initial-zero policy in `validate`: do we ever allow `PRINT Ri` where `Ri` is only ever the initial `0`? Default: disallow, since it's a trivial-answer shortcut.

## 13. References

- `Latent_State_as_Computer.docx` §3 (Tiny-VM specification), §7.1 (Tier 2 training conditions), §11 (Datasets), §17 (Week 1 plan).
- This spec is the input to the implementation plan, to be written next under `docs/superpowers/plans/`.
