# Tiny-VM Visualization Tool — Design Spec

**Date:** 2026-05-16
**Authors:** Siddhant (@sidgraph), Claude (@claudeai)
**Status:** Approved for implementation planning
**Source:** Brainstorm session 2026-05-16; `Latent_State_as_Computer.docx` §3 (Tiny-VM); `docs/superpowers/specs/2026-05-15-tinyvm-module-design.md` (Tiny-VM module)

## 1. Purpose

A TypeScript-based, in-browser visualization tool for the Tiny-VM environment. It serves two audiences simultaneously:

- **Researcher / model-eval companion.** Drop a `(program, ground_truth, model_prediction)` bundle and inspect where the model diverges from the interpreter, step-by-step, with full runtime state visible.
- **Pedagogical playground.** A code editor + execution visualizer that lets a learner type Tiny-VM source, watch state evolve register-by-register, and explore curated example programs without setting up Python.

The tool is a single static React SPA. It runs entirely in the browser; no Python server, no model inference. The Tiny-VM interpreter is re-implemented in TypeScript and held byte-exact with the Python reference via a checked-in golden-fixture parity test.

## 2. Scope

In scope (v1):

- **Tier coverage:** Tier 0 (counter), Tier 1 (register trace), Tier 2 (branched: branches + loops + optional stack).
- **TS port:** `isa`, `interpreter`, `verifier`, `parser` (new — Python has no source parser), and the `encode` / `decode` / `render_direct` subset of `tokeniser`.
- **Playground tab:** text editor with Tiny-VM syntax mode, lesson playlist, step controls, execution panel.
- **Compare tab:** comparison-bundle loader, divergence panel, same execution panel.
- **Parity harness:** Python emits a curated JSON fixture bundle; TS asserts byte-equality.

Out of scope (v1):

- Tier 4 userops, `render_userop_*` renderers, decomposition view (v1.1).
- CoT-mode predictions / per-step register prediction comparison (v1.1).
- Dataset-level browser over many bundles (v1.2).
- Pyodide-in-browser, anywidget notebook embed, separate npm package, telemetry, deploy targets.

## 3. Key design decisions

| # | Decision | Rationale |
|---|---|---|
| 1 | **Static SPA, no server.** | Both audiences are reachable via a URL; no backend, no infra to maintain. |
| 2 | **TS port over Pyodide.** | Pyodide is ~10 MB and slow to cold-start; awkward in the step-through loop. A 200 LOC TS port with parity testing buys correctness without the runtime cost. |
| 3 | **Sub-folder in this repo, not separate repo.** | Parity fixtures are emitted from the Python `tinyvm/` module; keeping both in one git history makes drift a one-PR cycle. |
| 4 | **CodeMirror 6, not Monaco.** | Smaller bundle, no web-worker setup, easier custom-language mode for the Tiny-VM grammar. |
| 5 | **No component library.** | The UI surface is ~10 components; hand-rolled with Tailwind is less code than wiring shadcn/MUI. |
| 6 | **Two top-level tabs, shared execution panel.** | Playground and Compare are distinct workflows; sharing the panel keeps the visual idiom consistent. |
| 7 | **Single-program comparison only in v1.** | Dataset browsing is the next natural step but is its own design problem; ship the failure-drill-down loop first. |
| 8 | **Lessons are seeds, not a tutorial framework.** | Clicking a lesson populates the editor; no locked steps, no progress tracking — matches "explorable explanation" rather than "guided course." |
| 9 | **Parity fixtures checked in, regenerated explicitly.** | CI fails if `golden.json` is stale relative to the current Python interpreter. Drift is loud and reviewable. |

## 4. Repo layout

