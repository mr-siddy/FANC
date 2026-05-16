# Tiny-VM Visualizer — v1 Polish Design Spec

**Date:** 2026-05-16
**Authors:** Siddhant (@sidgraph), Claude (@claudeai)
**Status:** Approved for implementation planning
**Source:** Live UI feedback after first dev-server run; final code review on `spec/tinyvm-module` PR.
**Parent specs:** `docs/superpowers/specs/2026-05-16-tinyvm-viz-design.md`, `docs/superpowers/specs/2026-05-15-tinyvm-module-design.md`.

## 1. Purpose

Five quality-of-life improvements to the v1 Tiny-VM Visualizer, shipped as a single polish round. Each item addresses either a visible UX gap surfaced by running the dev server (no syntax highlighting, no keyboard shortcuts, samples bundles invisible) or a deferred-but-flagged item from the final code review (parity-fixture sparsity, missing CI workflow, ProgramView/PC alignment bug).

The work is purely additive and internal-quality. No new external dependencies are introduced. No schema changes to `ComparisonBundle` or `SerializedTrace`. No new pages or top-level features.

## 2. Scope

In scope:

- **Editor syntax highlighting** via CodeMirror `StreamLanguage`.
- **Compare-page samples dropdown** + three new sample bundles (`branched_pass`, `branched_divergence`, `stack_pop_underflow`).
- **Parity-fixture expansion** from 12 to ~50 fixtures, covering the stack+branch+loop combinations that are currently untested.
- **CI workflow** at `.github/workflows/ci.yml` running Python tests, TypeScript tests, the TS build, and a golden-fixture staleness check.
- **Keyboard shortcuts** in the Playground (`→` / `←` / `space` / `r`).
- **ProgramView ↔ instruction alignment fix**: parser exposes a `lineToInstIdx` map; ProgramView uses it for the PC arrow.

