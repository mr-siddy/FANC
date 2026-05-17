# Tiny-VM Visualizer v1 Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the five Tier A polish items to v1 of the Tiny-VM Visualizer: CodeMirror syntax highlighting, Compare-page samples dropdown + three new bundles, parity-fixture expansion + CI workflow, Playground keyboard shortcuts, and the ProgramView↔instruction alignment fix.

**Architecture:** Additive, internal-quality polish. No new external dependencies, no schema changes other than one optional `BundleMeta.interpreterError?` field. Cross-cutting work centres on a parser-exposed `lineToInstIdx` map that flows through `ExecutionPanel` to a refactored `ProgramView`.

**Tech Stack:** TypeScript strict, React 18, CodeMirror 6 (`@codemirror/language`'s `StreamLanguage`), Vite 5 `import.meta.glob`, Vitest, Python 3.11 (`tinyvm` package), GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-05-16-tinyvm-viz-polish-design.md`.

---

## File touches

```
tinyvm-viz/
├── src/
│   ├── core/
│   │   ├── cmLanguage.ts             # NEW — StreamLanguage definition
│   │   ├── parser.ts                 # MODIFIED — add lineToInstIdx to ParseResult
│   │   └── types.ts                  # MODIFIED — BundleMeta.interpreterError?
│   ├── components/
│   │   ├── Editor.tsx                # MODIFIED — wire cmLanguage extension
│   │   ├── ProgramView.tsx           # MODIFIED — activePc → activeInstIdx + lineToInstIdx
│   │   └── ExecutionPanel.tsx        # MODIFIED — thread lineToInstIdx through
│   └── pages/
│       ├── Playground.tsx            # MODIFIED — keyboard shortcuts + thread lineToInstIdx
│       └── Compare.tsx               # MODIFIED — samples dropdown + fault banner + thread lineToInstIdx
├── samples/
│   ├── branched_pass.json            # NEW
│   ├── branched_divergence.json      # NEW
│   └── stack_pop_underflow.json      # NEW (hand-authored, halted: false)
├── tests/
│   ├── unit/
│   │   ├── core/
│   │   │   ├── cmLanguage.test.ts    # NEW
│   │   │   └── parser.test.ts        # APPEND — lineToInstIdx cases
│   │   ├── components/
│   │   │   ├── ProgramView.test.tsx  # MODIFIED — comment-line alignment
│   │   │   ├── Playground.test.tsx   # APPEND — keyboard event tests
│   │   │   └── Compare.test.tsx      # APPEND — samples dropdown + fault banner tests
│   │   └── samples.test.ts           # NEW — sweep over samples/*.json
│   └── fixtures/
│       └── golden.json               # REGENERATED — ~50 fixtures
└── ...

tinyvm/
├── scripts/
│   └── export_golden_fixtures.py     # MODIFIED — expanded sweep
└── tests/
    └── test_export_golden_fixtures.py # APPEND — bucket-coverage assertion

.github/
└── workflows/
    └── ci.yml                        # NEW
```

---

## Phase A — Syntax highlighting

### Task 1: `cmLanguage.ts` — StreamLanguage token grammar

**Files:**
- Create: `tinyvm-viz/src/core/cmLanguage.ts`
- Create: `tinyvm-viz/tests/unit/core/cmLanguage.test.ts`

- [ ] **Step 1: Write failing tests**

```ts
import { describe, it, expect } from "vitest";
import { tinyvm } from "@/core/cmLanguage";
import { EditorState } from "@codemirror/state";
import { LanguageSupport } from "@codemirror/language";

function tagSequence(source: string): string[] {
  const state = EditorState.create({ doc: source, extensions: [new LanguageSupport(tinyvm)] });
  const tags: string[] = [];
  // Iterate the StreamLanguage stream directly by hand-tokenising each line.
  // We test tinyvm's token(stream) function via a tiny driver below; this
  // avoids depending on CodeMirror's syntax-tree internals.
  return tags;
}

describe("cmLanguage: token function", () => {
  // We drive the StreamLanguage token function manually to get tag sequences.
  function tokens(line: string): string[] {
    const ts = (tinyvm as any).streamParser.token;
    const out: string[] = [];
    const stream: any = {
      pos: 0,
      string: line,
      eatSpace() {
        const m = this.string.slice(this.pos).match(/^\s+/);
        if (!m) return false;
        this.pos += m[0].length;
        return true;
      },
      match(re: RegExp) {
        const s = this.string.slice(this.pos);
        const m = s.match(re);
        if (!m || m.index !== 0) return null;
        this.pos += m[0].length;
        this._lastMatch = m[0];
        return m;
      },
      next() {
        this._lastMatch = this.string[this.pos];
        this.pos += 1;
      },
      current() { return this._lastMatch ?? ""; },
      sol() { return this.pos === 0; },
      eol() { return this.pos >= this.string.length; },
    };
    while (!stream.eol()) {
      const tag = ts(stream, null);
      if (tag !== null) out.push(tag);
    }
    return out;
  }

  it("tags LOAD opcode + register + integer literal", () => {
    expect(tokens("LOAD R3 -42")).toEqual(["keyword", "variableName", "number"]);
  });

  it("tags a label-defined line and arg registers", () => {
    expect(tokens("L3:ADD R0 R1 R2")).toEqual(["labelName", "keyword", "variableName", "variableName", "variableName"]);
  });

  it("tags JZ with a label reference", () => {
    expect(tokens("JZ R1 L7")).toEqual(["keyword", "variableName", "labelName"]);
  });

  it("tags a comment line", () => {
    expect(tokens("; this is a comment")).toEqual(["lineComment"]);
  });

  it("tags an unknown all-caps word as invalid", () => {
    expect(tokens("FOO R0")).toEqual(["invalid", "variableName"]);
  });

  it("tags a userop symbol (e.g. DOUBLE) as invalid in v1", () => {
    expect(tokens("DOUBLE R0 R1")).toEqual(["invalid", "variableName", "variableName"]);
  });
});

// Eat unused imports so TS strict doesn't complain
void tagSequence;
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd /Users/sidgraph/FANC/tinyvm-viz && npx vitest run tests/unit/core/cmLanguage.test.ts`
Expected: module not found.

- [ ] **Step 3: Create `tinyvm-viz/src/core/cmLanguage.ts`**

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
    if (stream.match(/^L\d+(?=\s*:)/)) return "labelName";
    if (stream.match(/^L\d+/)) return "labelName";
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

- [ ] **Step 4: Run tests and confirm pass**

Run: `cd /Users/sidgraph/FANC/tinyvm-viz && npx vitest run tests/unit/core/cmLanguage.test.ts`
Expected: 6 pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/sidgraph/FANC
git add tinyvm-viz/src/core/cmLanguage.ts tinyvm-viz/tests/unit/core/cmLanguage.test.ts
git commit -m "feat(viz): cmLanguage — StreamLanguage token grammar for Tiny-VM"
```

---

### Task 2: Wire `cmLanguage` into the Editor

**Files:**
- Modify: `tinyvm-viz/src/components/Editor.tsx`

- [ ] **Step 1: Add the import and extension**

In `tinyvm-viz/src/components/Editor.tsx`, add to the imports:

```tsx
import { tinyvm } from "@/core/cmLanguage";
```

In the `useEffect` that creates `EditorState`, add `tinyvm` to the extensions array (right after `lineNumbers()`):

```tsx
      extensions: [
        lineNumbers(),
        tinyvm,
        history(),
        highlightActiveLine(),
        editorTheme,
        keymap.of([...defaultKeymap, ...historyKeymap]),
        linter(tinyvmLinter, { delay: 150 }),
        EditorView.updateListener.of((u) => {
          if (u.docChanged) onChange(u.state.doc.toString());
        }),
      ],
```

- [ ] **Step 2: Run all tests and confirm pass**

Run: `cd /Users/sidgraph/FANC/tinyvm-viz && npm test`
Expected: previous Editor smoke tests still pass; new cmLanguage tests still pass.

- [ ] **Step 3: Build**

Run: `cd /Users/sidgraph/FANC/tinyvm-viz && npm run build`
Expected: clean.

- [ ] **Step 4: Commit**

```bash
cd /Users/sidgraph/FANC
git add tinyvm-viz/src/components/Editor.tsx
git commit -m "feat(viz): wire cmLanguage into Editor"
```

---

## Phase B — Parser `lineToInstIdx` + ProgramView refactor

### Task 3: Parser exposes `lineToInstIdx`

**Files:**
- Modify: `tinyvm-viz/src/core/parser.ts`
- Modify: `tinyvm-viz/tests/unit/core/parser.test.ts` (append)

- [ ] **Step 1: Write failing tests**

Append to `tinyvm-viz/tests/unit/core/parser.test.ts`:

```ts
describe("parser: lineToInstIdx", () => {
  it("maps a clean multi-line program one-to-one", () => {
    const src = "LOAD R0 5\nADD R0 R0 R0\nPRINT R0\nHALT\n";
    const { program, errors, lineToInstIdx } = parse(src);
    expect(errors).toEqual([]);
    expect(program!.instructions).toHaveLength(4);
    // Lines 0..3 are the four instructions; trailing empty line is null.
    expect(lineToInstIdx.slice(0, 4)).toEqual([0, 1, 2, 3]);
  });

  it("maps comment-only and blank lines to null", () => {
    const src = "; header\nLOAD R0 5\n\nHALT\n";
    const { program, errors, lineToInstIdx } = parse(src);
    expect(errors).toEqual([]);
    expect(program!.instructions.map((i) => i.op)).toEqual([Op.LOAD, Op.HALT]);
    expect(lineToInstIdx.slice(0, 4)).toEqual([null, 0, null, 1]);
  });

  it("maps a label-only line to a synthesised NOP (real instruction)", () => {
    const src = "L0:\nLOAD R0 1\nHALT\n";
    const { program, errors, lineToInstIdx } = parse(src);
    expect(errors).toEqual([]);
    expect(program!.instructions).toHaveLength(3);
    expect(lineToInstIdx.slice(0, 3)).toEqual([0, 1, 2]);
  });
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd /Users/sidgraph/FANC/tinyvm-viz && npx vitest run tests/unit/core/parser.test.ts`
Expected: TypeScript error / `lineToInstIdx` not on `ParseResult`.

- [ ] **Step 3: Add `lineToInstIdx` to `ParseResult`**

In `tinyvm-viz/src/core/parser.ts`, update the interface:

```ts
export interface ParseResult {
  program?: Program;
  errors: ParseError[];
  /** lineToInstIdx[i] = instruction index for source line i (0-indexed),
   *  or null if the line is blank, comment-only, or unparseable. */
  lineToInstIdx: (number | null)[];
}
```

- [ ] **Step 4: Populate `lineToInstIdx` inside `parse()`**

Inside `parse()`, before the loop:

```ts
  const lineToInstIdx: (number | null)[] = [];
```

Inside the loop, replace the existing `if (stripped.length === 0) continue;` block with:

```ts
    if (stripped.length === 0) {
      lineToInstIdx.push(null);
      continue;
    }
```

For each path that pushes an `Instruction` to `insts`, also append the new instruction's index to `lineToInstIdx`. There are exactly two such paths:

1. **Bare-label-only line** (after `tokens.length === 0` check): change

   ```ts
       if (tokens.length === 0) {
         insts.push({ op: Op.NOP, args: [], label, target: undefined });
         continue;
       }
   ```

   to:

   ```ts
       if (tokens.length === 0) {
         lineToInstIdx.push(insts.length);
         insts.push({ op: Op.NOP, args: [], label, target: undefined });
         continue;
       }
   ```

2. **Successful instruction parse** at the bottom of the loop. Before:

   ```ts
       insts.push({ op, args, label, target });
   ```

   becomes:

   ```ts
       lineToInstIdx.push(insts.length);
       insts.push({ op, args, label, target });
   ```

3. **Error paths** (unknown opcode, wrong arity, bad register, etc.) each `continue` after pushing an error. Add `lineToInstIdx.push(null);` immediately before each `continue;` in those error branches. There are four such `continue` statements; each gets the same push.

- [ ] **Step 5: Update both return statements**

The function has two `return` sites at the bottom:

```ts
  if (errors.length > 0) return { errors };
  try {
    return { program: buildProgram(insts), errors: [] };
  } catch (e) {
    const msg = (e as Error).message;
    const m = msg.match(/duplicate label: (L\d+)/);
    if (m) {
      const lbl = m[1]!;
      const lineNum = lines.findIndex((l, idx) => idx > 0 && stripComment(l).trim().startsWith(`${lbl}:`)) + 1;
      return { errors: [{ line: lineNum || 0, message: msg }] };
    }
    return { errors: [{ line: 0, message: msg }] };
  }
```

Each must include `lineToInstIdx`. Replace with:

```ts
  if (errors.length > 0) return { errors, lineToInstIdx };
  try {
    return { program: buildProgram(insts), errors: [], lineToInstIdx };
  } catch (e) {
    const msg = (e as Error).message;
    const m = msg.match(/duplicate label: (L\d+)/);
    if (m) {
      const lbl = m[1]!;
      const lineNum = lines.findIndex((l, idx) => idx > 0 && stripComment(l).trim().startsWith(`${lbl}:`)) + 1;
      return { errors: [{ line: lineNum || 0, message: msg }], lineToInstIdx };
    }
    return { errors: [{ line: 0, message: msg }], lineToInstIdx };
  }
```

- [ ] **Step 6: Run tests and confirm pass**

Run: `cd /Users/sidgraph/FANC/tinyvm-viz && npx vitest run tests/unit/core/parser.test.ts`
Expected: previous parser tests still pass; 3 new lineToInstIdx tests pass.

- [ ] **Step 7: Commit**

```bash
cd /Users/sidgraph/FANC
git add tinyvm-viz/src/core/parser.ts tinyvm-viz/tests/unit/core/parser.test.ts
git commit -m "feat(viz): parser exposes lineToInstIdx map"
```

---

### Task 4: ProgramView refactor + caller updates (atomic)

**Files:**
- Modify: `tinyvm-viz/src/components/ProgramView.tsx`
- Modify: `tinyvm-viz/src/components/ExecutionPanel.tsx`
- Modify: `tinyvm-viz/src/pages/Playground.tsx`
- Modify: `tinyvm-viz/src/pages/Compare.tsx`
- Modify: `tinyvm-viz/tests/unit/components/ProgramView.test.tsx`

This task changes a public prop shape and must update all callers in one atomic commit so the TS build stays green.

- [ ] **Step 1: Rewrite the ProgramView test**

Replace `tinyvm-viz/tests/unit/components/ProgramView.test.tsx` with:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProgramView } from "@/components/ProgramView";

describe("ProgramView", () => {
  it("renders each source line and marks the active instruction with ▶", () => {
    const source = "LOAD R0 5\nADD R0 R0 R0\nPRINT R0\nHALT\n";
    const lineToInstIdx = [0, 1, 2, 3];
    render(<ProgramView source={source} activeInstIdx={1} lineToInstIdx={lineToInstIdx} />);
    expect(screen.getByTestId("pgm-line-0")).toHaveTextContent("LOAD R0 5");
    const active = screen.getByTestId("pgm-line-1");
    expect(active).toHaveTextContent("ADD R0 R0 R0");
    expect(active).toHaveAttribute("data-active", "true");
    expect(screen.getByTestId("pgm-line-2")).toHaveAttribute("data-active", "false");
  });

  it("dims comment-only lines and aligns PC arrow with the right instruction", () => {
    const source = "; header\nLOAD R0 5\n\nHALT\n";
    const lineToInstIdx = [null, 0, null, 1];
    render(<ProgramView source={source} activeInstIdx={1} lineToInstIdx={lineToInstIdx} />);
    expect(screen.getByTestId("pgm-line-0")).toHaveAttribute("data-active", "false");  // comment
    expect(screen.getByTestId("pgm-line-1")).toHaveAttribute("data-active", "false");  // LOAD (inst 0)
    expect(screen.getByTestId("pgm-line-3")).toHaveAttribute("data-active", "true");   // HALT (inst 1)
  });

  it("treats trailing-newline overflow lines as dim no-ops", () => {
    const source = "LOAD R0 5\n";  // splits to ['LOAD R0 5', '']
    const lineToInstIdx = [0];     // length 1; index 1 overflows
    render(<ProgramView source={source} activeInstIdx={0} lineToInstIdx={lineToInstIdx} />);
    expect(screen.getByTestId("pgm-line-0")).toHaveAttribute("data-active", "true");
    expect(screen.getByTestId("pgm-line-1")).toHaveAttribute("data-active", "false");
  });
});
```

- [ ] **Step 2: Run and confirm the test compiles but fails on assertions**

Run: `cd /Users/sidgraph/FANC/tinyvm-viz && npx vitest run tests/unit/components/ProgramView.test.tsx`
Expected: type errors (props don't match yet).

- [ ] **Step 3: Rewrite `ProgramView.tsx`**

Replace `tinyvm-viz/src/components/ProgramView.tsx` with:

```tsx
interface ProgramViewProps {
  source: string;
  activeInstIdx: number | null;
  lineToInstIdx: readonly (number | null)[];
}

export function ProgramView({ source, activeInstIdx, lineToInstIdx }: ProgramViewProps) {
  const lines = source.split("\n");
  return (
    <pre className="text-sm font-mono leading-6 bg-white border border-slate-200 rounded p-3 overflow-auto">
      {lines.map((line, i) => {
        const instIdx = lineToInstIdx[i] ?? null;
        const active = instIdx !== null && instIdx === activeInstIdx;
        const dim = instIdx === null;
        return (
          <div
            key={i}
            data-testid={`pgm-line-${i}`}
            data-active={active ? "true" : "false"}
            className={`flex gap-2 ${active ? "bg-amber-50" : ""} ${dim ? "text-slate-400" : "text-slate-800"}`}
          >
            <span className="w-4 text-amber-600">{active ? "▶" : " "}</span>
            <span>{line}</span>
          </div>
        );
      })}
    </pre>
  );
}
```

- [ ] **Step 4: Update `ExecutionPanel.tsx` to thread the new props**

In `tinyvm-viz/src/components/ExecutionPanel.tsx`, update the props interface:

```tsx
interface ExecutionPanelProps {
  program: Program;
  source: string;
  trace: SerializedTrace;
  stepIdx: number;
  mode: "single" | "compare";
  modelOutput?: readonly number[];
  lineToInstIdx: readonly (number | null)[];
}
```

In the destructure at the top of the function, add `lineToInstIdx`. Then update the `<ProgramView>` call to pass:

```tsx
        <ProgramView source={source} activeInstIdx={step.pc} lineToInstIdx={lineToInstIdx} />
```

- [ ] **Step 5: Update `Playground.tsx`**

The existing `useMemo` returns `{ program, errors }`. Destructure `lineToInstIdx` too and pass it to `ExecutionPanel`:

Change:

```tsx
  const { program, errors } = useMemo(() => parse(source), [source]);
```

to:

```tsx
  const { program, errors, lineToInstIdx } = useMemo(() => parse(source), [source]);
```

In the `<ExecutionPanel>` JSX at the bottom, add the prop:

```tsx
        {program && trace && (
          <ExecutionPanel
            program={program}
            source={source}
            trace={trace}
            stepIdx={safeStep}
            mode="single"
            lineToInstIdx={lineToInstIdx}
          />
        )}
```

- [ ] **Step 6: Update `Compare.tsx`**

In the `reRun` `useMemo`, capture `lineToInstIdx` too:

```tsx
  const reRun = useMemo(() => {
    if (!bundle) return null;
    const { program, errors, lineToInstIdx } = parse(bundle.source);
    if (!program || errors.length) return { ok: false as const, message: "bundle.source did not parse", lineToInstIdx };
    try {
      const trace = serializeTrace(run(program));
      const same = JSON.stringify(trace.output) === JSON.stringify(bundle.groundTruth.trace.output);
      return { ok: same, program, tsTrace: trace, lineToInstIdx };
    } catch (e) {
      return { ok: false as const, message: (e as Error).message, lineToInstIdx };
    }
  }, [bundle]);
```

Pass it to `<ExecutionPanel>` at the bottom:

```tsx
      {reRun && "program" in reRun && (
        <ExecutionPanel
          program={reRun.program}
          source={bundle.source}
          trace={trace}
          stepIdx={safeStep}
          mode="compare"
          modelOutput={bundle.prediction.output}
          lineToInstIdx={reRun.lineToInstIdx}
        />
      )}
```

- [ ] **Step 7: Run all tests**

Run: `cd /Users/sidgraph/FANC/tinyvm-viz && npm test`
Expected: all existing tests still pass; the three new ProgramView tests pass.

The Playground test that asserts `screen.getByTestId("pgm-line-0")).toHaveTextContent("LOAD R0 3")` after clicking "Two registers" should still pass — the source format is unchanged, and `lineToInstIdx` for the canonical 5-line program is `[0, 1, 2, 3, 4]`.

- [ ] **Step 8: Build**

Run: `cd /Users/sidgraph/FANC/tinyvm-viz && npm run build`
Expected: clean (the `noEmit: true` from earlier means tsc is a type-checker only).

- [ ] **Step 9: Commit**

```bash
cd /Users/sidgraph/FANC
git add tinyvm-viz/src/components/ProgramView.tsx \
        tinyvm-viz/src/components/ExecutionPanel.tsx \
        tinyvm-viz/src/pages/Playground.tsx \
        tinyvm-viz/src/pages/Compare.tsx \
        tinyvm-viz/tests/unit/components/ProgramView.test.tsx
git commit -m "fix(viz): ProgramView aligns PC arrow via parser lineToInstIdx"
```

---

## Phase C — Keyboard shortcuts

### Task 5: Playground keyboard shortcuts

**Files:**
- Modify: `tinyvm-viz/src/pages/Playground.tsx`
- Modify: `tinyvm-viz/tests/unit/components/Playground.test.tsx` (append)

- [ ] **Step 1: Append failing tests**

Append to `tinyvm-viz/tests/unit/components/Playground.test.tsx`:

```tsx
import { fireEvent } from "@testing-library/react";

describe("Playground: keyboard shortcuts", () => {
  it("ArrowRight advances stepIdx when no input is focused", () => {
    render(<Playground />);
    const before = screen.getByTestId("reg-0-value").textContent;
    fireEvent.keyDown(document, { key: "ArrowRight" });
    // After advancing past LOAD R0 5, the PRINT step still shows R0=5,
    // but the stepper text in StepControls updates. Check the scrubber value.
    expect(before).toBe("5");
    expect(screen.getByTestId("scrubber")).toHaveValue("1");
  });

  it("ArrowLeft retreats stepIdx", () => {
    render(<Playground />);
    fireEvent.keyDown(document, { key: "ArrowRight" });
    fireEvent.keyDown(document, { key: "ArrowRight" });
    expect(screen.getByTestId("scrubber")).toHaveValue("2");
    fireEvent.keyDown(document, { key: "ArrowLeft" });
    expect(screen.getByTestId("scrubber")).toHaveValue("1");
  });

  it("r resets stepIdx to 0", () => {
    render(<Playground />);
    fireEvent.keyDown(document, { key: "ArrowRight" });
    fireEvent.keyDown(document, { key: "ArrowRight" });
    expect(screen.getByTestId("scrubber")).toHaveValue("2");
    fireEvent.keyDown(document, { key: "r" });
    expect(screen.getByTestId("scrubber")).toHaveValue("0");
  });

  it("Cmd+R does not reset (browser refresh shortcut)", () => {
    render(<Playground />);
    fireEvent.keyDown(document, { key: "ArrowRight" });
    expect(screen.getByTestId("scrubber")).toHaveValue("1");
    fireEvent.keyDown(document, { key: "r", metaKey: true });
    expect(screen.getByTestId("scrubber")).toHaveValue("1");
  });

  it("ignores keys when an input has focus", () => {
    render(<Playground />);
    fireEvent.keyDown(document, { key: "ArrowRight" });
    expect(screen.getByTestId("scrubber")).toHaveValue("1");
    // Simulate input focus.
    const input = document.createElement("input");
    document.body.appendChild(input);
    input.focus();
    fireEvent.keyDown(document, { key: "ArrowRight" });
    expect(screen.getByTestId("scrubber")).toHaveValue("1");
    input.remove();
  });
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd /Users/sidgraph/FANC/tinyvm-viz && npx vitest run tests/unit/components/Playground.test.tsx`
Expected: 5 new failures (keyboard handler not wired).

- [ ] **Step 3: Add the keyboard handler to Playground**

In `tinyvm-viz/src/pages/Playground.tsx`, add a new `useEffect` (place it after the existing run-loop effect):

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

- [ ] **Step 4: Run tests and confirm pass**

Run: `cd /Users/sidgraph/FANC/tinyvm-viz && npm test`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
cd /Users/sidgraph/FANC
git add tinyvm-viz/src/pages/Playground.tsx tinyvm-viz/tests/unit/components/Playground.test.tsx
git commit -m "feat(viz): Playground keyboard shortcuts (←/→/space/r)"
```

---

## Phase D — Bundle types & fault-bundle handling

### Task 6: Extend `BundleMeta` with `interpreterError`

**Files:**
- Modify: `tinyvm-viz/src/core/types.ts`
- Modify: `tinyvm-viz/tests/unit/core/types.test.ts` (append)

- [ ] **Step 1: Append a failing test**

Append to `tinyvm-viz/tests/unit/core/types.test.ts`:

```ts
describe("BundleMeta.interpreterError", () => {
  it("accepts a bundle whose meta carries interpreterError (fault bundles)", () => {
    const step: SerializedStep = { pc: 0, regs: [0,0,0,0,0,0,0,0], stack: [], emitted: null };
    const trace: SerializedTrace = { steps: [step], output: [], halted: false };
    const bundle: ComparisonBundle = {
      schema: "tinyvm-viz/comparison/v1",
      meta: { generator: "manual", seed: 0, interpreterError: "stack underflow at step 2" },
      source: "POP R0\n",
      groundTruth: { trace },
      prediction: { output: [] },
    };
    expect(bundle.meta.interpreterError).toBe("stack underflow at step 2");
  });
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd /Users/sidgraph/FANC/tinyvm-viz && npx vitest run tests/unit/core/types.test.ts`
Expected: TS error — property `interpreterError` does not exist on `BundleMeta`.

- [ ] **Step 3: Add the optional field to `BundleMeta`**

In `tinyvm-viz/src/core/types.ts`, update `BundleMeta`:

```ts
export interface BundleMeta {
  generator: string;
  seed: number;
  spec?: Record<string, unknown>;
  tier?: string;
  interpreterError?: string;
}
```

- [ ] **Step 4: Run tests and confirm pass**

Run: `cd /Users/sidgraph/FANC/tinyvm-viz && npx vitest run tests/unit/core/types.test.ts`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/sidgraph/FANC
git add tinyvm-viz/src/core/types.ts tinyvm-viz/tests/unit/core/types.test.ts
git commit -m "feat(viz): BundleMeta.interpreterError optional field"
```

---

### Task 7: Compare-page fault-bundle handling

**Files:**
- Modify: `tinyvm-viz/src/pages/Compare.tsx`
- Modify: `tinyvm-viz/tests/unit/components/Compare.test.tsx` (append)

- [ ] **Step 1: Append a failing test**

In `tinyvm-viz/tests/unit/components/Compare.test.tsx`, add at the top after the existing imports:

```tsx
const faultBundle = {
  schema: "tinyvm-viz/comparison/v1" as const,
  meta: { generator: "manual", seed: 2, interpreterError: "stack underflow at step 0" },
  source: "POP R0\n",
  groundTruth: {
    trace: {
      steps: [{ pc: 0, regs: [0,0,0,0,0,0,0,0], stack: [], emitted: null }],
      output: [],
      halted: false,
    },
  },
  prediction: { output: [] },
};
```

Add the test (inside the existing `describe("Compare", ...)` block):

```tsx
it("renders a fault-bundle (halted=false) with an amber 'interpreter halted' banner", () => {
  render(<Compare initialBundle={faultBundle as never} />);
  expect(screen.getByTestId("fault-banner")).toHaveTextContent(/stack underflow at step 0/);
  // Importantly, no 'parity drift suspected' banner.
  expect(screen.queryByTestId("parity-banner")).toBeNull();
});

it("falls back to generic 'halted before completion' when meta.interpreterError absent", () => {
  const noErrMeta = { ...faultBundle, meta: { generator: "manual", seed: 3 } };
  render(<Compare initialBundle={noErrMeta as never} />);
  expect(screen.getByTestId("fault-banner")).toHaveTextContent(/halted before completion/i);
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd /Users/sidgraph/FANC/tinyvm-viz && npx vitest run tests/unit/components/Compare.test.tsx`
Expected: 2 new failures — `fault-banner` not found.

- [ ] **Step 3: Update `reRun` memo and JSX in Compare.tsx**

Replace the `reRun` memo in `tinyvm-viz/src/pages/Compare.tsx` with:

```tsx
const reRun = useMemo(() => {
  if (!bundle) return null;
  // Fault bundles: ground truth was authored as a halted=false partial trace.
  // Don't re-run; the TS interpreter would throw and the existing parity-drift
  // path would surface the wrong message.
  if (bundle.groundTruth.trace.halted === false) {
    const { program, errors, lineToInstIdx } = parse(bundle.source);
    if (!program || errors.length) return { ok: false as const, message: "bundle.source did not parse", lineToInstIdx };
    return { ok: true as const, program, tsTrace: bundle.groundTruth.trace, lineToInstIdx, faulted: true as const };
  }
  const { program, errors, lineToInstIdx } = parse(bundle.source);
  if (!program || errors.length) return { ok: false as const, message: "bundle.source did not parse", lineToInstIdx };
  try {
    const trace = serializeTrace(run(program));
    const same = JSON.stringify(trace.output) === JSON.stringify(bundle.groundTruth.trace.output);
    return { ok: same, program, tsTrace: trace, lineToInstIdx, faulted: false as const };
  } catch (e) {
    return { ok: false as const, message: (e as Error).message, lineToInstIdx };
  }
}, [bundle]);
```

Update the banner-rendering JSX. Replace the existing parity-banner block with:

```tsx
      {reRun && "faulted" in reRun && reRun.faulted && (
        <div data-testid="fault-banner" className="text-sm bg-amber-100 text-amber-900 p-2 rounded">
          interpreter halted with: {bundle.meta.interpreterError ?? "halted before completion"}
        </div>
      )}
      {reRun && !reRun.ok && !("faulted" in reRun && reRun.faulted) && (
        <div data-testid="parity-banner" className="text-sm bg-red-100 text-red-800 p-2 rounded">
          parity drift suspected — bundle ground truth disagrees with TS re-run
        </div>
      )}
```

- [ ] **Step 4: Run tests and confirm pass**

Run: `cd /Users/sidgraph/FANC/tinyvm-viz && npx vitest run tests/unit/components/Compare.test.tsx`
Expected: all green; existing parity-drift test still passes, new fault tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/sidgraph/FANC
git add tinyvm-viz/src/pages/Compare.tsx tinyvm-viz/tests/unit/components/Compare.test.tsx
git commit -m "feat(viz): Compare renders fault bundles with amber banner"
```

---

## Phase E — Samples dropdown + new sample bundles

### Task 8: Samples dropdown in Compare

**Files:**
- Modify: `tinyvm-viz/src/pages/Compare.tsx`
- Modify: `tinyvm-viz/tests/unit/components/Compare.test.tsx` (append)

- [ ] **Step 1: Append a failing test**

Append to `tinyvm-viz/tests/unit/components/Compare.test.tsx`:

```tsx
it("renders a samples dropdown listing every samples/*.json", () => {
  render(<Compare />);
  const select = screen.getByTestId("samples-select") as HTMLSelectElement;
  // At least the two existing samples must be options.
  const filenames = Array.from(select.options).map((o) => o.value);
  expect(filenames).toContain("example_pass.json");
  expect(filenames).toContain("example_divergence.json");
});

it("selecting a sample loads that bundle", () => {
  render(<Compare />);
  const select = screen.getByTestId("samples-select") as HTMLSelectElement;
  fireEvent.change(select, { target: { value: "example_divergence.json" } });
  expect(screen.getByTestId("div-summary")).toHaveTextContent(/first divergence at #0/i);
});
```

(Note: `fireEvent` is already imported in this file via the existing tests.)

- [ ] **Step 2: Run and confirm failure**

Run: `cd /Users/sidgraph/FANC/tinyvm-viz && npx vitest run tests/unit/components/Compare.test.tsx`
Expected: 2 new failures.

- [ ] **Step 3: Add the dropdown to Compare.tsx**

At the top of `tinyvm-viz/src/pages/Compare.tsx`, after the imports, add:

```tsx
const sampleModules = import.meta.glob<{ default: ComparisonBundle }>(
  "/samples/*.json",
  { eager: true, import: "default" },
);
const samples = Object.entries(sampleModules)
  .map(([path, bundle]) => ({ filename: path.split("/").pop()!, bundle }))
  .sort((a, b) => a.filename.localeCompare(b.filename));
```

In the "no bundle loaded" branch of `Compare()`, replace the file-input block:

```tsx
  if (!bundle) {
    return (
      <div className="p-4 space-y-3">
        <h2 className="text-lg font-semibold">Comparison view</h2>
        <div className="flex items-center gap-3">
          <label className="text-sm">Load a sample:</label>
          <select
            data-testid="samples-select"
            className="border border-slate-200 rounded px-2 py-1 text-sm"
            defaultValue=""
            onChange={(e) => {
              const choice = samples.find((s) => s.filename === e.target.value);
              if (choice) { setBundle(choice.bundle); setStepIdx(0); }
            }}
          >
            <option value="" disabled>Choose a sample…</option>
            {samples.map((s) => (
              <option key={s.filename} value={s.filename}>{s.filename}</option>
            ))}
          </select>
          <span className="text-xs text-slate-500">or drop a file:</span>
          <input
            type="file"
            accept="application/json"
            onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0]!)}
          />
        </div>
        {loadError && <div className="text-red-600 text-sm">{loadError}</div>}
      </div>
    );
  }
```

- [ ] **Step 4: Build check**

Run: `cd /Users/sidgraph/FANC/tinyvm-viz && npm run build`
Expected: clean. Vite resolves `/samples/*.json` against the project root.

- [ ] **Step 5: Run tests and confirm pass**

Run: `cd /Users/sidgraph/FANC/tinyvm-viz && npx vitest run tests/unit/components/Compare.test.tsx`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
cd /Users/sidgraph/FANC
git add tinyvm-viz/src/pages/Compare.tsx tinyvm-viz/tests/unit/components/Compare.test.tsx
git commit -m "feat(viz): Compare samples dropdown via import.meta.glob"
```

---

### Task 9: Hand-author `stack_pop_underflow.json`

**Files:**
- Create: `tinyvm-viz/samples/stack_pop_underflow.json`

- [ ] **Step 1: Author the bundle**

Create `tinyvm-viz/samples/stack_pop_underflow.json`:

```json
{
  "schema": "tinyvm-viz/comparison/v1",
  "meta": {
    "generator": "manual",
    "seed": 2,
    "interpreterError": "stack underflow at step 0"
  },
  "source": "POP R0\nHALT\n",
  "groundTruth": {
    "trace": {
      "steps": [
        { "pc": 0, "regs": [0, 0, 0, 0, 0, 0, 0, 0], "stack": [], "emitted": null }
      ],
      "output": [],
      "halted": false
    }
  },
  "prediction": { "output": [] }
}
```

- [ ] **Step 2: Verify the bundle loads without crashing**

Run: `cd /Users/sidgraph/FANC/tinyvm-viz && npm test`
Expected: all green. The samples-dropdown test from Task 8 now picks up `stack_pop_underflow.json` automatically; the existing tests still pass.

- [ ] **Step 3: Commit**

```bash
cd /Users/sidgraph/FANC
git add tinyvm-viz/samples/stack_pop_underflow.json
git commit -m "feat(viz): stack_pop_underflow.json fault sample bundle"
```

---

### Task 10: Generate `branched_pass.json` and `branched_divergence.json`

**Files:**
- Create: `tinyvm-viz/samples/branched_pass.json`
- Create: `tinyvm-viz/samples/branched_divergence.json`

- [ ] **Step 1: Generate `branched_pass.json` via the Python helper**

The pass bundle uses the ground-truth output as the prediction (same array → no divergence). Run:

```bash
cd /Users/sidgraph/FANC && python -c "
from pathlib import Path
import random
from tinyvm.scripts.export_comparison_bundle import build_bundle, write_bundle
from tinyvm.generators import GenSpec, gen_branched
from tinyvm.interpreter import run as run_p

# Build the program ourselves so we know the ground truth output for the prediction.
rng = random.Random(0)
spec = GenSpec(n=24, k=4, b=1, l=0)
p = gen_branched(spec=spec, rng=rng)
gt = run_p(p)
prediction_output = list(gt.output)

bundle = build_bundle(
    generator='gen_branched', seed=0,
    generator_kwargs={'n': 24, 'k': 4, 'b': 1, 'l': 0},
    prediction_output=prediction_output,
)
Path('tinyvm-viz/samples/branched_pass.json').write_text(__import__('json').dumps(bundle, indent=2, sort_keys=True))
print('wrote tinyvm-viz/samples/branched_pass.json with prediction_output =', prediction_output)
"
```

- [ ] **Step 2: Generate `branched_divergence.json`**

Same seed/spec, but perturb the prediction so the divergence panel has something to highlight:

```bash
cd /Users/sidgraph/FANC && python -c "
from pathlib import Path
import random, json
from tinyvm.scripts.export_comparison_bundle import build_bundle
from tinyvm.generators import GenSpec, gen_branched
from tinyvm.interpreter import run as run_p

rng = random.Random(0)
spec = GenSpec(n=24, k=4, b=1, l=0)
p = gen_branched(spec=spec, rng=rng)
gt = run_p(p)
prediction_output = list(gt.output)
# Perturb the LAST PRINT value if any, else inject a wrong PRINT.
if prediction_output:
    prediction_output[-1] = (prediction_output[-1] + 1) % 1024
else:
    prediction_output = [999]

bundle = build_bundle(
    generator='gen_branched', seed=0,
    generator_kwargs={'n': 24, 'k': 4, 'b': 1, 'l': 0},
    prediction_output=prediction_output,
)
Path('tinyvm-viz/samples/branched_divergence.json').write_text(json.dumps(bundle, indent=2, sort_keys=True))
print('wrote tinyvm-viz/samples/branched_divergence.json with prediction_output =', prediction_output)
"
```

- [ ] **Step 3: Verify both files load correctly**

Run: `cd /Users/sidgraph/FANC/tinyvm-viz && npm test`
Expected: all green.

- [ ] **Step 4: Commit**

```bash
cd /Users/sidgraph/FANC
git add tinyvm-viz/samples/branched_pass.json tinyvm-viz/samples/branched_divergence.json
git commit -m "feat(viz): branched_pass and branched_divergence sample bundles"
```

---

### Task 11: Sample sweep test

**Files:**
- Create: `tinyvm-viz/tests/unit/samples.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest";
import { parse } from "@/core/parser";
import { run } from "@/core/interpreter";
import { validateBundle } from "@/pages/Compare";

const bundleModules = import.meta.glob<{ default: unknown }>(
  "/samples/*.json",
  { eager: true, import: "default" },
);

describe("samples/*.json", () => {
  it("at least one sample exists", () => {
    expect(Object.keys(bundleModules).length).toBeGreaterThan(0);
  });

  for (const [path, raw] of Object.entries(bundleModules)) {
    const filename = path.split("/").pop()!;
    it(`${filename} passes validateBundle`, () => {
      expect(validateBundle(raw)).toBe(true);
    });

    it(`${filename} parses and (if non-fault) matches its groundTruth output`, () => {
      const b = raw as { source: string; groundTruth: { trace: { output: number[]; halted: boolean } } };
      const { program, errors } = parse(b.source);
      expect(errors, `parse errors in ${filename}`).toEqual([]);
      if (b.groundTruth.trace.halted) {
        const trace = run(program!);
        expect(trace.output, `output mismatch in ${filename}`).toEqual(b.groundTruth.trace.output);
      }
    });
  }
});
```

- [ ] **Step 2: Run and confirm pass**

Run: `cd /Users/sidgraph/FANC/tinyvm-viz && npx vitest run tests/unit/samples.test.ts`
Expected: 11 tests pass (1 existence + 5 bundles × 2 assertions, depending on how many `samples/*.json` exist at this point).

- [ ] **Step 3: Commit**

```bash
cd /Users/sidgraph/FANC
git add tinyvm-viz/tests/unit/samples.test.ts
git commit -m "test(viz): sweep validates every samples/*.json bundle"
```

---

## Phase F — Parity fixture expansion

### Task 12: Expand `export_golden_fixtures.py` and add bucket-coverage test

**Files:**
- Modify: `tinyvm/scripts/export_golden_fixtures.py`
- Modify: `tinyvm/tests/test_export_golden_fixtures.py`

- [ ] **Step 1: Expand the sweep tables in `export_golden_fixtures.py`**

Replace the three sweep constants in `tinyvm/scripts/export_golden_fixtures.py`:

```python
COUNTER_SEEDS: list[tuple[int, int]] = [
    (0, 4), (1, 8), (2, 4), (3, 6),
    (4, 12), (5, 16), (6, 24), (7, 8),
]

REGISTER_TRACE_SPECS: list[tuple[int, int, int]] = [  # (seed, n, k)
    (0, 8, 2), (1, 16, 4), (2, 32, 4), (3, 16, 8),
    (4, 48, 4), (5, 48, 6), (6, 64, 8),
    (7, 16, 2), (8, 24, 6), (9, 32, 8),
    (10, 48, 8), (11, 64, 4),
]

BRANCHED_SPECS: list[tuple[int, GenSpec]] = [
    # Existing four
    (0, GenSpec(n=24, k=4, b=1, l=0)),
    (1, GenSpec(n=32, k=4, b=2, l=4)),
    (2, GenSpec(n=48, k=6, b=2, l=8)),
    (3, GenSpec(n=48, k=6, b=0, l=0, use_stack=True, stack_frames=2)),
    # branches + loops (no stack)
    (4, GenSpec(n=48, k=4, b=2, l=4)),
    (5, GenSpec(n=64, k=6, b=4, l=8)),
    (6, GenSpec(n=96, k=6, b=4, l=12)),
    (7, GenSpec(n=128, k=8, b=8, l=16)),
    # branches + stack (no loops)
    (8, GenSpec(n=32, k=4, b=1, l=0, use_stack=True, stack_frames=1)),
    (9, GenSpec(n=48, k=6, b=2, l=0, use_stack=True, stack_frames=2)),
    (10, GenSpec(n=64, k=6, b=4, l=0, use_stack=True, stack_frames=2)),
    (11, GenSpec(n=64, k=8, b=2, l=0, use_stack=True, stack_frames=3)),
    # loops + stack (no branches)
    (12, GenSpec(n=48, k=4, b=0, l=4, use_stack=True, stack_frames=1)),
    (13, GenSpec(n=64, k=6, b=0, l=8, use_stack=True, stack_frames=2)),
    (14, GenSpec(n=96, k=8, b=0, l=12, use_stack=True, stack_frames=2)),
    # branches + loops + stack (the gap)
    (15, GenSpec(n=64, k=6, b=2, l=4, use_stack=True, stack_frames=1)),
    (16, GenSpec(n=96, k=6, b=2, l=8, use_stack=True, stack_frames=2)),
    (17, GenSpec(n=128, k=8, b=4, l=8, use_stack=True, stack_frames=2)),
    (18, GenSpec(n=128, k=8, b=4, l=12, use_stack=True, stack_frames=3)),
    # additional shape coverage
    (19, GenSpec(n=24, k=4, b=3, l=2)),
    (20, GenSpec(n=24, k=4, b=0, l=6)),
    (21, GenSpec(n=32, k=4, b=0, l=8)),
    (22, GenSpec(n=48, k=6, b=1, l=2)),
    (23, GenSpec(n=64, k=8, b=2, l=6)),
    (24, GenSpec(n=80, k=8, b=4, l=4)),
    (25, GenSpec(n=80, k=8, b=2, l=12)),
    (26, GenSpec(n=96, k=6, b=4, l=6)),
    (27, GenSpec(n=64, k=6, b=1, l=16)),
    (28, GenSpec(n=48, k=4, b=4, l=2)),
    (29, GenSpec(n=64, k=4, b=2, l=4, use_stack=True, stack_frames=1)),
]
```

This gives 8 counter + 12 register-trace + 30 branched = 50 fixtures.

- [ ] **Step 2: Add the bucket-coverage Python test**

Append to `tinyvm/tests/test_export_golden_fixtures.py`:

```python
def test_branched_sweep_covers_combinations():
    by_bucket = {"sb": 0, "sl": 0, "bl": 0, "sbl": 0}
    for f in build_fixtures():
        if f["generator"] != "gen_branched":
            continue
        s = f["spec"]
        if s["use_stack"] and s["b"] > 0:
            by_bucket["sb"] += 1
        if s["use_stack"] and s["l"] > 0:
            by_bucket["sl"] += 1
        if s["b"] > 0 and s["l"] > 0:
            by_bucket["bl"] += 1
        if s["use_stack"] and s["b"] > 0 and s["l"] > 0:
            by_bucket["sbl"] += 1
    for bucket, n in by_bucket.items():
        assert n >= 1, f"no gen_branched fixture in bucket {bucket}"


def test_total_fixture_count_at_least_fifty():
    fixtures = build_fixtures()
    assert len(fixtures) >= 50, f"expected ~50 fixtures, got {len(fixtures)}"
```

- [ ] **Step 3: Run the Python tests**

Run: `cd /Users/sidgraph/FANC && python -m pytest tinyvm/tests/test_export_golden_fixtures.py -v`
Expected: all green, including the two new tests.

- [ ] **Step 4: Commit**

```bash
cd /Users/sidgraph/FANC
git add tinyvm/scripts/export_golden_fixtures.py tinyvm/tests/test_export_golden_fixtures.py
git commit -m "feat(viz): expand parity-fixture sweep to ~50 with stack+branch+loop coverage"
```

---

### Task 13: Regenerate `golden.json` and run TS parity suite

**Files:**
- Modify: `tinyvm-viz/tests/fixtures/golden.json`

- [ ] **Step 1: Regenerate**

Run: `cd /Users/sidgraph/FANC && python -m tinyvm.scripts.export_golden_fixtures`
Expected: prints `wrote /Users/sidgraph/FANC/tinyvm-viz/tests/fixtures/golden.json`. The file grows from ~9k lines to ~30-40k lines.

- [ ] **Step 2: Run TS parity tests**

Run: `cd /Users/sidgraph/FANC/tinyvm-viz && npx vitest run tests/parity`
Expected: 50 tests pass. If any fail, it indicates a TS-vs-Python interpreter divergence on the new spec — DO NOT alter the fixture; fix the TS side (parser/interpreter) so it matches Python.

- [ ] **Step 3: Run the full suite**

Run: `cd /Users/sidgraph/FANC/tinyvm-viz && npm test`
Expected: total green count jumps by ~38 parity tests.

- [ ] **Step 4: Commit**

```bash
cd /Users/sidgraph/FANC
git add tinyvm-viz/tests/fixtures/golden.json
git commit -m "feat(viz): regenerate golden.json with expanded fixture sweep"
```

---

## Phase G — CI workflow

### Task 14: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create the workflow file**

Create `.github/workflows/ci.yml`:

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
        with:
          python-version: "3.11"
      - name: Install package
        run: pip install -e .
      - name: Run pytest
        run: python -m pytest tinyvm/ -v

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
      - name: Install dependencies
        run: npm ci
      - name: Run vitest
        run: npm test
      - name: Build
        run: npm run build

  golden-fixture-staleness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install package
        run: pip install -e .
      - name: Regenerate golden.json
        run: python -m tinyvm.scripts.export_golden_fixtures
      - name: Verify golden.json is up-to-date
        run: git diff --exit-code tinyvm-viz/tests/fixtures/golden.json
```

- [ ] **Step 2: Validate YAML locally**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" && echo OK`
Expected: prints `OK` (no parse error).

- [ ] **Step 3: Commit**

```bash
cd /Users/sidgraph/FANC
git add .github/workflows/ci.yml
git commit -m "ci: GitHub Actions workflow with golden-fixture staleness check"
```

- [ ] **Step 4: Final whole-suite verification**

Run: `cd /Users/sidgraph/FANC/tinyvm-viz && npm test && npm run build`
Expected: TS suite green (≈ 104-110 tests), build clean.

Run: `cd /Users/sidgraph/FANC && python -m pytest tinyvm/ -v 2>&1 | tail -3`
Expected: ≈ 131 Python tests pass.

---

## Self-review notes

- **Spec coverage:** §5 highlighting → Tasks 1-2; §6 samples dropdown → Task 8; §7 sample bundles → Tasks 9-11; §8 fixture expansion → Tasks 12-13; §9 CI → Task 14; §10 keyboard shortcuts → Task 5; §11 ProgramView alignment → Tasks 3-4; §12 testing → tests live alongside each task.
- **Cross-cutting:** the `BundleMeta.interpreterError` schema extension (Task 6) is required by Task 7 (fault banner) but stays backward-compatible.
- **Type consistency:** `lineToInstIdx` shape (`readonly (number | null)[]`) is identical across parser export (Task 3), ProgramView prop (Task 4), and Compare/Playground threading (Task 4).
- **Test ID consistency:** new `data-testid`s used: `samples-select`, `fault-banner`. Existing tests use `parity-banner`, `div-summary`, `div-row-N`, `pgm-line-N`, `reg-N-value`, `scrubber`.
- **Out of scope reminder:** No custom CodeMirror theme colours, no Tier 4 userop support, no GH Pages deploy step. Each was named in spec §2.