```
tinyvm-viz/
├── package.json
├── vite.config.ts                # base: './' so static-host deployment is trivial
├── tsconfig.json                 # strict, noUncheckedIndexedAccess
├── index.html
├── src/
│   ├── main.tsx
│   ├── App.tsx                   # tab shell, react-router
│   ├── core/                     # UI-free TS port; testable without React
│   │   ├── isa.ts
│   │   ├── parser.ts             # source text → Program
│   │   ├── interpreter.ts
│   │   ├── verifier.ts
│   │   ├── tokeniser.ts          # encode/decode + render_direct only
│   │   └── types.ts              # ComparisonBundle, SerializedTrace, etc.
│   ├── components/
│   │   ├── ExecutionPanel.tsx
│   │   ├── RegisterFile.tsx
│   │   ├── StackView.tsx
│   │   ├── ProgramView.tsx
│   │   ├── OutputStream.tsx
│   │   ├── Editor.tsx            # CodeMirror w/ Tiny-VM mode
│   │   ├── StepControls.tsx
│   │   ├── LessonPlaylist.tsx
│   │   └── DivergencePanel.tsx
│   ├── pages/
│   │   ├── Playground.tsx
│   │   └── Compare.tsx
│   ├── lessons/                  # hand-authored TS lesson seeds
│   └── styles/
├── samples/                      # checked-in ComparisonBundle JSON files
├── tests/
│   ├── unit/                     # core/* + components (vitest)
│   ├── parity/                   # vs golden.json (vitest)
│   └── fixtures/
│       └── golden.json           # emitted by export_golden_fixtures.py
└── README.md

tinyvm/scripts/
├── export_golden_fixtures.py     # idempotent on a fixed seed sweep
└── export_comparison_bundle.py   # wraps generator + model prediction → bundle
```

`core/` is framework-free TS. It imports nothing from React. UI in `components/` only depends on `core/` types and pure functions. This means the parity test is `vitest run tests/parity` against the port alone.

## 5. TS port scope

The port is intentionally narrower than the Python module — only what the UI needs in v1.

**Ported (`src/core/`):**

| File | Mirrors Python module | Notes |
|---|---|---|
| `isa.ts` | `tinyvm/isa.py` | `Op` enum (16 base ops; userop slots reserved but unused in v1), `Instruction`, `Program.build()` with the same dup-label rejection and immutable `labelIndex` |
| `interpreter.ts` | `tinyvm/interpreter.py` | `run(program, stepCap)` → `ExecutionTrace = { steps, output, halted }`. Identical clamp / DIV-0 → 0 / stack-fault / userop-raises semantics |
| `verifier.ts` | `tinyvm/verifier.py` | `validate(program)` (arity, label targets, PRINT-predecessor reachability, stack balance/depth); `scoreOutput(predicted, target)` |
| `parser.ts` | **new in TS** | Source text → `Program`. Surface syntax matches Python `_tokens_to_text`. Returns `{program, errors[]}` so the editor surfaces line-level diagnostics. |
| `tokeniser.ts` | `tinyvm/tokeniser.py` (subset) | `encode` / `decode` + `renderDirect`. CoT / probe-query / userop renderers deferred to v1.1 |

**Not ported in v1:** generators (`gen_counter`, `gen_register_trace`, `gen_branched`, `gen_userop_trace`), `substitute_userops`, `render_cot`, `render_probe_query`, `render_userop_direct`, `render_userop_with_decomposition`, distribution sanity layer. Programs come from the editor or from Python-emitted fixtures/bundles.

## 6. Parity strategy

The Python interpreter is the spec; the TS port is held byte-exact against it.

1. **`tinyvm/scripts/export_golden_fixtures.py`** runs `gen_counter`, `gen_register_trace`, `gen_branched` across a curated seed/spec sweep (~50 programs spanning Tier 0/1/2 difficulty axes) and emits:

   ```json
   [{
     "seed": 0, "generator": "gen_register_trace", "spec": {"n": 16, "k": 4},
     "source_text": "LOAD R3 5\nADD R3 R3 R3\n...PRINT R3\nHALT\n",
     "program_ir": {...},                  // optional, catches parser drift
     "expected_trace": {"steps": [...], "output": [...], "halted": true}
   }, ...]
   ```

2. **`tinyvm-viz/tests/fixtures/golden.json`** is the emitted bundle, checked in.

3. **`tests/parity/interpreter.parity.test.ts`** for each fixture: TS parser parses `source_text`, TS interpreter runs it, asserts byte-equal to `expected_trace`. If `program_ir` is present, also asserts `parse(source_text) === program_ir` to catch parser drift independently.

4. **Drift discipline.** CI runs `export_golden_fixtures.py` and `git diff --exit-code` on the JSON. Stale fixtures fail CI. Regenerating fixtures is an explicit, reviewable PR step.