Out of scope (named so we don't drift):

- Custom highlight palette / theme tweaks beyond CodeMirror defaults.
- Tier 4 userop highlighting (handled by `invalid` tag for now — correct for v1).
- Lesson narratives, share-via-URL fragment, dataset browser.
- Deployment to GitHub Pages (the CI workflow verifies; deploy is a separate follow-up).
- Additional keyboard shortcuts beyond the four.
- Parser performance work.

## 3. Key design decisions

| # | Decision | Rationale |
|---|---|---|
| 1 | **CodeMirror `StreamLanguage` over Lezer or hand-rolled ViewPlugin.** | ~30 LOC, no build-step changes, sufficient for Tiny-VM's flat grammar. Lezer would require `@lezer/generator` + a `.grammar` build artefact for negligible benefit. |
| 2 | **Default highlightStyle, no custom palette.** | CodeMirror's defaults already distinguish keywords, registers, numbers, labels, and comments visibly. Custom palettes are out of scope. |
| 3 | **Unknown all-caps word → `invalid` tag.** | Keeps the visual cue (red background) consistent with the parser's "unknown opcode" diagnostic. Tier 4 userops correctly render as `invalid` until v1.1 wires them in. |
| 4 | **Vite `import.meta.glob` for samples dropdown.** | Zero-maintenance: drop a JSON in `samples/`, refresh, it appears. Static at build time, which is fine for v1. |
| 5 | **Hand-author the fault-case sample bundle.** | The Python `export_comparison_bundle.py` helper assumes happy execution. Extending it for fault cases is out of scope; one 30-line hand-authored JSON is cheaper than the refactor. |
| 6 | **Fixture sweep targets ~50 fixtures with explicit bucket coverage.** | Spec §6 calls for ~50; current 12 is below target. The expansion specifically closes the stack+branches+loops gap that the final review flagged. |
| 7 | **Three CI jobs, no matrix.** | Python tests, TS tests + build, and `golden.json` staleness check. No multi-version matrix; no deploy. Pure verification. |
| 8 | **Document-level keydown listener with CodeMirror priority.** | A `.cm-editor` ancestor check in the handler means typing in the editor is never hijacked. Standard explorable-explanation pattern. |
| 9 | **Parser produces `lineToInstIdx`; ProgramView consumes it.** | Preserves the user's original source formatting (comments, blank lines). Alternative — re-rendering canonical text — would lose those. |
| 10 | **`BundleMeta` gains one optional field (`interpreterError`).** | The smallest schema extension that lets fault bundles carry their human-readable error message. Backward-compatible (existing bundles work without it). |

## 4. File touches

```
tinyvm-viz/
├── src/
│   ├── core/
│   │   ├── cmLanguage.ts             # NEW — StreamLanguage definition
│   │   └── parser.ts                 # MODIFIED — add lineToInstIdx to ParseResult
│   ├── components/
│   │   ├── Editor.tsx                # MODIFIED — wire cmLanguage extension
│   │   ├── ProgramView.tsx           # MODIFIED — activePc → activeInstIdx + lineToInstIdx
│   │   └── ExecutionPanel.tsx        # MODIFIED — thread lineToInstIdx through
│   ├── pages/
│   │   ├── Playground.tsx            # MODIFIED — keyboard shortcuts; thread parseResult
│   │   └── Compare.tsx               # MODIFIED — samples dropdown; thread parseResult
│   └── ...
├── samples/
│   ├── branched_pass.json            # NEW
│   ├── branched_divergence.json      # NEW
│   └── stack_pop_underflow.json      # NEW (hand-authored, halted: false)
├── tests/
│   ├── unit/
│   │   ├── core/
│   │   │   ├── cmLanguage.test.ts    # NEW
│   │   │   └── parser.test.ts        # MODIFIED — lineToInstIdx cases
│   │   ├── components/
│   │   │   ├── ProgramView.test.tsx  # MODIFIED — comment-line alignment
│   │   │   ├── Playground.test.tsx   # MODIFIED — keyboard event tests
│   │   │   └── Compare.test.tsx      # MODIFIED — samples-dropdown test
│   │   └── samples.test.ts           # NEW — sweep over samples/*.json
│   └── fixtures/
│       └── golden.json               # REGENERATED — ~50 fixtures
└── ...

tinyvm/
├── scripts/
│   └── export_golden_fixtures.py     # MODIFIED — expanded sweep
└── tests/
    └── test_export_golden_fixtures.py # MODIFIED — bucket-coverage assertion

.github/
└── workflows/
    └── ci.yml                        # NEW
```

## 5. Syntax highlighting

**Module** (`src/core/cmLanguage.ts`):

```ts
import { StreamLanguage, StringStream } from "@codemirror/language";

const OPCODES = new Set([
  "LOAD", "MOV", "ADD", "SUB", "MUL", "DIV", "NEG", "EQ", "LT",
  "JZ", "JMP", "PUSH", "POP", "PRINT", "NOP", "HALT",
]);

export const tinyvm = StreamLanguage.define({
  token(stream: StringStream) {
    if (stream.eatSpace()) return null;
    if (stream.match(/^;.*/)) return "lineComment";
    if (stream.match(/^L\d+(?=\s*:)/)) return "labelName";   // label definition
    if (stream.match(/^L\d+/)) return "labelName";           // label reference
    if (stream.match(/^R[0-7]\b/)) return "variableName";
    if (stream.match(/^-?\d+\b/)) return "number";
    if (stream.match(/^[A-Z]+\b/)) {
      const word = stream.current();
      return OPCODES.has(word) ? "keyword" : "invalid";
    }
    stream.next();
    return null;
  },
  languageData: { commentTokens: { line: ";" } },
});
```

**Editor integration** (`src/components/Editor.tsx`): add `tinyvm` to the extensions array, alongside the existing `editorTheme`, `lineNumbers()`, etc.

**Token sequence semantics:**

| Surface | Tag sequence |
|---|---|
| `LOAD R3 -42` | `keyword`, `variableName`, `number` |
| `L3:ADD R0 R1 R2` | `labelName`, `keyword`, `variableName`, `variableName`, `variableName` |
| `JZ R1 L7` | `keyword`, `variableName`, `labelName` |
| `; comment` | `lineComment` |
| `FOO R0` | `invalid`, `variableName` |
| `DOUBLE R0 R1` (Tier 4 userop) | `invalid`, `variableName`, `variableName` |

CodeMirror's default `HighlightStyle.defaultHighlightStyle` colours these visibly — no theme customisation is needed.

## 6. Compare-page samples dropdown

`Compare.tsx` adds a `<select>` populated by Vite's eager-glob import:

```tsx
const sampleModules = import.meta.glob<{ default: ComparisonBundle }>(
  "/samples/*.json",
  { eager: true, import: "default" },
);
const samples = Object.entries(sampleModules).map(([path, bundle]) => ({
  filename: path.split("/").pop()!,
  bundle,
}));
```

Layout (replacing the current bare file input):

```
┌─ Bundle loader ─────────────────────────────────────────────────────┐
│ Load a sample: [ branched_pass.json ▾ ]                             │
│ — or drop a file: [ Choose File ]                                   │
│ Loaded: branched_pass.json                                          │
└─────────────────────────────────────────────────────────────────────┘
```

Selecting an option goes through the existing `validateBundle` → `setBundle` path. The `?bundle=` query param continues to take precedence on first mount; the dropdown is purely an interactive convenience.

## 7. Sample bundles (three new)

| File | Content | Origin |
|---|---|---|
| `samples/branched_pass.json` | `gen_branched(seed=0, GenSpec(n=24, k=4, b=1, l=0))`; `prediction.output == groundTruth.trace.output`. Tests the "researcher loads a passing bundle and uses the step-through to understand model behaviour" flow. | Emit via `python -m tinyvm.scripts.export_comparison_bundle ...`. |
| `samples/branched_divergence.json` | Same program; `prediction.output` differs from `groundTruth.trace.output` at the second PRINT (replace value with `999`). Tests the divergence-detection path. | Emit via `export_comparison_bundle.py` with a custom `prediction_output` list. |
| `samples/stack_pop_underflow.json` | Hand-authored: a 5-instruction program that POPs from an empty stack at step 2. `groundTruth.trace.halted == false`, `steps` truncated at the fault, and `meta.interpreterError == "stack underflow at step 2"`. Tests the Compare page's robustness to non-halting bundles. | Hand-authored — the Python helper assumes happy execution and extending it for fault paths is out of scope. |

**Compare-page robustness changes:**

1. **Skip the TS re-run for fault bundles.** Today's `reRun` memo unconditionally calls `parse + run` on `bundle.source`. For a fault bundle, `run()` throws and the existing catch surfaces a `parity drift suspected` banner — which is the wrong message (the bundle is *intentionally* a fault case; the TS throw is the expected behaviour). New behaviour: if `bundle.groundTruth.trace.halted === false`, skip the re-run comparison entirely and render the bundle as authored.

2. **New amber banner for fault bundles.** When `halted === false`, render `"interpreter halted with: <meta.interpreterError>"` (fall back to `"interpreter halted before completion"` if `meta.interpreterError` is absent). The DivergencePanel still renders normally; the truncated `trace.steps` renders without crashing.

**Schema extension.** `BundleMeta` gains a single optional field:

```ts
interface BundleMeta {
  generator: string;
  seed: number;
  spec?: Record<string, unknown>;
  tier?: string;
  interpreterError?: string;   // NEW — populated by fault bundles
}
```

This is a backward-compatible addition (existing bundles omit the field). `validateBundle` doesn't need to check it — when absent, the banner uses the generic fallback message.

## 8. Parity fixture expansion

`tinyvm/scripts/export_golden_fixtures.py` currently produces 12 fixtures. Expand the sweep:

| Generator | Now | Target | New cases |
|---|---|---|---|
| `gen_counter` | 4 | 8 | longer programs (n ∈ {12, 16, 24}); seeds producing negative literals and clamp ceilings |
| `gen_register_trace` | 4 | 12 | longer trajectories (n ∈ {48, 64}); wider active sets (k ∈ {6, 8}); additional seeds |
| `gen_branched` | 4 | 30 | branches-and-loops, branches-and-stack, **stack+branches+loops together** (currently missing); deeper cases (b=8, l=16); multiple `stack_frames` values |

Concretely: add ~15 `BRANCHED_SPECS` entries combining stack with branches and loops. The current sweep has zero fixtures where `use_stack=True` AND `b>0` AND `l>0`, which means a PUSH/POP-vs-JZ-back-edge bug would not be caught by parity tests. The new sweep guarantees at least one fixture in each of these four buckets:

- `use_stack && b>0`
- `use_stack && l>0`
- `b>0 && l>0`
- `use_stack && b>0 && l>0`

A new Python test asserts this bucket coverage:

```python
def test_branched_sweep_covers_combinations():
    by_bucket = {"sb": 0, "sl": 0, "bl": 0, "sbl": 0}
    for f in build_fixtures():
        if f["generator"] != "gen_branched":
            continue
        s = f["spec"]
        if s["use_stack"] and s["b"] > 0:                                by_bucket["sb"] += 1
        if s["use_stack"] and s["l"] > 0:                                by_bucket["sl"] += 1
        if s["b"] > 0 and s["l"] > 0:                                    by_bucket["bl"] += 1
        if s["use_stack"] and s["b"] > 0 and s["l"] > 0:                 by_bucket["sbl"] += 1
    for bucket, n in by_bucket.items():
        assert n >= 1, f"no fixture in bucket {bucket}"
```

`golden.json` is regenerated by re-running `python -m tinyvm.scripts.export_golden_fixtures` and the file is committed. The existing TS parity test auto-discovers the new entries — no test change needed.

## 9. CI workflow

`.github/workflows/ci.yml`:

```yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:
jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -e .
      - run: python -m pytest tinyvm/ -v

  typescript:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: tinyvm-viz
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: tinyvm-viz/package-lock.json
      - run: npm ci
      - run: npm test
      - run: npm run build

  golden-fixture-staleness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -e .
      - run: python -m tinyvm.scripts.export_golden_fixtures
      - name: Verify golden.json is up-to-date
        run: git diff --exit-code tinyvm-viz/tests/fixtures/golden.json
```

Three independent jobs. No secrets, no deploy. The third job is the spec §6 "drift discipline" promise made real: editing the Python interpreter without regenerating fixtures fails CI with a diff message.

The TS-side and Python-side test counts after this round (~104 TS, ~131 Python) should both be present in CI logs for at-a-glance verification.

## 10. Keyboard shortcuts

`Playground.tsx` adds a single document-level `keydown` listener:

```tsx
useEffect(() => {
  const onKey = (e: KeyboardEvent) => {
    const active = document.activeElement as HTMLElement | null;
    if (active && (active.closest(".cm-editor") || active.tagName === "INPUT" || active.tagName === "TEXTAREA")) return;

    switch (e.key) {
      case "ArrowRight":
        e.preventDefault();
        setStepIdx((s) => Math.min(s + 1, maxStep));
        break;
      case "ArrowLeft":
        e.preventDefault();
        setStepIdx((s) => Math.max(s - 1, 0));
        break;
      case " ":
        e.preventDefault();
        setRunning((r) => !r);
        break;
      case "r":
      case "R":
        if (e.metaKey || e.ctrlKey) return;
        e.preventDefault();
        setStepIdx(0);
        break;
    }
  };
  document.addEventListener("keydown", onKey);
  return () => document.removeEventListener("keydown", onKey);
}, [maxStep]);
```

**Focus discipline:** `.cm-editor` ancestor check stops the editor from being hijacked. `INPUT` / `TEXTAREA` check covers the file picker on the Compare tab and any future form fields. `⌘R` / `Ctrl-R` continues to refresh the page (modifier check).

**Compare tab:** the same shortcuts are useful but lower priority. Out of scope for this round — Compare uses StepControls only.

## 11. ProgramView alignment fix

**Today's bug.** `ProgramView` does `source.split("\n").filter(l => l.length > 0)` and treats array index as instruction index. A comment-only line (`; this is a header`) survives the filter but doesn't correspond to an instruction, so the `▶` PC arrow points one row off.

**Fix.** Surface a line-to-instruction map from the parser; pass it into `ProgramView` alongside `activeInstIdx`.

**Parser change** (`src/core/parser.ts`):

```ts
export interface ParseResult {
  program?: Program;
  errors: ParseError[];
  /** lineToInstIdx[i] = instruction index for source line i (0-indexed),
   *  or null if the line is blank, comment-only, or unparseable. */
  lineToInstIdx: (number | null)[];
}
```

The existing `for (let li = 0; ...)` loop already iterates lines. Record the mapping inline: push `null` for blank/comment-only/errored lines, push `insts.length` (the next instruction's index) on successful parses. Lines that become label-only synthesised NOPs DO get an index — that NOP is a real instruction.

**ProgramView change** (`src/components/ProgramView.tsx`):

```ts
interface ProgramViewProps {
  source: string;
  activeInstIdx: number | null;
  lineToInstIdx: readonly (number | null)[];
}
```

Render every line of the unfiltered source (drop the `.filter(l => l.length > 0)`). Each line:

- if `lineToInstIdx[i] === activeInstIdx && activeInstIdx !== null`: highlighted, `▶` marker, `data-active="true"`.
- if `lineToInstIdx[i] == null` (null or undefined — handles trailing-newline overflow when source ends with `\n`): rendered dim (`text-slate-400`), no marker, `data-active="false"`.
- otherwise: normal styling, no marker, `data-active="false"`.

**Trailing newline note.** Tiny-VM canonical text always ends with `\n`, so `source.split("\n")` yields an extra empty trailing element. The parser's `lineToInstIdx` array may be one shorter than the split. The view uses `lineToInstIdx[i] ?? null` to treat overflow as "no instruction" — the trailing empty line renders as a no-op dim row.

**ExecutionPanel change.** Currently computes `step.pc` and passes it as `activePc`. Now passes `activeInstIdx={step.pc}` (the field rename is intentional — `pc` is in instruction-index space, and the new ProgramView prop name reflects that) plus the new `lineToInstIdx` array.

**Caller plumbing.** Both `Playground.tsx` and `Compare.tsx` parse the source already; they need to also retain the parser's `lineToInstIdx` and pass it through ExecutionPanel.

## 12. Testing strategy

| Item | New / modified tests | Where |
|---|---|---|
| Syntax highlighting | Token-sequence unit test against `tinyvm` language (~6 source snippets, asserts tag arrays); Editor smoke continues to pass | `tests/unit/core/cmLanguage.test.ts` (new) |
| Samples dropdown | Render `<Compare />`, select a sample, assert bundle loaded; sample-content sweep validates every `samples/*.json` via `validateBundle` and (for non-fault bundles) confirms `run(parse(source)) === groundTruth.trace.output` | `tests/unit/components/Compare.test.tsx` (modified); `tests/unit/samples.test.ts` (new) |
| Fixture expansion | Bucket-coverage Python test; parity suite auto-discovers extra fixtures | `tinyvm/tests/test_export_golden_fixtures.py` (modified); TS parity test unchanged |
| CI workflow | Manual review of `ci.yml`; first push exercises it | n/a — YAML is reviewed, not tested |
| Keyboard shortcuts | `fireEvent.keyDown(document, { key: "ArrowRight" })` advances `stepIdx`; focus the editor and assert the keypress is ignored | `tests/unit/components/Playground.test.tsx` (modified) |
| ProgramView alignment | `parse("; header\nLOAD R0 5\n\nHALT\n").lineToInstIdx === [null, 0, null, 1]`; ProgramView with comment-line source and `activeInstIdx=1` shows `data-active=true` on the right row | `tests/unit/core/parser.test.ts` (modified); `tests/unit/components/ProgramView.test.tsx` (modified) |

Estimated delta: **+10 to +12** TS tests, **+1 to +2** Python tests. Final TS suite ≈ 104–106; Python ≈ 130–131.

**No-regression.** Existing tests pass. The cross-cutting refactor is the `ProgramView` prop rename (`activePc → activeInstIdx`) plus the new `lineToInstIdx` prop; three callers update (Playground, Compare, ExecutionPanel). The existing ProgramView test rewrites slightly to pass the new prop shape.

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| **StreamLanguage token grammar drifts from parser.** A grammar-only edit (e.g., adding a userop opcode to OPCODES) could highlight valid-looking syntax that the parser still rejects, or vice versa. | The token sequence unit test on `cmLanguage.ts` is hand-authored, not generated from `parser.ts`. Visual highlighting is informational; the parser is the source of truth for diagnostics. Disagreement is harmless (the linter wins). |
| **`import.meta.glob` is build-time-static.** Adding a sample JSON to `samples/` does not appear in a running dev server until restart, and never appears in a deployed build until the next build. | Document in README; not a real production concern because v1 ships a fixed set of samples. |
| **Hand-authored fault bundle drifts from interpreter behaviour.** If the interpreter's stack-underflow message changes, the bundle's `meta.interpreterError` field becomes stale. | `meta.interpreterError` is informational only — the Compare page renders the bundle correctly regardless. A future iteration can re-emit the bundle via an extended Python helper. |
| **CI workflow doesn't run on a fork's first PR** (permissions). | Out of scope for this round; ship the workflow on `main`, document the limitation. |
| **`lineToInstIdx` confuses callers that previously used `activePc`.** | The prop rename is a forcing function — TypeScript will fail compilation on any caller that didn't update. Catches drift at build time. |

## 14. Open questions deferred to implementation

- **Comment formatting in samples.** Hand-authored `stack_pop_underflow.json` needs to decide whether to include the source's leading `; This program POPs from empty stack` comment line. Decide at authoring time.
- **CI Node and Python versions.** Spec says Node 20 / Python 3.11. If the project locks specific versions later, update the workflow.
- **Keyboard shortcut for "step to next PRINT"** is tempting but out of scope; flag as a possible Tier B item if pedagogical use surfaces a need.

## 15. References

- `docs/superpowers/specs/2026-05-16-tinyvm-viz-design.md` (parent v1 spec).
- Final code review on `spec/tinyvm-module` PR — issues 5 (fixture expansion), 6 (CI workflow), 7 (keyboard shortcuts), 3 (ProgramView alignment).
- Live UI feedback from first dev-server run (syntax highlighting absence).
- This spec is the input to the implementation plan, to be written next under `docs/superpowers/plans/`.