Rejected alternative: Pyodide-in-browser. ~10 MB payload, cold-start latency, awkward to call from the React step-through loop.

## 7. Execution panel (shared visual idiom)

Single component, shared by both tabs. Renders runtime state at a chosen step. Has no controls of its own.

**Props contract:**

```ts
interface ExecutionPanelProps {
  program: Program;
  trace: ExecutionTrace;
  stepIdx: number;                       // 0..trace.steps.length-1
  mode: "single" | "compare";
  modelOutput?: number[];                // required when mode === "compare"
  clampBadges?: boolean;                 // default true
}
```

**Layout** (single column on narrow screens, two on wide):

- **ProgramView** — full source with a `▶` PC marker on `program.instructions[steps[stepIdx].pc]`. Read-only here; the editor lives in `<Editor>`.
- **RegisterFile** — 8 cells (R0..R7) showing current values. The register written by step `stepIdx-1 → stepIdx` flashes once (200 ms background pulse).
- **StackView** — top-down, depth indicator `n / 16` at the bottom. PUSH/POP slide tiles in/out with the same 200 ms timing.
- **OutputStream** — append-only list of PRINT values. The latest emission flashes on the step that printed it.
- **Clamp badges** — values produced via `_clamp` get a tiny `⊏` marker (educational value: clamping is non-obvious).
- **Step indicator** — compact `step 12 / 47` plus the current opcode name.

**Compare-mode additions:** output stream renders two columns (ground truth, model); cells diff-highlight on disagreement; first divergent index anchored at the top of view.

**Not doing:** data-flow arrows between source/destination registers; timeline heatmaps; kinetic between-step animations beyond the diff flash. Toy-y animations distract researchers and don't help learners after the first 30 seconds.

## 8. Playground tab

```
┌─ LessonPlaylist ──┐  ┌─ Editor ─────────────┐  ┌─ ExecutionPanel ─┐
│ ▸ 1. Counter      │  │ LOAD  R0 5           │  │ (Section 7)      │
│ ▸ 2. Two regs     │  │ ADD   R0 R0 R0       │  │                  │
│ ▸ 3. First branch │  │ PRINT R0             │  │                  │
│ ▸ 4. Count-down   │  │ HALT                 │  │                  │
│ ▸ 5. Stack frame  │  │                      │  │                  │
│ ▸ 6. Free play    │  │                      │  │                  │
└───────────────────┘  └──────────────────────┘  └──────────────────┘
                       ┌─ StepControls ──────────────────────────┐
                       │ ⟲ reset  ◂ step  ▶ run  ▸ step  ⏯ speed │
                       │ step 3 / 12          ◀═══●═════▶        │
                       └─────────────────────────────────────────┘
```

**Lessons.** Hand-authored TS files under `src/lessons/`. Each lesson is `{ id, title, source, summary, expectedOutput }`. v1 ships ~6 lessons progressing along the difficulty axes: 1 reg → many regs → branch → loop → stack → free play. "Free play" is empty. Clicking a lesson populates the editor; nothing is locked.

**Editor.** CodeMirror 6 with a custom Tiny-VM language mode:

- Tokeniser (~50 LOC) recognises opcodes, registers, integer literals, labels (`L<digits>:` and `L<digits>` references), comments (`;` to end of line).
- Highlighting: opcode / register / literal / label / comment classes, themed via Tailwind.
- Diagnostics: every edit (debounced 150 ms) calls `parser.parse(source)`. Errors render as red squiggles with margin markers. After a successful parse, `verifier.validate(program)` adds yellow squiggles for well-formedness issues. Both come from `core/`.

**StepControls.** Step back / forward, reset, run-to-end, pause. Speed slider (1 step every 50 ms ↔ 1 s). Scrubber for direct jump. Keyboard: `→` step, `←` back, `space` run/pause, `r` reset.

**Run-loop wiring.** Editor → `parser` → `program` (state). On run or `stepIdx` change: if `program` changed since last run, call `interpreter.run(program)` → `trace` (memoised). If `interpreter.run` raises (overflow, etc.), the status row shows the error and the panel renders the partial trace up to the faulting step.

**Initial state.** The editor loads lesson #1 pre-populated with `stepIdx = 1`, so the first thing the user sees is meaningful state, not zeros.

## 9. Compare tab

```
┌─ Bundle loader ─────────────────────────────────────────────────────┐
│ Drop a .json file here, or pick one from /samples/                  │
│ Loaded: counter_len32_seed42_failed.json                            │
│   trajectory: 32 steps · branches: 0 · loops: 0 · stack: no         │
│   ground truth: [5, 25, -3]   model: [5, 25, 7]   ✗ diverges at #2  │
└─────────────────────────────────────────────────────────────────────┘

┌─ ProgramView ───────────────────┐  ┌─ RegisterFile ──┐
│ (read-only, Section 7)          │  │ (Section 7)     │
└─────────────────────────────────┘  └─────────────────┘

┌─ DivergencePanel ───────────────┐  ┌─ StackView ─────┐
│ idx │ ground truth │ model      │  │ (Section 7)     │
│  0  │      5       │   5     ✓  │  └─────────────────┘
│  1  │     25       │  25     ✓
│  2  │     −3       │   7     ✗  ← first divergence anchored here
│  3  │      …       │   …
└─────────────────────────────────┘
```

**Bundle format** (`core/types.ts`):

```ts
interface SerializedStep {
  pc: number;
  regs: number[];                  // length 8
  stack: number[];                 // 0..16
  emitted: number | null;
}

interface SerializedTrace {
  steps: SerializedStep[];
  output: number[];
  halted: boolean;
}

interface ComparisonBundle {
  schema: "tinyvm-viz/comparison/v1";
  meta: { generator: string; seed: number; spec?: object; tier?: string };
  source: string;                  // Tiny-VM source text
  groundTruth: { trace: SerializedTrace };
  prediction: {
    output: number[];              // model's predicted PRINT stream
    model?: string;
    decodeWarnings?: string[];     // value-stream decoded with warnings
  };
}
```

`SerializedTrace` is the wire form of `ExecutionTrace`; `core/interpreter.ts` exposes a pair of helpers to convert in both directions.

**Loading paths.** Drag-and-drop, file picker, dropdown of `samples/*.json`, or `?bundle=<url>` query param. Pages are shareable.

**Validation on load.** The bundle is parsed, `source` is re-parsed by `core/parser`, the program is re-run on the TS interpreter, and the resulting `output` is compared against `groundTruth.trace.output`. If they disagree, a banner reads *"This bundle's ground truth disagrees with the TS interpreter at step N — parity drift suspected."* The bundle still renders so the failure can be inspected.

**Divergence rules.**

- Index-aligned rows for the two value sequences; missing entries on either side render as `—` and count as divergences.
- First divergent row scrolls into view on load and is bordered.
- Step controls auto-position at the step that PRINTed the first divergent value, so the register file shows the state when things went wrong.

**Emitting bundles.** `tinyvm/scripts/export_comparison_bundle.py` wraps `(seed, generator, generator_kwargs, model_predictions)` and writes a `ComparisonBundle`. v1 ships ~5 hand-authored samples spanning pass / divergence / interpreter-error cases. Real model predictions slot in once Tier 1 produces them.

## 10. Tech stack and build

- **React 18 + Vite 5**, TypeScript strict (`strict: true`, `noUncheckedIndexedAccess: true`).
- **CodeMirror 6** for the editor.
- **Tailwind CSS** for styling. No component library.
- **State management:** `useState` / `useReducer` + a tiny `Context` for the currently-loaded program/trace. No Redux, no Zustand.
- **Routing:** `react-router-dom`. `/playground` (default), `/compare`, plus `?bundle=` query param.
- **Build:** `npm run build` → static `dist/`. `base: './'` for trivial static-host deployment.

## 11. Testing strategy

Three layers, all `vitest`:

| Layer | What it checks | Where |
|---|---|---|
| **core unit** | parser round-trip; interpreter semantics (clamp, DIV/0, JZ taken/not, fall-off-end, stack over/underflow); verifier rules (arity, label targets, PRINT-write, stack balance) | `tests/unit/core/*.test.ts` — framework-free, fast |
| **parity** | every fixture in `golden.json` round-trips: TS parser parses Python's `source_text`, TS interpreter reproduces `expected_trace` byte-equal; when `program_ir` is present in the fixture, also assert `parse(source_text) === program_ir` to catch parser drift independent of interpreter drift | `tests/parity/interpreter.parity.test.ts` |
| **component** | Editor surfaces parser errors as squiggles; StepControls updates `stepIdx`; DivergencePanel anchors the first divergent row; bundle validation catches malformed JSON | `tests/unit/components/*.test.tsx` — Vitest + jsdom + React Testing Library |

CI runs all three on every PR.

**Fixture refresh.** A CI step re-runs `export_golden_fixtures.py` and `git diff --exit-code tinyvm-viz/tests/fixtures/golden.json`. Stale fixtures fail loudly. Regenerating is an explicit reviewed PR step.

## 12. Error handling

| Failure | Surface |
|---|---|
| Parse error (bad syntax) | Editor squiggle + status-row message; previously valid `program` stays cached so the panel doesn't blank out |
| Verifier failure (unknown label, PRINT-without-write, etc.) | Yellow squiggle + status-row note. Program still runs — the interpreter is the source of truth in the playground; the validator is advisory |
| Interpreter error (stack over/underflow, step-cap, userop) | Status banner ("stack overflow at step 47"); panel renders partial trace up to the faulting step; step controls clamped |
| Comparison bundle: malformed JSON / schema mismatch | Loader rejects with explicit message; nothing populates downstream |
| Comparison bundle: ground truth disagrees with TS re-run | Loud banner ("parity drift suspected — fixture or interpreter changed"). Bundle still renders for inspection |
| Comparison bundle: model output not decodable | DivergencePanel renders the raw `output` array; `decodeWarnings` shown in a tooltip on the bundle-meta row |

Not built: a logging service, telemetry, error reporting, feature flags.

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| **TS interpreter drifts from Python** | Parity test suite + CI fixture-staleness check (§6, §11). Drift surfaces as red CI on the first PR that introduces it. |
| **Parser-vs-Python-renderer divergence** (TS parser accepts syntax that Python's `_tokens_to_text` never emits, or vice-versa) | Golden fixtures include both `source_text` and `program_ir`; parity asserts `parse(source_text) === program_ir`. Round-trip tests on the TS side use Python-generated text. |
| **CoT bundles arrive before v1.1** (research starts producing per-step register predictions) | `ComparisonBundle.prediction` is a flat shape; extending it with an optional `perStepRegisters` field is non-breaking. Banner in v1 warns if unrecognised fields are present. |
| **Tier 4 emits userop programs and there's nowhere to render them** | The TS `isa.ts` reserves userop slots from day one; loading a bundle with userops triggers an explicit "v1.1 feature" banner rather than a parser crash. |
| **Bundle gets large and slow** (very long Tier 2 trajectories) | `ExecutionTrace.steps` is bounded by program length (≤ 256 instructions × loop iterations ≤ a few thousand steps). Virtualise the ProgramView and DivergencePanel rows if profiling shows it matters; defer until measured. |

## 14. Open questions deferred to implementation

- **Source-text canonical form.** Python's `_tokens_to_text` is the de-facto source format. TS parser should accept that exact form *and* a slightly more permissive human-typed form (e.g., extra whitespace, mixed case opcodes). Decide on the permissive surface during parser implementation; canonical form for fixture round-tripping is non-negotiable.
- **Lesson content.** The six lessons need actual programs + summaries. Defer wording to implementation; the structure is fixed.
- **Sample bundle authoring.** v1 needs ~5 hand-crafted bundles spanning the pass/divergence/error space. These are content, not architecture — write them when the Compare tab is functional.
- **CoT bundle schema for v1.1.** Sketch only — the v1 `ComparisonBundle` shape is extensible.

## 15. References

- `Latent_State_as_Computer.docx` §3 (Tiny-VM specification), §7 (Tier 2 conditions), §9 (Tier 4 programmability).
- `docs/superpowers/specs/2026-05-15-tinyvm-module-design.md` — Python Tiny-VM module spec (parent of this tool).
- This spec is the input to the implementation plan, to be written next under `docs/superpowers/plans/`.
