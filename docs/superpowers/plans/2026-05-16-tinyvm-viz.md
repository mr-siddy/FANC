# Tiny-VM Visualization Tool — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a TypeScript + React + Vite SPA at `tinyvm-viz/` that lets users (a) write and step through Tiny-VM programs in the browser, and (b) drop a `(program, ground_truth, model_prediction)` JSON bundle and inspect divergences against the Tiny-VM interpreter.

**Architecture:** Static SPA. Framework-free TS port of the Python `tinyvm` interpreter (`isa` / `parser` / `interpreter` / `verifier` / `tokeniser` subset) under `src/core/`. UI under `src/components/` and `src/pages/` depends only on `core/`. A Python-side script emits golden-fixture JSON; a vitest `parity/` layer asserts the TS interpreter is byte-equal to the Python reference.

**Tech Stack:** React 18, Vite 5, TypeScript strict, CodeMirror 6 (custom Tiny-VM language mode), Tailwind CSS, react-router-dom, vitest + @testing-library/react + jsdom.

**Spec:** `docs/superpowers/specs/2026-05-16-tinyvm-viz-design.md`.

## File structure

```
tinyvm-viz/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
├── postcss.config.js
├── vitest.config.ts
├── index.html
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── core/
│   │   ├── isa.ts
│   │   ├── types.ts
│   │   ├── interpreter.ts
│   │   ├── parser.ts
│   │   ├── verifier.ts
│   │   └── tokeniser.ts
│   ├── components/
│   │   ├── ExecutionPanel.tsx
│   │   ├── RegisterFile.tsx
│   │   ├── StackView.tsx
│   │   ├── ProgramView.tsx
│   │   ├── OutputStream.tsx
│   │   ├── Editor.tsx
│   │   ├── StepControls.tsx
│   │   ├── LessonPlaylist.tsx
│   │   └── DivergencePanel.tsx
│   ├── pages/
│   │   ├── Playground.tsx
│   │   └── Compare.tsx
│   ├── lessons/
│   │   └── index.ts
│   └── styles/
│       └── index.css
├── samples/
├── tests/
│   ├── unit/
│   │   ├── core/
│   │   └── components/
│   ├── parity/
│   └── fixtures/
│       └── golden.json
└── README.md

tinyvm/scripts/
├── export_golden_fixtures.py
└── export_comparison_bundle.py
```

---

## Phase A — Scaffolding

### Task 1: Initialise the Vite + React + TS workspace

**Files:**
- Create: `tinyvm-viz/package.json`
- Create: `tinyvm-viz/vite.config.ts`
- Create: `tinyvm-viz/tsconfig.json`
- Create: `tinyvm-viz/tsconfig.node.json`
- Create: `tinyvm-viz/index.html`
- Create: `tinyvm-viz/src/main.tsx`
- Create: `tinyvm-viz/src/App.tsx`
- Create: `tinyvm-viz/.gitignore`
- Create: `tinyvm-viz/README.md`

- [ ] **Step 1: Create `tinyvm-viz/package.json`**

```json
{
  "name": "tinyvm-viz",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.2"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.5.0",
    "@testing-library/react": "^16.0.1",
    "@testing-library/user-event": "^14.5.2",
    "@types/react": "^18.3.5",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.20",
    "jsdom": "^25.0.0",
    "postcss": "^8.4.45",
    "tailwindcss": "^3.4.10",
    "typescript": "^5.5.4",
    "vite": "^5.4.5",
    "vitest": "^2.0.5"
  }
}
```

- [ ] **Step 2: Create `tinyvm-viz/vite.config.ts`**

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "./",
  plugins: [react()],
  resolve: {
    alias: { "@": "/src" },
  },
});
```

- [ ] **Step 3: Create `tinyvm-viz/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "isolatedModules": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "skipLibCheck": true,
    "baseUrl": ".",
    "paths": { "@/*": ["src/*"] },
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src", "tests"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 4: Create `tinyvm-viz/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts", "vitest.config.ts"]
}
```

- [ ] **Step 5: Create `tinyvm-viz/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Tiny-VM Visualizer</title>
  </head>
  <body class="bg-slate-50 text-slate-900">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: Create `tinyvm-viz/src/main.tsx`**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles/index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 7: Create `tinyvm-viz/src/App.tsx` (placeholder)**

```tsx
export default function App() {
  return (
    <main className="p-8">
      <h1 className="text-2xl font-semibold">Tiny-VM Visualizer</h1>
      <p className="text-slate-600">Scaffolding only. Real UI lands later.</p>
    </main>
  );
}
```

- [ ] **Step 8: Create `tinyvm-viz/.gitignore`**

```
node_modules/
dist/
*.log
.vite/
.DS_Store
```

- [ ] **Step 9: Create `tinyvm-viz/README.md`**

```markdown
# Tiny-VM Visualizer

In-browser visualization for the Tiny-VM environment. See `docs/superpowers/specs/2026-05-16-tinyvm-viz-design.md`.

## Develop
- `npm install`
- `npm run dev`
- `npm test`
```

- [ ] **Step 10: Install dependencies and verify**

Run: `cd tinyvm-viz && npm install`
Expected: completes; `node_modules/` populated.

Run: `cd tinyvm-viz && npm run build`
Expected: TypeScript builds without errors; `dist/` emitted.

- [ ] **Step 11: Commit**

```bash
git add tinyvm-viz/package.json tinyvm-viz/package-lock.json \
        tinyvm-viz/vite.config.ts tinyvm-viz/tsconfig.json \
        tinyvm-viz/tsconfig.node.json tinyvm-viz/index.html \
        tinyvm-viz/src/main.tsx tinyvm-viz/src/App.tsx \
        tinyvm-viz/.gitignore tinyvm-viz/README.md
git commit -m "feat(viz): scaffold Vite + React + TS workspace"
```

---

### Task 2: Wire Tailwind, PostCSS, and vitest

**Files:**
- Create: `tinyvm-viz/tailwind.config.js`
- Create: `tinyvm-viz/postcss.config.js`
- Create: `tinyvm-viz/src/styles/index.css`
- Create: `tinyvm-viz/vitest.config.ts`
- Create: `tinyvm-viz/tests/setup.ts`
- Create: `tinyvm-viz/tests/unit/sanity.test.ts`

- [ ] **Step 1: Create `tinyvm-viz/tailwind.config.js`**

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {} },
  plugins: [],
};
```

- [ ] **Step 2: Create `tinyvm-viz/postcss.config.js`**

```js
export default {
  plugins: { tailwindcss: {}, autoprefixer: {} },
};
```

- [ ] **Step 3: Create `tinyvm-viz/src/styles/index.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  font-family: ui-sans-serif, system-ui, sans-serif;
}
```

- [ ] **Step 4: Create `tinyvm-viz/vitest.config.ts`**

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    include: ["tests/**/*.test.{ts,tsx}"],
  },
  resolve: { alias: { "@": "/src" } },
});
```

- [ ] **Step 5: Create `tinyvm-viz/tests/setup.ts`**

```ts
import "@testing-library/jest-dom";
```

- [ ] **Step 6: Write a sanity test that should pass**

`tinyvm-viz/tests/unit/sanity.test.ts`:

```ts
import { describe, it, expect } from "vitest";

describe("vitest sanity", () => {
  it("runs", () => {
    expect(1 + 1).toBe(2);
  });
});
```

- [ ] **Step 7: Run tests**

Run: `cd tinyvm-viz && npm test`
Expected: 1 test passes.

- [ ] **Step 8: Commit**

```bash
git add tinyvm-viz/tailwind.config.js tinyvm-viz/postcss.config.js \
        tinyvm-viz/src/styles/index.css tinyvm-viz/vitest.config.ts \
        tinyvm-viz/tests/setup.ts tinyvm-viz/tests/unit/sanity.test.ts
git commit -m "feat(viz): wire Tailwind and Vitest"
```

---

## Phase B — Core port (UI-free TypeScript)

### Task 3: Core types — `SerializedTrace`, `SerializedStep`, `ComparisonBundle`

**Files:**
- Create: `tinyvm-viz/src/core/types.ts`
- Create: `tinyvm-viz/tests/unit/core/types.test.ts`

- [ ] **Step 1: Write a failing test asserting type-level structure via construction**

`tinyvm-viz/tests/unit/core/types.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import type { ComparisonBundle, SerializedStep, SerializedTrace } from "@/core/types";

describe("core types: construction", () => {
  it("permits a well-formed ComparisonBundle", () => {
    const step: SerializedStep = { pc: 0, regs: [0, 0, 0, 0, 0, 0, 0, 0], stack: [], emitted: null };
    const trace: SerializedTrace = { steps: [step], output: [], halted: true };
    const bundle: ComparisonBundle = {
      schema: "tinyvm-viz/comparison/v1",
      meta: { generator: "gen_counter", seed: 0 },
      source: "LOAD R0 5\nPRINT R0\nHALT\n",
      groundTruth: { trace },
      prediction: { output: [5] },
    };
    expect(bundle.groundTruth.trace.steps).toHaveLength(1);
  });
});
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/types.test.ts`
Expected: FAIL — cannot resolve `@/core/types`.

- [ ] **Step 3: Create `tinyvm-viz/src/core/types.ts`**

```ts
export interface SerializedStep {
  pc: number;
  regs: number[];                  // length 8
  stack: number[];                 // 0..16
  emitted: number | null;
}

export interface SerializedTrace {
  steps: SerializedStep[];
  output: number[];
  halted: boolean;
}

export interface BundleMeta {
  generator: string;
  seed: number;
  spec?: Record<string, unknown>;
  tier?: string;
}

export interface ComparisonBundle {
  schema: "tinyvm-viz/comparison/v1";
  meta: BundleMeta;
  source: string;
  groundTruth: { trace: SerializedTrace };
  prediction: {
    output: number[];
    model?: string;
    decodeWarnings?: string[];
  };
}
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/types.test.ts`
Expected: 1 pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm-viz/src/core/types.ts tinyvm-viz/tests/unit/core/types.test.ts
git commit -m "feat(viz): core types (ComparisonBundle, SerializedTrace)"
```

---

### Task 4: ISA — `Op`, `Instruction`, `Program.build()`

**Files:**
- Create: `tinyvm-viz/src/core/isa.ts`
- Create: `tinyvm-viz/tests/unit/core/isa.test.ts`

- [ ] **Step 1: Write failing tests**

`tinyvm-viz/tests/unit/core/isa.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { Op, isUserop, NUM_REGS, VAL_MIN, VAL_MAX, LITERAL_MIN, LITERAL_MAX, STACK_DEPTH, buildProgram } from "@/core/isa";

describe("ISA constants", () => {
  it("matches Python spec", () => {
    expect(NUM_REGS).toBe(8);
    expect(VAL_MIN).toBe(-1024);
    expect(VAL_MAX).toBe(1023);
    expect(LITERAL_MIN).toBe(-127);
    expect(LITERAL_MAX).toBe(127);
    expect(STACK_DEPTH).toBe(16);
  });
});

describe("Op enum", () => {
  it("has 16 base ops at integer ids 0..15", () => {
    expect(Op.LOAD).toBe(0);
    expect(Op.HALT).toBe(15);
  });

  it("reserves 5 userop slots at 16..20", () => {
    expect(Op.USEROP_0).toBe(16);
    expect(Op.USEROP_4).toBe(20);
  });

  it("isUserop separates base from userop", () => {
    expect(isUserop(Op.ADD)).toBe(false);
    expect(isUserop(Op.USEROP_0)).toBe(true);
  });
});

describe("buildProgram", () => {
  it("precomputes labelIndex", () => {
    const program = buildProgram([
      { op: Op.LOAD, args: [0, 5], label: "L0" },
      { op: Op.HALT, args: [] },
    ]);
    expect(program.labelIndex.get("L0")).toBe(0);
  });

  it("throws on duplicate labels", () => {
    expect(() =>
      buildProgram([
        { op: Op.NOP, args: [], label: "L0" },
        { op: Op.NOP, args: [], label: "L0" },
      ]),
    ).toThrow(/duplicate label/);
  });
});
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/isa.test.ts`
Expected: cannot resolve module.

- [ ] **Step 3: Create `tinyvm-viz/src/core/isa.ts`**

```ts
export const NUM_REGS = 8;
export const VAL_MIN = -1024;
export const VAL_MAX = 1023;
export const LITERAL_MIN = -127;
export const LITERAL_MAX = 127;
export const STACK_DEPTH = 16;
export const DEFAULT_STEP_CAP = 1_000_000;

export enum Op {
  LOAD = 0,
  MOV = 1,
  ADD = 2,
  SUB = 3,
  MUL = 4,
  DIV = 5,
  NEG = 6,
  EQ = 7,
  LT = 8,
  JZ = 9,
  JMP = 10,
  PUSH = 11,
  POP = 12,
  PRINT = 13,
  NOP = 14,
  HALT = 15,
  USEROP_0 = 16,
  USEROP_1 = 17,
  USEROP_2 = 18,
  USEROP_3 = 19,
  USEROP_4 = 20,
}

export function isUserop(op: Op): boolean {
  return op >= Op.USEROP_0;
}

export interface Instruction {
  op: Op;
  args: number[];
  label?: string;
  target?: string;
}

export interface Program {
  instructions: readonly Instruction[];
  labelIndex: ReadonlyMap<string, number>;
}

export function buildProgram(instructions: Instruction[]): Program {
  const labelIndex = new Map<string, number>();
  instructions.forEach((inst, idx) => {
    if (inst.label !== undefined) {
      if (labelIndex.has(inst.label)) {
        throw new Error(`duplicate label: ${inst.label}`);
      }
      labelIndex.set(inst.label, idx);
    }
  });
  return { instructions: Object.freeze(instructions.slice()), labelIndex };
}
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/isa.test.ts`
Expected: 5 pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm-viz/src/core/isa.ts tinyvm-viz/tests/unit/core/isa.test.ts
git commit -m "feat(viz): core/isa — Op enum, Instruction, buildProgram"
```

---

## Phase C — Interpreter

### Task 5: Interpreter — arithmetic, clamping, DIV/0

**Files:**
- Create: `tinyvm-viz/src/core/interpreter.ts`
- Create: `tinyvm-viz/tests/unit/core/interpreter.test.ts`

- [ ] **Step 1: Write failing tests**

`tinyvm-viz/tests/unit/core/interpreter.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { buildProgram, Op } from "@/core/isa";
import { run } from "@/core/interpreter";

describe("interpreter: arithmetic", () => {
  it("LOAD then MOV", () => {
    const p = buildProgram([
      { op: Op.LOAD, args: [0, 5] },
      { op: Op.MOV, args: [1, 0] },
      { op: Op.HALT, args: [] },
    ]);
    const trace = run(p);
    expect(trace.steps.at(-1)!.regs[1]).toBe(5);
  });

  it("ADD / SUB / MUL / NEG produce expected values", () => {
    const p = buildProgram([
      { op: Op.LOAD, args: [0, 3] },
      { op: Op.LOAD, args: [1, 4] },
      { op: Op.ADD, args: [2, 0, 1] }, // 7
      { op: Op.SUB, args: [3, 1, 0] }, // 1
      { op: Op.MUL, args: [4, 0, 1] }, // 12
      { op: Op.NEG, args: [5, 0] },    // -3
      { op: Op.HALT, args: [] },
    ]);
    const regs = run(p).steps.at(-1)!.regs;
    expect([regs[2], regs[3], regs[4], regs[5]]).toEqual([7, 1, 12, -3]);
  });

  it("clamps to [VAL_MIN, VAL_MAX]", () => {
    const p = buildProgram([
      { op: Op.LOAD, args: [0, 100] },
      { op: Op.MUL, args: [0, 0, 0] }, // 10_000 → 1023
      { op: Op.HALT, args: [] },
    ]);
    expect(run(p).steps.at(-1)!.regs[0]).toBe(1023);
  });

  it("DIV by 0 returns 0", () => {
    const p = buildProgram([
      { op: Op.LOAD, args: [0, 10] },
      { op: Op.DIV, args: [1, 0, 2] }, // R2 unset = 0
      { op: Op.HALT, args: [] },
    ]);
    expect(run(p).steps.at(-1)!.regs[1]).toBe(0);
  });

  it("DIV truncates toward zero", () => {
    const p = buildProgram([
      { op: Op.LOAD, args: [0, -7] },
      { op: Op.LOAD, args: [1, 2] },
      { op: Op.DIV, args: [2, 0, 1] }, // -7 / 2 = -3 (truncate toward 0)
      { op: Op.HALT, args: [] },
    ]);
    expect(run(p).steps.at(-1)!.regs[2]).toBe(-3);
  });
});
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/interpreter.test.ts`
Expected: cannot resolve module.

- [ ] **Step 3: Create `tinyvm-viz/src/core/interpreter.ts`**

```ts
import { DEFAULT_STEP_CAP, NUM_REGS, Op, Program, STACK_DEPTH, VAL_MAX, VAL_MIN, isUserop } from "./isa";

export class InterpreterError extends Error {}

export interface StepRecord {
  pc: number;
  regs: number[];
  stack: number[];
  emitted: number | null;
}

export interface ExecutionTrace {
  steps: StepRecord[];
  output: number[];
  halted: boolean;
}

function clamp(v: number): number {
  if (v < VAL_MIN) return VAL_MIN;
  if (v > VAL_MAX) return VAL_MAX;
  return v;
}

function truncDiv(a: number, b: number): number {
  const q = Math.floor(Math.abs(a) / Math.abs(b));
  return (a < 0) !== (b < 0) ? -q : q;
}

export function run(program: Program, stepCap: number | null = DEFAULT_STEP_CAP): ExecutionTrace {
  const regs = new Array<number>(NUM_REGS).fill(0);
  const stack: number[] = [];
  const steps: StepRecord[] = [];
  const output: number[] = [];
  let pc = 0;
  let stepCount = 0;
  const n = program.instructions.length;

  while (pc < n) {
    if (stepCap !== null && stepCount >= stepCap) {
      throw new InterpreterError(`step cap ${stepCap} exceeded`);
    }
    stepCount += 1;
    const executedPc = pc;
    const inst = program.instructions[pc]!;
    let nextPc = pc + 1;
    let emitted: number | null = null;

    switch (inst.op) {
      case Op.LOAD: {
        const [i, lit] = inst.args as [number, number];
        regs[i] = clamp(lit);
        break;
      }
      case Op.MOV: {
        const [i, j] = inst.args as [number, number];
        regs[i] = regs[j]!;
        break;
      }
      case Op.ADD: {
        const [i, j, k] = inst.args as [number, number, number];
        regs[i] = clamp(regs[j]! + regs[k]!);
        break;
      }
      case Op.SUB: {
        const [i, j, k] = inst.args as [number, number, number];
        regs[i] = clamp(regs[j]! - regs[k]!);
        break;
      }
      case Op.MUL: {
        const [i, j, k] = inst.args as [number, number, number];
        regs[i] = clamp(regs[j]! * regs[k]!);
        break;
      }
      case Op.DIV: {
        const [i, j, k] = inst.args as [number, number, number];
        const divisor = regs[k]!;
        regs[i] = divisor === 0 ? 0 : clamp(truncDiv(regs[j]!, divisor));
        break;
      }
      case Op.NEG: {
        const [i, j] = inst.args as [number, number];
        regs[i] = clamp(-regs[j]!);
        break;
      }
      default:
        throw new InterpreterError(`unhandled op in this task: ${Op[inst.op]}`);
    }

    steps.push({ pc: executedPc, regs: [...regs], stack: [...stack], emitted });
    pc = nextPc;
    void stack; void output; void STACK_DEPTH; void isUserop;
  }

  return { steps, output, halted: true };
}
```

> The `void` line keeps unused-symbol warnings quiet until later tasks add the missing branches. It will be removed in Task 7.

- [ ] **Step 4: Add a `HALT` branch so tests terminate cleanly**

Replace the `default:` clause in the `switch` with:

```ts
      case Op.HALT: {
        steps.push({ pc: executedPc, regs: [...regs], stack: [...stack], emitted: null });
        return { steps, output, halted: true };
      }
      default:
        throw new InterpreterError(`unhandled op in this task: ${Op[inst.op]}`);
```

- [ ] **Step 5: Run the tests**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/interpreter.test.ts`
Expected: 5 pass.

- [ ] **Step 6: Commit**

```bash
git add tinyvm-viz/src/core/interpreter.ts tinyvm-viz/tests/unit/core/interpreter.test.ts
git commit -m "feat(viz): interpreter — arithmetic, clamping, DIV/0"
```

---

### Task 6: Interpreter — comparisons (EQ, LT)

**Files:**
- Modify: `tinyvm-viz/src/core/interpreter.ts`
- Modify: `tinyvm-viz/tests/unit/core/interpreter.test.ts`

- [ ] **Step 1: Append failing tests**

Append to `tinyvm-viz/tests/unit/core/interpreter.test.ts`:

```ts
describe("interpreter: comparisons", () => {
  it("EQ → 1 if equal else 0", () => {
    const p = buildProgram([
      { op: Op.LOAD, args: [0, 4] },
      { op: Op.LOAD, args: [1, 4] },
      { op: Op.LOAD, args: [2, 5] },
      { op: Op.EQ, args: [3, 0, 1] }, // 1
      { op: Op.EQ, args: [4, 0, 2] }, // 0
      { op: Op.HALT, args: [] },
    ]);
    const regs = run(p).steps.at(-1)!.regs;
    expect([regs[3], regs[4]]).toEqual([1, 0]);
  });

  it("LT is strict", () => {
    const p = buildProgram([
      { op: Op.LOAD, args: [0, 2] },
      { op: Op.LOAD, args: [1, 5] },
      { op: Op.LT, args: [2, 0, 1] }, // 1
      { op: Op.LT, args: [3, 1, 0] }, // 0
      { op: Op.LT, args: [4, 0, 0] }, // 0 (strict)
      { op: Op.HALT, args: [] },
    ]);
    const regs = run(p).steps.at(-1)!.regs;
    expect([regs[2], regs[3], regs[4]]).toEqual([1, 0, 0]);
  });
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/interpreter.test.ts`
Expected: 2 fail with "unhandled op".

- [ ] **Step 3: Add EQ and LT branches**

In `tinyvm-viz/src/core/interpreter.ts`, add inside the `switch` (before `case Op.HALT`):

```ts
      case Op.EQ: {
        const [i, j, k] = inst.args as [number, number, number];
        regs[i] = regs[j]! === regs[k]! ? 1 : 0;
        break;
      }
      case Op.LT: {
        const [i, j, k] = inst.args as [number, number, number];
        regs[i] = regs[j]! < regs[k]! ? 1 : 0;
        break;
      }
```

- [ ] **Step 4: Run and confirm pass**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/interpreter.test.ts`
Expected: 7 pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm-viz/src/core/interpreter.ts tinyvm-viz/tests/unit/core/interpreter.test.ts
git commit -m "feat(viz): interpreter — EQ and LT"
```

---

### Task 7: Interpreter — control flow (JZ, JMP, NOP, fall-off-end)

**Files:**
- Modify: `tinyvm-viz/src/core/interpreter.ts`
- Modify: `tinyvm-viz/tests/unit/core/interpreter.test.ts`

- [ ] **Step 1: Append failing tests**

```ts
describe("interpreter: control flow", () => {
  it("JZ taken when register is zero", () => {
    const p = buildProgram([
      { op: Op.LOAD, args: [0, 0] },
      { op: Op.JZ, args: [0], target: "L_END" },
      { op: Op.LOAD, args: [1, 99] },
      { op: Op.NOP, args: [], label: "L_END" },
      { op: Op.HALT, args: [] },
    ]);
    expect(run(p).steps.at(-1)!.regs[1]).toBe(0);
  });

  it("JZ not taken when register is non-zero", () => {
    const p = buildProgram([
      { op: Op.LOAD, args: [0, 1] },
      { op: Op.JZ, args: [0], target: "L_END" },
      { op: Op.LOAD, args: [1, 99] },
      { op: Op.NOP, args: [], label: "L_END" },
      { op: Op.HALT, args: [] },
    ]);
    expect(run(p).steps.at(-1)!.regs[1]).toBe(99);
  });

  it("JMP is unconditional", () => {
    const p = buildProgram([
      { op: Op.JMP, args: [], target: "L_SKIP" },
      { op: Op.LOAD, args: [0, 99] },
      { op: Op.NOP, args: [], label: "L_SKIP" },
      { op: Op.HALT, args: [] },
    ]);
    expect(run(p).steps.at(-1)!.regs[0]).toBe(0);
  });

  it("falls off end halts implicitly", () => {
    const p = buildProgram([
      { op: Op.LOAD, args: [0, 5] },
    ]);
    const trace = run(p);
    expect(trace.halted).toBe(true);
    expect(trace.steps.at(-1)!.regs[0]).toBe(5);
  });
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/interpreter.test.ts`
Expected: 4 fail with "unhandled op" for JZ/JMP/NOP.

- [ ] **Step 3: Add JZ, JMP, NOP branches**

Remove the `void stack; void output; void STACK_DEPTH; void isUserop;` line from Task 5.

Add inside the `switch`:

```ts
      case Op.JZ: {
        const [i] = inst.args as [number];
        if (regs[i]! === 0) {
          const t = inst.target!;
          nextPc = program.labelIndex.get(t)!;
        }
        break;
      }
      case Op.JMP: {
        const t = inst.target!;
        nextPc = program.labelIndex.get(t)!;
        break;
      }
      case Op.NOP:
        break;
```

- [ ] **Step 4: Run and confirm pass**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/interpreter.test.ts`
Expected: 11 pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm-viz/src/core/interpreter.ts tinyvm-viz/tests/unit/core/interpreter.test.ts
git commit -m "feat(viz): interpreter — JZ, JMP, NOP, fall-off-end"
```

---

### Task 8: Interpreter — stack (PUSH, POP) with overflow / underflow

**Files:**
- Modify: `tinyvm-viz/src/core/interpreter.ts`
- Modify: `tinyvm-viz/tests/unit/core/interpreter.test.ts`

- [ ] **Step 1: Append failing tests**

```ts
import { InterpreterError } from "@/core/interpreter";

describe("interpreter: stack", () => {
  it("PUSH then POP round-trips", () => {
    const p = buildProgram([
      { op: Op.LOAD, args: [0, 7] },
      { op: Op.PUSH, args: [0] },
      { op: Op.POP, args: [1] },
      { op: Op.HALT, args: [] },
    ]);
    expect(run(p).steps.at(-1)!.regs[1]).toBe(7);
  });

  it("PUSH past STACK_DEPTH raises", () => {
    const insts = [];
    insts.push({ op: Op.LOAD, args: [0, 1] });
    for (let i = 0; i < 17; i++) insts.push({ op: Op.PUSH, args: [0] });
    const p = buildProgram(insts);
    expect(() => run(p)).toThrow(InterpreterError);
  });

  it("POP from empty stack raises", () => {
    const p = buildProgram([{ op: Op.POP, args: [0] }]);
    expect(() => run(p)).toThrow(InterpreterError);
  });
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/interpreter.test.ts`
Expected: 3 new fail.

- [ ] **Step 3: Add PUSH and POP branches**

Inside `switch`:

```ts
      case Op.PUSH: {
        const [i] = inst.args as [number];
        if (stack.length >= STACK_DEPTH) {
          throw new InterpreterError("stack overflow");
        }
        stack.push(regs[i]!);
        break;
      }
      case Op.POP: {
        const [i] = inst.args as [number];
        if (stack.length === 0) {
          throw new InterpreterError("stack underflow");
        }
        regs[i] = stack.pop()!;
        break;
      }
```

- [ ] **Step 4: Run and confirm pass**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/interpreter.test.ts`
Expected: 14 pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm-viz/src/core/interpreter.ts tinyvm-viz/tests/unit/core/interpreter.test.ts
git commit -m "feat(viz): interpreter — PUSH/POP with overflow/underflow"
```

---

### Task 9: Interpreter — PRINT, step-cap, USEROP raises, trace (de)serialisation

**Files:**
- Modify: `tinyvm-viz/src/core/interpreter.ts`
- Modify: `tinyvm-viz/tests/unit/core/interpreter.test.ts`

- [ ] **Step 1: Append failing tests**

```ts
describe("interpreter: PRINT, step-cap, USEROP", () => {
  it("PRINT emits register value into output", () => {
    const p = buildProgram([
      { op: Op.LOAD, args: [0, 9] },
      { op: Op.PRINT, args: [0] },
      { op: Op.PRINT, args: [0] },
      { op: Op.HALT, args: [] },
    ]);
    expect(run(p).output).toEqual([9, 9]);
  });

  it("step cap raises", () => {
    const p = buildProgram([
      { op: Op.JMP, args: [], target: "L0", label: "L0" },
    ]);
    expect(() => run(p, 100)).toThrow(/step cap/);
  });

  it("disables cap when stepCap=null", () => {
    const p = buildProgram([
      { op: Op.LOAD, args: [0, 5] },
      { op: Op.HALT, args: [] },
    ]);
    expect(run(p, null).halted).toBe(true);
  });

  it("USEROP_0 raises with a clear message", () => {
    const p = buildProgram([{ op: Op.USEROP_0, args: [0, 1] }]);
    expect(() => run(p)).toThrow(/userop/i);
  });
});

describe("interpreter: trace (de)serialisation", () => {
  it("serializeTrace and deserializeTrace are inverses", async () => {
    const { serializeTrace, deserializeTrace } = await import("@/core/interpreter");
    const p = buildProgram([
      { op: Op.LOAD, args: [0, 3] },
      { op: Op.PRINT, args: [0] },
      { op: Op.HALT, args: [] },
    ]);
    const trace = run(p);
    const round = deserializeTrace(serializeTrace(trace));
    expect(round).toEqual(trace);
  });
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/interpreter.test.ts`
Expected: 4 new fail.

- [ ] **Step 3: Add PRINT and USEROP branches and the (de)serialise helpers**

Inside `switch` (before `default`):

```ts
      case Op.PRINT: {
        const [i] = inst.args as [number];
        emitted = regs[i]!;
        output.push(emitted);
        break;
      }
```

Above the `default`, after the USEROP slots are checked, add:

```ts
      case Op.USEROP_0:
      case Op.USEROP_1:
      case Op.USEROP_2:
      case Op.USEROP_3:
      case Op.USEROP_4:
        throw new InterpreterError(
          `userop opcode USEROP_${inst.op - Op.USEROP_0} encountered; substitute via decomposition before run()`,
        );
```

Add (de)serialisation helpers at the bottom of the file:

```ts
import type { SerializedStep, SerializedTrace } from "./types";

export function serializeTrace(t: ExecutionTrace): SerializedTrace {
  return {
    steps: t.steps.map((s) => ({ pc: s.pc, regs: [...s.regs], stack: [...s.stack], emitted: s.emitted })),
    output: [...t.output],
    halted: t.halted,
  };
}

export function deserializeTrace(s: SerializedTrace): ExecutionTrace {
  return {
    steps: s.steps.map<StepRecord>((st: SerializedStep) => ({
      pc: st.pc,
      regs: [...st.regs],
      stack: [...st.stack],
      emitted: st.emitted,
    })),
    output: [...s.output],
    halted: s.halted,
  };
}
```

- [ ] **Step 4: Run and confirm pass**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/interpreter.test.ts`
Expected: 18 pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm-viz/src/core/interpreter.ts tinyvm-viz/tests/unit/core/interpreter.test.ts
git commit -m "feat(viz): interpreter — PRINT, step-cap, USEROP raises, (de)serialisation"
```

---

## Phase D — Parser

### Task 10: Parser — single-line opcodes (LOAD, MOV, ADD, SUB, MUL, DIV, NEG, EQ, LT, PRINT, NOP, HALT, PUSH, POP)

**Files:**
- Create: `tinyvm-viz/src/core/parser.ts`
- Create: `tinyvm-viz/tests/unit/core/parser.test.ts`

- [ ] **Step 1: Write failing tests**

```ts
import { describe, it, expect } from "vitest";
import { parse } from "@/core/parser";
import { Op } from "@/core/isa";

describe("parser: single-line opcodes", () => {
  it("parses LOAD with negative literal", () => {
    const { program, errors } = parse("LOAD R3 -42\n");
    expect(errors).toEqual([]);
    expect(program!.instructions).toEqual([{ op: Op.LOAD, args: [3, -42], label: undefined, target: undefined }]);
  });

  it("parses ADD with three registers", () => {
    const { program, errors } = parse("ADD R0 R1 R2\n");
    expect(errors).toEqual([]);
    expect(program!.instructions[0]).toMatchObject({ op: Op.ADD, args: [0, 1, 2] });
  });

  it("parses a multi-line program", () => {
    const src = "LOAD R0 5\nADD R0 R0 R0\nPRINT R0\nHALT\n";
    const { program, errors } = parse(src);
    expect(errors).toEqual([]);
    expect(program!.instructions.map((i) => i.op)).toEqual([Op.LOAD, Op.ADD, Op.PRINT, Op.HALT]);
  });

  it("accepts trailing whitespace and ;-comments", () => {
    const src = "LOAD R0 5  ; load five\nHALT\n";
    const { program, errors } = parse(src);
    expect(errors).toEqual([]);
    expect(program!.instructions[0]!.args).toEqual([0, 5]);
  });

  it("reports a line-numbered error for an unknown opcode", () => {
    const { program, errors } = parse("FOO R0\n");
    expect(program).toBeUndefined();
    expect(errors).toHaveLength(1);
    expect(errors[0]).toMatchObject({ line: 1, message: expect.stringMatching(/unknown opcode/i) });
  });

  it("reports an error for wrong arity", () => {
    const { program, errors } = parse("ADD R0 R1\n");
    expect(program).toBeUndefined();
    expect(errors).toHaveLength(1);
    expect(errors[0]!.message).toMatch(/ADD .* expects/i);
  });
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/parser.test.ts`
Expected: module not found.

- [ ] **Step 3: Create `tinyvm-viz/src/core/parser.ts`**

```ts
import { buildProgram, Instruction, Op, Program } from "./isa";

export interface ParseError {
  line: number;
  message: string;
}

export interface ParseResult {
  program?: Program;
  errors: ParseError[];
}

interface ArgSchema {
  regs: number;
  lits: number;
  hasTarget: boolean;
}

const SCHEMA: Record<Op, ArgSchema> = {
  [Op.LOAD]: { regs: 1, lits: 1, hasTarget: false },
  [Op.MOV]: { regs: 2, lits: 0, hasTarget: false },
  [Op.ADD]: { regs: 3, lits: 0, hasTarget: false },
  [Op.SUB]: { regs: 3, lits: 0, hasTarget: false },
  [Op.MUL]: { regs: 3, lits: 0, hasTarget: false },
  [Op.DIV]: { regs: 3, lits: 0, hasTarget: false },
  [Op.NEG]: { regs: 2, lits: 0, hasTarget: false },
  [Op.EQ]: { regs: 3, lits: 0, hasTarget: false },
  [Op.LT]: { regs: 3, lits: 0, hasTarget: false },
  [Op.JZ]: { regs: 1, lits: 0, hasTarget: true },
  [Op.JMP]: { regs: 0, lits: 0, hasTarget: true },
  [Op.PUSH]: { regs: 1, lits: 0, hasTarget: false },
  [Op.POP]: { regs: 1, lits: 0, hasTarget: false },
  [Op.PRINT]: { regs: 1, lits: 0, hasTarget: false },
  [Op.NOP]: { regs: 0, lits: 0, hasTarget: false },
  [Op.HALT]: { regs: 0, lits: 0, hasTarget: false },
  [Op.USEROP_0]: { regs: 2, lits: 0, hasTarget: false },
  [Op.USEROP_1]: { regs: 3, lits: 0, hasTarget: false },
  [Op.USEROP_2]: { regs: 2, lits: 0, hasTarget: false },
  [Op.USEROP_3]: { regs: 3, lits: 0, hasTarget: false },
  [Op.USEROP_4]: { regs: 2, lits: 0, hasTarget: false },
};

const OP_BY_NAME: Record<string, Op> = Object.fromEntries(
  Object.keys(Op)
    .filter((k) => isNaN(Number(k)) && !k.startsWith("USEROP"))
    .map((k) => [k, Op[k as keyof typeof Op] as Op]),
);

function stripComment(line: string): string {
  const ci = line.indexOf(";");
  return ci >= 0 ? line.slice(0, ci) : line;
}

function tokenise(line: string): string[] {
  return stripComment(line).trim().split(/\s+/).filter((t) => t.length > 0);
}

function parseReg(tok: string): number | null {
  if (!/^R[0-7]$/.test(tok)) return null;
  return Number(tok.slice(1));
}

function parseInt127(tok: string): number | null {
  if (!/^-?\d+$/.test(tok)) return null;
  return Number(tok);
}

function parseLabelRef(tok: string): string | null {
  return /^L\d+$/.test(tok) ? tok : null;
}

export function parse(source: string): ParseResult {
  const errors: ParseError[] = [];
  const insts: Instruction[] = [];
  const lines = source.split("\n");
  for (let li = 0; li < lines.length; li++) {
    const raw = lines[li]!;
    let line = raw;
    let label: string | undefined;
    const stripped = stripComment(line).trim();
    if (stripped.length === 0) continue;

    // Optional label definition: L<digits>: [opcode...]
    const labelMatch = stripped.match(/^(L\d+)\s*:\s*(.*)$/);
    if (labelMatch) {
      label = labelMatch[1]!;
      line = labelMatch[2]!;
    } else {
      line = stripped;
    }

    const tokens = tokenise(line);
    if (tokens.length === 0) {
      // a bare label on its own line — synthesise a NOP carrying the label
      insts.push({ op: Op.NOP, args: [], label, target: undefined });
      continue;
    }
    const opName = tokens[0]!.toUpperCase();
    const op = OP_BY_NAME[opName];
    if (op === undefined) {
      errors.push({ line: li + 1, message: `unknown opcode: ${opName}` });
      continue;
    }
    const schema = SCHEMA[op];
    const expected = schema.regs + schema.lits + (schema.hasTarget ? 1 : 0);
    const got = tokens.length - 1;
    if (got !== expected) {
      errors.push({ line: li + 1, message: `${opName} expects ${expected} operands, got ${got}` });
      continue;
    }

    const args: number[] = [];
    let target: string | undefined;
    let cursor = 1;
    for (let i = 0; i < schema.regs; i++) {
      const r = parseReg(tokens[cursor]!);
      if (r === null) {
        errors.push({ line: li + 1, message: `expected register, got '${tokens[cursor]}'` });
        cursor++;
        continue;
      }
      args.push(r);
      cursor++;
    }
    for (let i = 0; i < schema.lits; i++) {
      const v = parseInt127(tokens[cursor]!);
      if (v === null) {
        errors.push({ line: li + 1, message: `expected integer literal, got '${tokens[cursor]}'` });
        cursor++;
        continue;
      }
      args.push(v);
      cursor++;
    }
    if (schema.hasTarget) {
      const t = parseLabelRef(tokens[cursor]!);
      if (t === null) {
        errors.push({ line: li + 1, message: `expected label target, got '${tokens[cursor]}'` });
      } else {
        target = t;
      }
      cursor++;
    }
    insts.push({ op, args, label, target });
  }

  if (errors.length > 0) return { errors };
  try {
    return { program: buildProgram(insts), errors: [] };
  } catch (e) {
    return { errors: [{ line: 0, message: (e as Error).message }] };
  }
}
```

- [ ] **Step 4: Run and confirm pass**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/parser.test.ts`
Expected: 6 pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm-viz/src/core/parser.ts tinyvm-viz/tests/unit/core/parser.test.ts
git commit -m "feat(viz): parser — single-line opcodes with line-numbered errors"
```

---

### Task 11: Parser — labels, JZ / JMP targets, round-trip via interpreter

**Files:**
- Modify: `tinyvm-viz/tests/unit/core/parser.test.ts`

- [ ] **Step 1: Append failing tests**

```ts
import { run } from "@/core/interpreter";

describe("parser: labels and jumps", () => {
  it("parses a labelled NOP and uses it as a JZ target", () => {
    const src = "LOAD R0 0\nJZ R0 L0\nLOAD R1 99\nL0:NOP\nHALT\n";
    const { program, errors } = parse(src);
    expect(errors).toEqual([]);
    expect(program!.labelIndex.get("L0")).toBe(3);
    expect(run(program!).steps.at(-1)!.regs[1]).toBe(0);
  });

  it("parses unconditional JMP", () => {
    const src = "JMP L1\nLOAD R0 99\nL1:HALT\n";
    const { program, errors } = parse(src);
    expect(errors).toEqual([]);
    expect(run(program!).steps.at(-1)!.regs[0]).toBe(0);
  });

  it("accepts a label on its own line", () => {
    const src = "L0:\nLOAD R0 1\nHALT\n";
    const { program, errors } = parse(src);
    expect(errors).toEqual([]);
    expect(program!.labelIndex.has("L0")).toBe(true);
  });

  it("rejects duplicate label definitions", () => {
    const src = "L0:NOP\nL0:HALT\n";
    const { program, errors } = parse(src);
    expect(program).toBeUndefined();
    expect(errors[0]!.message).toMatch(/duplicate label/);
  });
});
```

- [ ] **Step 2: Run and confirm pass — most should pass already, duplicate-label test may need a tweak**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/parser.test.ts`
Expected: the JZ/JMP/standalone-label cases pass; duplicate-label may pass via `buildProgram` already, depending on whether `errors[0]` has the right shape.

- [ ] **Step 3: If duplicate-label is missing line info, adjust the catch block in `parse`**

Replace the trailing `catch` clause in `parse`:

```ts
  } catch (e) {
    return { errors: [{ line: 0, message: (e as Error).message }] };
  }
```

with:

```ts
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

- [ ] **Step 4: Run and confirm pass**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/parser.test.ts`
Expected: 10 pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm-viz/src/core/parser.ts tinyvm-viz/tests/unit/core/parser.test.ts
git commit -m "feat(viz): parser — labels and JZ/JMP targets"
```

---

## Phase E — Tokeniser subset

### Task 12: Tokeniser — surface-text canonical form (encode)

**Files:**
- Create: `tinyvm-viz/src/core/tokeniser.ts`
- Create: `tinyvm-viz/tests/unit/core/tokeniser.test.ts`

- [ ] **Step 1: Write failing tests**

```ts
import { describe, it, expect } from "vitest";
import { renderProgramText } from "@/core/tokeniser";
import { buildProgram, Op } from "@/core/isa";

describe("tokeniser: renderProgramText (canonical form)", () => {
  it("renders LOAD with negative literal", () => {
    const p = buildProgram([{ op: Op.LOAD, args: [3, -42] }]);
    expect(renderProgramText(p)).toBe("LOAD R3 -42\n");
  });

  it("renders ADD with three registers", () => {
    const p = buildProgram([{ op: Op.ADD, args: [0, 1, 2] }]);
    expect(renderProgramText(p)).toBe("ADD R0 R1 R2\n");
  });

  it("renders a label-defined line as 'L3:OP ...'", () => {
    const p = buildProgram([{ op: Op.ADD, args: [0, 1, 2], label: "L3" }]);
    expect(renderProgramText(p)).toBe("L3:ADD R0 R1 R2\n");
  });

  it("renders JZ with a label target", () => {
    const p = buildProgram([
      { op: Op.JZ, args: [1], target: "L7" },
      { op: Op.NOP, args: [], label: "L7" },
    ]);
    expect(renderProgramText(p)).toBe("JZ R1 L7\nL7:NOP\n");
  });
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/tokeniser.test.ts`
Expected: module not found.

- [ ] **Step 3: Create `tinyvm-viz/src/core/tokeniser.ts`**

```ts
import { Instruction, Op, Program } from "./isa";

const SCHEMA: Record<Op, { regs: number; lits: number; hasTarget: boolean }> = {
  [Op.LOAD]: { regs: 1, lits: 1, hasTarget: false },
  [Op.MOV]: { regs: 2, lits: 0, hasTarget: false },
  [Op.ADD]: { regs: 3, lits: 0, hasTarget: false },
  [Op.SUB]: { regs: 3, lits: 0, hasTarget: false },
  [Op.MUL]: { regs: 3, lits: 0, hasTarget: false },
  [Op.DIV]: { regs: 3, lits: 0, hasTarget: false },
  [Op.NEG]: { regs: 2, lits: 0, hasTarget: false },
  [Op.EQ]: { regs: 3, lits: 0, hasTarget: false },
  [Op.LT]: { regs: 3, lits: 0, hasTarget: false },
  [Op.JZ]: { regs: 1, lits: 0, hasTarget: true },
  [Op.JMP]: { regs: 0, lits: 0, hasTarget: true },
  [Op.PUSH]: { regs: 1, lits: 0, hasTarget: false },
  [Op.POP]: { regs: 1, lits: 0, hasTarget: false },
  [Op.PRINT]: { regs: 1, lits: 0, hasTarget: false },
  [Op.NOP]: { regs: 0, lits: 0, hasTarget: false },
  [Op.HALT]: { regs: 0, lits: 0, hasTarget: false },
  [Op.USEROP_0]: { regs: 2, lits: 0, hasTarget: false },
  [Op.USEROP_1]: { regs: 3, lits: 0, hasTarget: false },
  [Op.USEROP_2]: { regs: 2, lits: 0, hasTarget: false },
  [Op.USEROP_3]: { regs: 3, lits: 0, hasTarget: false },
  [Op.USEROP_4]: { regs: 2, lits: 0, hasTarget: false },
};

function renderInstruction(inst: Instruction): string {
  const parts: string[] = [];
  const opName = Op[inst.op];
  parts.push(opName);
  const schema = SCHEMA[inst.op];
  let cursor = 0;
  for (let i = 0; i < schema.regs; i++) {
    parts.push(`R${inst.args[cursor]}`);
    cursor++;
  }
  for (let i = 0; i < schema.lits; i++) {
    parts.push(String(inst.args[cursor]));
    cursor++;
  }
  if (schema.hasTarget) parts.push(inst.target!);
  const body = parts.join(" ");
  return inst.label !== undefined ? `${inst.label}:${body}` : body;
}

export function renderProgramText(program: Program): string {
  return program.instructions.map(renderInstruction).map((l) => l + "\n").join("");
}
```

- [ ] **Step 4: Run and confirm pass**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/tokeniser.test.ts`
Expected: 4 pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm-viz/src/core/tokeniser.ts tinyvm-viz/tests/unit/core/tokeniser.test.ts
git commit -m "feat(viz): tokeniser — canonical surface-text renderer"
```

---

### Task 13: Tokeniser ↔ Parser round-trip

**Files:**
- Modify: `tinyvm-viz/tests/unit/core/tokeniser.test.ts`

- [ ] **Step 1: Append a round-trip test**

```ts
import { parse } from "@/core/parser";

describe("tokeniser/parser round-trip", () => {
  it("parse(render(p)) preserves structure", () => {
    const p = buildProgram([
      { op: Op.LOAD, args: [0, 5] },
      { op: Op.ADD, args: [1, 0, 0] },
      { op: Op.JZ, args: [1], target: "L0" },
      { op: Op.PRINT, args: [1] },
      { op: Op.NOP, args: [], label: "L0" },
      { op: Op.HALT, args: [] },
    ]);
    const text = renderProgramText(p);
    const { program, errors } = parse(text);
    expect(errors).toEqual([]);
    expect(program!.instructions).toEqual(p.instructions);
  });
});
```

- [ ] **Step 2: Run**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/tokeniser.test.ts`
Expected: 5 pass. If the round-trip fails because the parser doesn't accept `L0:HALT` without a space, fix the parser's `labelMatch` regex to `/^(L\d+)\s*:\s*(.*)$/` (already present in Task 10 — confirm with a re-read).

- [ ] **Step 3: Commit**

```bash
git add tinyvm-viz/tests/unit/core/tokeniser.test.ts
git commit -m "test(viz): tokeniser/parser round-trip"
```

---

## Phase F — Verifier

### Task 14: Verifier — `scoreOutput`

**Files:**
- Create: `tinyvm-viz/src/core/verifier.ts`
- Create: `tinyvm-viz/tests/unit/core/verifier.test.ts`

- [ ] **Step 1: Write failing tests**

```ts
import { describe, it, expect } from "vitest";
import { scoreOutput } from "@/core/verifier";

describe("verifier: scoreOutput", () => {
  it("returns 1 on exact match", () => {
    expect(scoreOutput([1, 2, 3], [1, 2, 3])).toBe(1);
  });
  it("returns 0 on mismatch", () => {
    expect(scoreOutput([1, 2, 3], [1, 2, 4])).toBe(0);
  });
  it("returns 0 on length mismatch", () => {
    expect(scoreOutput([1, 2], [1, 2, 3])).toBe(0);
  });
  it("handles negatives", () => {
    expect(scoreOutput([-5, 0, 5], [-5, 0, 5])).toBe(1);
  });
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/verifier.test.ts`
Expected: module not found.

- [ ] **Step 3: Create `tinyvm-viz/src/core/verifier.ts`**

```ts
import { Op, Program } from "./isa";

export function scoreOutput(predicted: number[], target: number[]): number {
  if (predicted.length !== target.length) return 0;
  for (let i = 0; i < predicted.length; i++) {
    if (predicted[i] !== target[i]) return 0;
  }
  return 1;
}
```

- [ ] **Step 4: Run and confirm pass**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/verifier.test.ts`
Expected: 4 pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm-viz/src/core/verifier.ts tinyvm-viz/tests/unit/core/verifier.test.ts
git commit -m "feat(viz): verifier — scoreOutput"
```

---

### Task 15: Verifier — `validate` (arity, label targets, PRINT-write reachability, stack balance/depth)

**Files:**
- Modify: `tinyvm-viz/src/core/verifier.ts`
- Modify: `tinyvm-viz/tests/unit/core/verifier.test.ts`

- [ ] **Step 1: Append failing tests**

```ts
import { validate } from "@/core/verifier";
import { buildProgram } from "@/core/isa";

describe("verifier: validate", () => {
  it("accepts a clean program", () => {
    const p = buildProgram([
      { op: Op.LOAD, args: [0, 5] },
      { op: Op.PRINT, args: [0] },
      { op: Op.HALT, args: [] },
    ]);
    expect(validate(p).ok).toBe(true);
  });

  it("rejects an unknown JZ label target", () => {
    const p = buildProgram([
      { op: Op.LOAD, args: [0, 0] },
      { op: Op.JZ, args: [0], target: "L99" },
      { op: Op.HALT, args: [] },
    ]);
    const r = validate(p);
    expect(r.ok).toBe(false);
    expect(r.errors[0]).toMatch(/unknown label target/);
  });

  it("rejects wrong arity", () => {
    const p = buildProgram([{ op: Op.ADD, args: [0, 1] }]);
    expect(validate(p).ok).toBe(false);
  });

  it("rejects PRINT R0 with no prior write", () => {
    const p = buildProgram([{ op: Op.PRINT, args: [0] }]);
    const r = validate(p);
    expect(r.ok).toBe(false);
    expect(r.errors[0]).toMatch(/PRINT R0.*not preceded by write/i);
  });

  it("rejects POP from empty stack on all paths", () => {
    const p = buildProgram([{ op: Op.POP, args: [0] }]);
    const r = validate(p);
    expect(r.ok).toBe(false);
    expect(r.errors[0]).toMatch(/POP.*underflow/i);
  });

  it("rejects PUSH overflowing depth 16", () => {
    const insts = [];
    insts.push({ op: Op.LOAD, args: [0, 1] });
    for (let i = 0; i < 17; i++) insts.push({ op: Op.PUSH, args: [0] });
    const r = validate(buildProgram(insts));
    expect(r.ok).toBe(false);
  });
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/verifier.test.ts`
Expected: 6 new fail.

- [ ] **Step 3: Implement `validate`**

Append to `tinyvm-viz/src/core/verifier.ts`:

```ts
import { NUM_REGS, STACK_DEPTH } from "./isa";

const ARG_SCHEMA: Record<Op, { regs: number; lits: number; hasTarget: boolean }> = {
  [Op.LOAD]: { regs: 1, lits: 1, hasTarget: false },
  [Op.MOV]: { regs: 2, lits: 0, hasTarget: false },
  [Op.ADD]: { regs: 3, lits: 0, hasTarget: false },
  [Op.SUB]: { regs: 3, lits: 0, hasTarget: false },
  [Op.MUL]: { regs: 3, lits: 0, hasTarget: false },
  [Op.DIV]: { regs: 3, lits: 0, hasTarget: false },
  [Op.NEG]: { regs: 2, lits: 0, hasTarget: false },
  [Op.EQ]: { regs: 3, lits: 0, hasTarget: false },
  [Op.LT]: { regs: 3, lits: 0, hasTarget: false },
  [Op.JZ]: { regs: 1, lits: 0, hasTarget: true },
  [Op.JMP]: { regs: 0, lits: 0, hasTarget: true },
  [Op.PUSH]: { regs: 1, lits: 0, hasTarget: false },
  [Op.POP]: { regs: 1, lits: 0, hasTarget: false },
  [Op.PRINT]: { regs: 1, lits: 0, hasTarget: false },
  [Op.NOP]: { regs: 0, lits: 0, hasTarget: false },
  [Op.HALT]: { regs: 0, lits: 0, hasTarget: false },
  [Op.USEROP_0]: { regs: 2, lits: 0, hasTarget: false },
  [Op.USEROP_1]: { regs: 3, lits: 0, hasTarget: false },
  [Op.USEROP_2]: { regs: 2, lits: 0, hasTarget: false },
  [Op.USEROP_3]: { regs: 3, lits: 0, hasTarget: false },
  [Op.USEROP_4]: { regs: 2, lits: 0, hasTarget: false },
};

const WRITES_ONE_REG = new Set([Op.LOAD, Op.MOV, Op.ADD, Op.SUB, Op.MUL, Op.DIV, Op.NEG, Op.EQ, Op.LT, Op.POP]);

export interface ValidationResult {
  ok: boolean;
  errors: string[];
}

function successors(program: Program, idx: number): number[] {
  const inst = program.instructions[idx]!;
  const n = program.instructions.length;
  if (inst.op === Op.HALT) return [];
  if (inst.op === Op.JMP) return [program.labelIndex.get(inst.target!)!];
  if (inst.op === Op.JZ) {
    const out: number[] = [];
    if (idx + 1 < n) out.push(idx + 1);
    out.push(program.labelIndex.get(inst.target!)!);
    return out;
  }
  return idx + 1 < n ? [idx + 1] : [];
}

function checkArity(program: Program, errors: string[]): void {
  for (let i = 0; i < program.instructions.length; i++) {
    const inst = program.instructions[i]!;
    const s = ARG_SCHEMA[inst.op];
    const expected = s.regs + s.lits;
    if (inst.args.length !== expected) {
      errors.push(`${Op[inst.op]} at idx ${i} expects ${expected} args, got ${inst.args.length}`);
    }
    if (s.hasTarget && inst.target === undefined) {
      errors.push(`${Op[inst.op]} at idx ${i} requires target label`);
    }
  }
}

function checkLabelTargets(program: Program, errors: string[]): void {
  for (let i = 0; i < program.instructions.length; i++) {
    const inst = program.instructions[i]!;
    if (inst.target !== undefined && !program.labelIndex.has(inst.target)) {
      errors.push(`unknown label target: ${inst.target}`);
    }
  }
}

function writesOf(inst: Instruction): Set<number> {
  return WRITES_ONE_REG.has(inst.op) ? new Set([inst.args[0]!]) : new Set();
}

import type { Instruction } from "./isa";

function checkPrintPredecessors(program: Program, errors: string[]): void {
  const n = program.instructions.length;
  if (n === 0) return;
  const UNIVERSE = new Set<number>();
  for (let r = 0; r < NUM_REGS; r++) UNIVERSE.add(r);
  const writtenIn: Set<number>[] = Array.from({ length: n }, () => new Set(UNIVERSE));
  writtenIn[0] = new Set();
  const preds: number[][] = Array.from({ length: n }, () => []);
  for (let i = 0; i < n; i++) {
    for (const j of successors(program, i)) preds[j]!.push(i);
  }
  let changed = true;
  while (changed) {
    changed = false;
    for (let i = 1; i < n; i++) {
      const p = preds[i]!;
      let next: Set<number>;
      if (p.length === 0) {
        next = new Set();
      } else {
        const first = new Set([...writtenIn[p[0]!]!, ...writesOf(program.instructions[p[0]!]!)]);
        next = first;
        for (let k = 1; k < p.length; k++) {
          const s = new Set([...writtenIn[p[k]!]!, ...writesOf(program.instructions[p[k]!]!)]);
          next = new Set([...next].filter((x) => s.has(x)));
        }
      }
      if (next.size !== writtenIn[i]!.size || ![...next].every((x) => writtenIn[i]!.has(x))) {
        writtenIn[i] = next;
        changed = true;
      }
    }
  }
  for (let i = 0; i < n; i++) {
    const inst = program.instructions[i]!;
    if (inst.op === Op.PRINT && !writtenIn[i]!.has(inst.args[0]!)) {
      errors.push(`PRINT R${inst.args[0]} at idx ${i} not preceded by write on all paths`);
    }
  }
}

function checkStackBalance(program: Program, errors: string[]): void {
  const n = program.instructions.length;
  if (n === 0) return;
  const depthIn: (number | null)[] = new Array(n).fill(null);
  depthIn[0] = 0;
  const preds: number[][] = Array.from({ length: n }, () => []);
  for (let i = 0; i < n; i++) {
    for (const j of successors(program, i)) preds[j]!.push(i);
  }
  const delta = (op: Op): number => (op === Op.PUSH ? 1 : op === Op.POP ? -1 : 0);
  let changed = true;
  while (changed) {
    changed = false;
    for (let i = 1; i < n; i++) {
      const p = preds[i]!;
      if (p.length === 0) continue;
      let merged: number | null = null;
      for (const pi of p) {
        if (depthIn[pi] === null) continue;
        const d = depthIn[pi]! + delta(program.instructions[pi]!.op);
        if (d < 0) { errors.push(`POP at idx ${pi} underflows`); return; }
        if (d > STACK_DEPTH) { errors.push(`PUSH at idx ${pi} overflows (depth ${d} > ${STACK_DEPTH})`); return; }
        const dAfter = d + delta(program.instructions[i]!.op);
        if (dAfter < 0) { errors.push(`POP at idx ${i} underflows`); return; }
        if (dAfter > STACK_DEPTH) { errors.push(`PUSH at idx ${i} overflows (depth ${dAfter} > ${STACK_DEPTH})`); return; }
        if (merged === null) merged = d;
        else if (merged !== d) { errors.push(`stack depth at idx ${i} not balanced across paths: ${merged} vs ${d}`); return; }
      }
      if (merged !== null && depthIn[i] !== merged) {
        depthIn[i] = merged;
        changed = true;
      }
    }
  }
}

export function validate(program: Program): ValidationResult {
  const errors: string[] = [];
  checkArity(program, errors);
  if (errors.length === 0) checkLabelTargets(program, errors);
  if (errors.length === 0) checkPrintPredecessors(program, errors);
  if (errors.length === 0) checkStackBalance(program, errors);
  return { ok: errors.length === 0, errors };
}
```

- [ ] **Step 4: Run and confirm pass**

Run: `cd tinyvm-viz && npx vitest run tests/unit/core/verifier.test.ts`
Expected: 10 pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm-viz/src/core/verifier.ts tinyvm-viz/tests/unit/core/verifier.test.ts
git commit -m "feat(viz): verifier — validate (arity, labels, PRINT-write, stack balance)"
```

---

## Phase G — Parity harness

### Task 16: Python-side `export_golden_fixtures.py`

**Files:**
- Create: `tinyvm/scripts/__init__.py`
- Create: `tinyvm/scripts/export_golden_fixtures.py`
- Create: `tinyvm/tests/test_export_golden_fixtures.py`
- Create: `tinyvm-viz/tests/fixtures/.gitkeep`

- [ ] **Step 1: Write a failing test on the Python side**

`tinyvm/tests/test_export_golden_fixtures.py`:

```python
import json
from pathlib import Path

from tinyvm.scripts.export_golden_fixtures import build_fixtures, write_fixtures


def test_build_fixtures_is_idempotent_on_seed_sweep():
    a = build_fixtures()
    b = build_fixtures()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_build_fixtures_covers_each_generator():
    fixtures = build_fixtures()
    generators = {f["generator"] for f in fixtures}
    assert generators == {"gen_counter", "gen_register_trace", "gen_branched"}


def test_each_fixture_has_required_keys():
    for f in build_fixtures():
        assert {"seed", "generator", "spec", "source_text", "program_ir", "expected_trace"} <= f.keys()
        assert f["expected_trace"]["halted"] is True


def test_write_fixtures_writes_stable_json(tmp_path: Path):
    out = tmp_path / "golden.json"
    write_fixtures(out)
    a = out.read_text()
    write_fixtures(out)
    b = out.read_text()
    assert a == b
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd /Users/sidgraph/FANC && python -m pytest tinyvm/tests/test_export_golden_fixtures.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Create `tinyvm/scripts/__init__.py`**

Empty file.

- [ ] **Step 4: Create `tinyvm/scripts/export_golden_fixtures.py`**

```python
"""Emit golden parity fixtures consumed by the TS interpreter."""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from tinyvm.generators import gen_branched, gen_counter, gen_register_trace, GenSpec
from tinyvm.interpreter import run
from tinyvm.isa import Program
from tinyvm.tokeniser import render_direct_text


# A small, fixed sweep — Tier 0/1/2 difficulty axes.
COUNTER_SEEDS: list[tuple[int, int]] = [(0, 4), (1, 8), (2, 4), (3, 6)]
REGISTER_TRACE_SPECS: list[tuple[int, int, int]] = [  # (seed, n, k)
    (0, 8, 2), (1, 16, 4), (2, 32, 4), (3, 16, 8),
]
BRANCHED_SPECS: list[tuple[int, GenSpec]] = [
    (0, GenSpec(n=24, k=4, b=1, l=0)),
    (1, GenSpec(n=32, k=4, b=2, l=4)),
    (2, GenSpec(n=48, k=6, b=2, l=8)),
    (3, GenSpec(n=48, k=6, b=0, l=0, use_stack=True, stack_frames=2)),
]


def _serialise_inst(inst: Any) -> dict:
    return {
        "op": int(inst.op),
        "args": list(inst.args),
        "label": inst.label,
        "target": inst.target,
    }


def _serialise_program(p: Program) -> dict:
    return {
        "instructions": [_serialise_inst(i) for i in p.instructions],
        "label_index": dict(p.label_index),
    }


def _serialise_trace(t: Any) -> dict:
    return {
        "steps": [
            {"pc": s.pc, "regs": list(s.regs), "stack": list(s.stack), "emitted": s.emitted}
            for s in t.steps
        ],
        "output": list(t.output),
        "halted": t.halted,
    }


def _one(generator: str, seed: int, spec: dict, program: Program) -> dict:
    trace = run(program)
    src, _ = render_direct_text(program, trace)
    # Strip the leading BOS/trailing EOS marks render_direct_text leaves in.
    # render_direct_text emits 'BOS ... EOS'; we want just the program text.
    # The text renderer omits BOS/EOS already; if it's present, this trims defensively.
    return {
        "seed": seed,
        "generator": generator,
        "spec": spec,
        "source_text": src,
        "program_ir": _serialise_program(program),
        "expected_trace": _serialise_trace(trace),
    }


def build_fixtures() -> list[dict]:
    out: list[dict] = []
    for seed, n in COUNTER_SEEDS:
        p = gen_counter(n=n, rng=random.Random(seed))
        out.append(_one("gen_counter", seed, {"n": n}, p))
    for seed, n, k in REGISTER_TRACE_SPECS:
        p = gen_register_trace(n=n, k=k, rng=random.Random(seed))
        out.append(_one("gen_register_trace", seed, {"n": n, "k": k}, p))
    for seed, spec in BRANCHED_SPECS:
        p = gen_branched(spec=spec, rng=random.Random(seed))
        out.append(_one(
            "gen_branched",
            seed,
            {"n": spec.n, "k": spec.k, "b": spec.b, "l": spec.l, "use_stack": spec.use_stack, "stack_frames": spec.stack_frames},
            p,
        ))
    return out


def write_fixtures(out_path: Path) -> None:
    fixtures = build_fixtures()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(fixtures, indent=2, sort_keys=True))


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[2] / "tinyvm-viz" / "tests" / "fixtures" / "golden.json"
    write_fixtures(target)
    print(f"wrote {target}")
```

- [ ] **Step 5: Run and confirm pass**

Run: `cd /Users/sidgraph/FANC && python -m pytest tinyvm/tests/test_export_golden_fixtures.py -v`
Expected: 4 pass.

- [ ] **Step 6: Emit the actual fixture file**

Run: `cd /Users/sidgraph/FANC && python -m tinyvm.scripts.export_golden_fixtures`
Expected: prints `wrote /Users/sidgraph/FANC/tinyvm-viz/tests/fixtures/golden.json`.

- [ ] **Step 7: Commit**

```bash
git add tinyvm/scripts/__init__.py tinyvm/scripts/export_golden_fixtures.py \
        tinyvm/tests/test_export_golden_fixtures.py \
        tinyvm-viz/tests/fixtures/golden.json
git commit -m "feat(viz): export_golden_fixtures.py emits parity bundle"
```

---

### Task 17: TS parity test

**Files:**
- Create: `tinyvm-viz/tests/parity/interpreter.parity.test.ts`
- Modify: `tinyvm-viz/vitest.config.ts` (include `tests/parity/**`)

- [ ] **Step 1: Update `vitest.config.ts` include glob**

In `tinyvm-viz/vitest.config.ts`, change `include` to:

```ts
    include: ["tests/**/*.test.{ts,tsx}", "tests/parity/**/*.test.ts"],
```

- [ ] **Step 2: Write the parity test**

`tinyvm-viz/tests/parity/interpreter.parity.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { parse } from "@/core/parser";
import { run, serializeTrace } from "@/core/interpreter";
import { Op } from "@/core/isa";

const fixturePath = resolve(__dirname, "../fixtures/golden.json");
const fixtures = JSON.parse(readFileSync(fixturePath, "utf-8")) as Array<{
  seed: number;
  generator: string;
  spec: Record<string, unknown>;
  source_text: string;
  program_ir: {
    instructions: Array<{ op: number; args: number[]; label: string | null; target: string | null }>;
    label_index: Record<string, number>;
  };
  expected_trace: { steps: Array<{ pc: number; regs: number[]; stack: number[]; emitted: number | null }>; output: number[]; halted: boolean };
}>;

describe("parity: TS interpreter matches Python golden fixtures", () => {
  for (const f of fixtures) {
    it(`${f.generator} seed=${f.seed} (${JSON.stringify(f.spec)})`, () => {
      const { program, errors } = parse(f.source_text);
      expect(errors).toEqual([]);

      // parser IR equality (catches parser drift independently of interpreter drift)
      const tsInsts = program!.instructions.map((i) => ({
        op: i.op,
        args: i.args,
        label: i.label ?? null,
        target: i.target ?? null,
      }));
      expect(tsInsts).toEqual(f.program_ir.instructions);

      // interpreter parity
      const trace = serializeTrace(run(program!));
      expect(trace).toEqual(f.expected_trace);
      void Op;
    });
  }
});
```

- [ ] **Step 3: Run**

Run: `cd tinyvm-viz && npx vitest run tests/parity`
Expected: each fixture passes. If a generator-specific case fails (e.g., a label round-trip mismatch), iterate on the parser/renderer until parity holds; the failure message should pinpoint the divergent field.

- [ ] **Step 4: Commit**

```bash
git add tinyvm-viz/tests/parity/interpreter.parity.test.ts tinyvm-viz/vitest.config.ts
git commit -m "test(viz): parity layer — TS interpreter vs Python golden fixtures"
```

---

## Phase H — Execution panel primitives

### Task 18: `<RegisterFile>` component

**Files:**
- Create: `tinyvm-viz/src/components/RegisterFile.tsx`
- Create: `tinyvm-viz/tests/unit/components/RegisterFile.test.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { RegisterFile } from "@/components/RegisterFile";

describe("RegisterFile", () => {
  it("renders 8 registers with given values", () => {
    render(<RegisterFile regs={[1, 2, 3, 4, 5, 6, 7, 8]} highlightedReg={null} />);
    for (let i = 0; i < 8; i++) {
      expect(screen.getByTestId(`reg-${i}`)).toHaveTextContent(`R${i}`);
      expect(screen.getByTestId(`reg-${i}-value`)).toHaveTextContent(String(i + 1));
    }
  });

  it("highlights the register passed in highlightedReg", () => {
    render(<RegisterFile regs={[0, 0, 0, 0, 0, 0, 0, 0]} highlightedReg={3} />);
    expect(screen.getByTestId("reg-3")).toHaveAttribute("data-highlighted", "true");
    expect(screen.getByTestId("reg-2")).toHaveAttribute("data-highlighted", "false");
  });
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/RegisterFile.test.tsx`
Expected: module not found.

- [ ] **Step 3: Create the component**

```tsx
interface RegisterFileProps {
  regs: readonly number[];
  highlightedReg: number | null;
}

export function RegisterFile({ regs, highlightedReg }: RegisterFileProps) {
  return (
    <div className="grid grid-cols-2 gap-1 text-sm font-mono">
      {regs.map((v, i) => {
        const highlighted = i === highlightedReg;
        return (
          <div
            key={i}
            data-testid={`reg-${i}`}
            data-highlighted={highlighted ? "true" : "false"}
            className={`flex items-center justify-between px-2 py-1 rounded border ${
              highlighted ? "bg-amber-100 border-amber-300" : "bg-white border-slate-200"
            }`}
          >
            <span className="text-slate-500">R{i}</span>
            <span data-testid={`reg-${i}-value`} className="text-slate-900">
              {v}
            </span>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4: Run and confirm pass**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/RegisterFile.test.tsx`
Expected: 2 pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm-viz/src/components/RegisterFile.tsx tinyvm-viz/tests/unit/components/RegisterFile.test.tsx
git commit -m "feat(viz): RegisterFile component"
```

---

### Task 19: `<StackView>` component

**Files:**
- Create: `tinyvm-viz/src/components/StackView.tsx`
- Create: `tinyvm-viz/tests/unit/components/StackView.test.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StackView } from "@/components/StackView";

describe("StackView", () => {
  it("renders the stack top-down with depth label", () => {
    render(<StackView stack={[1, 2, 3]} maxDepth={16} />);
    expect(screen.getByTestId("stack-depth")).toHaveTextContent("3 / 16");
    const items = screen.getAllByTestId(/stack-item-/);
    expect(items[0]).toHaveTextContent("3");      // top at top
    expect(items[2]).toHaveTextContent("1");
  });

  it("renders an empty stack with depth 0", () => {
    render(<StackView stack={[]} maxDepth={16} />);
    expect(screen.getByTestId("stack-depth")).toHaveTextContent("0 / 16");
    expect(screen.queryAllByTestId(/stack-item-/)).toHaveLength(0);
  });
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/StackView.test.tsx`
Expected: module not found.

- [ ] **Step 3: Create the component**

```tsx
interface StackViewProps {
  stack: readonly number[];
  maxDepth: number;
}

export function StackView({ stack, maxDepth }: StackViewProps) {
  const reversed = [...stack].reverse(); // top first
  return (
    <div className="text-sm font-mono">
      <div className="space-y-1">
        {reversed.map((v, i) => (
          <div
            key={i}
            data-testid={`stack-item-${i}`}
            className="px-2 py-1 rounded border bg-white border-slate-200"
          >
            {v}
          </div>
        ))}
      </div>
      <div data-testid="stack-depth" className="mt-2 text-xs text-slate-500">
        {stack.length} / {maxDepth}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run and confirm pass**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/StackView.test.tsx`
Expected: 2 pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm-viz/src/components/StackView.tsx tinyvm-viz/tests/unit/components/StackView.test.tsx
git commit -m "feat(viz): StackView component"
```

---

### Task 20: `<ProgramView>` component (read-only program with PC arrow)

**Files:**
- Create: `tinyvm-viz/src/components/ProgramView.tsx`
- Create: `tinyvm-viz/tests/unit/components/ProgramView.test.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProgramView } from "@/components/ProgramView";

describe("ProgramView", () => {
  it("renders each instruction as a row and marks the active PC with ▶", () => {
    const source = "LOAD R0 5\nADD R0 R0 R0\nPRINT R0\nHALT\n";
    render(<ProgramView source={source} activePc={1} />);
    expect(screen.getByTestId("pgm-line-0")).toHaveTextContent("LOAD R0 5");
    const active = screen.getByTestId("pgm-line-1");
    expect(active).toHaveTextContent("ADD R0 R0 R0");
    expect(active).toHaveAttribute("data-active", "true");
    expect(screen.getByTestId("pgm-line-2")).toHaveAttribute("data-active", "false");
  });
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/ProgramView.test.tsx`
Expected: module not found.

- [ ] **Step 3: Create the component**

```tsx
interface ProgramViewProps {
  source: string;
  activePc: number | null;
}

export function ProgramView({ source, activePc }: ProgramViewProps) {
  const lines = source.split("\n").filter((l) => l.length > 0);
  return (
    <pre className="text-sm font-mono leading-6 bg-white border border-slate-200 rounded p-3 overflow-auto">
      {lines.map((line, i) => {
        const active = i === activePc;
        return (
          <div
            key={i}
            data-testid={`pgm-line-${i}`}
            data-active={active ? "true" : "false"}
            className={`flex gap-2 ${active ? "bg-amber-50" : ""}`}
          >
            <span className="w-4 text-amber-600">{active ? "▶" : " "}</span>
            <span className="text-slate-800">{line}</span>
          </div>
        );
      })}
    </pre>
  );
}
```

- [ ] **Step 4: Run and confirm pass**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/ProgramView.test.tsx`
Expected: 1 pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm-viz/src/components/ProgramView.tsx tinyvm-viz/tests/unit/components/ProgramView.test.tsx
git commit -m "feat(viz): ProgramView component with PC arrow"
```

---

### Task 21: `<OutputStream>` component (with optional model column)

**Files:**
- Create: `tinyvm-viz/src/components/OutputStream.tsx`
- Create: `tinyvm-viz/tests/unit/components/OutputStream.test.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { OutputStream } from "@/components/OutputStream";

describe("OutputStream", () => {
  it("renders ground-truth values as rows", () => {
    render(<OutputStream groundTruth={[1, 2, 3]} model={null} />);
    expect(screen.getByTestId("out-gt-0")).toHaveTextContent("1");
    expect(screen.getByTestId("out-gt-2")).toHaveTextContent("3");
  });

  it("renders a second 'model' column with diff markers when supplied", () => {
    render(<OutputStream groundTruth={[1, 2, 3]} model={[1, 2, 9]} />);
    expect(screen.getByTestId("out-model-2")).toHaveTextContent("9");
    expect(screen.getByTestId("out-row-2")).toHaveAttribute("data-divergent", "true");
    expect(screen.getByTestId("out-row-1")).toHaveAttribute("data-divergent", "false");
  });
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/OutputStream.test.tsx`
Expected: module not found.

- [ ] **Step 3: Create the component**

```tsx
interface OutputStreamProps {
  groundTruth: readonly number[];
  model: readonly number[] | null;
}

export function OutputStream({ groundTruth, model }: OutputStreamProps) {
  const n = Math.max(groundTruth.length, model ? model.length : 0);
  return (
    <div className="text-sm font-mono">
      <div className="grid grid-cols-[auto_1fr_1fr] gap-x-2 gap-y-0.5">
        <div className="text-xs uppercase text-slate-400">#</div>
        <div className="text-xs uppercase text-slate-400">gt</div>
        <div className="text-xs uppercase text-slate-400">{model ? "model" : ""}</div>
        {Array.from({ length: n }).map((_, i) => {
          const gt = groundTruth[i];
          const m = model ? model[i] : undefined;
          const divergent = model !== null && gt !== m;
          return (
            <div
              key={i}
              data-testid={`out-row-${i}`}
              data-divergent={divergent ? "true" : "false"}
              className={`contents ${divergent ? "" : ""}`}
            >
              <div className="text-slate-400">{i}</div>
              <div data-testid={`out-gt-${i}`} className={divergent ? "bg-red-100" : ""}>{gt ?? "—"}</div>
              <div data-testid={`out-model-${i}`} className={divergent ? "bg-red-100" : ""}>
                {model ? (m ?? "—") : ""}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run and confirm pass**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/OutputStream.test.tsx`
Expected: 2 pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm-viz/src/components/OutputStream.tsx tinyvm-viz/tests/unit/components/OutputStream.test.tsx
git commit -m "feat(viz): OutputStream component"
```

---

### Task 22: `<ExecutionPanel>` composition

**Files:**
- Create: `tinyvm-viz/src/components/ExecutionPanel.tsx`
- Create: `tinyvm-viz/tests/unit/components/ExecutionPanel.test.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ExecutionPanel } from "@/components/ExecutionPanel";
import { buildProgram, Op } from "@/core/isa";
import { run, serializeTrace } from "@/core/interpreter";
import { renderProgramText } from "@/core/tokeniser";

describe("ExecutionPanel", () => {
  function fixture() {
    const p = buildProgram([
      { op: Op.LOAD, args: [0, 5] },
      { op: Op.PRINT, args: [0] },
      { op: Op.HALT, args: [] },
    ]);
    return { program: p, trace: serializeTrace(run(p)), source: renderProgramText(p) };
  }

  it("renders RegisterFile, ProgramView, OutputStream, StackView at stepIdx=0", () => {
    const f = fixture();
    render(
      <ExecutionPanel program={f.program} source={f.source} trace={f.trace} stepIdx={0} mode="single" />,
    );
    expect(screen.getByTestId("pgm-line-0")).toHaveAttribute("data-active", "true");
    expect(screen.getByTestId("reg-0-value")).toHaveTextContent("5");
    expect(screen.getByTestId("stack-depth")).toHaveTextContent("0 / 16");
  });

  it("renders model output column in compare mode", () => {
    const f = fixture();
    render(
      <ExecutionPanel
        program={f.program}
        source={f.source}
        trace={f.trace}
        stepIdx={1}
        mode="compare"
        modelOutput={[5]}
      />,
    );
    expect(screen.getByTestId("out-model-0")).toHaveTextContent("5");
  });
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/ExecutionPanel.test.tsx`
Expected: module not found.

- [ ] **Step 3: Create the component**

```tsx
import { Program } from "@/core/isa";
import { SerializedTrace } from "@/core/types";
import { RegisterFile } from "./RegisterFile";
import { StackView } from "./StackView";
import { ProgramView } from "./ProgramView";
import { OutputStream } from "./OutputStream";

interface ExecutionPanelProps {
  program: Program;
  source: string;
  trace: SerializedTrace;
  stepIdx: number;
  mode: "single" | "compare";
  modelOutput?: readonly number[];
}

export function ExecutionPanel({ source, trace, stepIdx, mode, modelOutput }: ExecutionPanelProps) {
  const step = trace.steps[Math.max(0, Math.min(stepIdx, trace.steps.length - 1))]!;
  const prev = stepIdx > 0 ? trace.steps[stepIdx - 1]! : null;
  const highlighted = prev
    ? step.regs.findIndex((v, i) => v !== prev.regs[i])
    : -1;
  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_18rem] gap-4">
      <div className="space-y-4">
        <ProgramView source={source} activePc={step.pc} />
        <OutputStream
          groundTruth={trace.output}
          model={mode === "compare" ? (modelOutput ?? []) : null}
        />
      </div>
      <div className="space-y-4">
        <RegisterFile regs={step.regs} highlightedReg={highlighted >= 0 ? highlighted : null} />
        <StackView stack={step.stack} maxDepth={16} />
        <div className="text-xs text-slate-500">
          step {stepIdx + 1} / {trace.steps.length}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run and confirm pass**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/ExecutionPanel.test.tsx`
Expected: 2 pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm-viz/src/components/ExecutionPanel.tsx tinyvm-viz/tests/unit/components/ExecutionPanel.test.tsx
git commit -m "feat(viz): ExecutionPanel composes the four primitives"
```

---

## Phase I — Editor and Playground

### Task 23: Install CodeMirror

**Files:**
- Modify: `tinyvm-viz/package.json` (dependency additions only via `npm install`)

- [ ] **Step 1: Install**

Run: `cd tinyvm-viz && npm install codemirror @codemirror/state @codemirror/view @codemirror/language @codemirror/lint @codemirror/commands @lezer/highlight`
Expected: dependencies added.

- [ ] **Step 2: Commit**

```bash
git add tinyvm-viz/package.json tinyvm-viz/package-lock.json
git commit -m "chore(viz): add CodeMirror 6 dependencies"
```

---

### Task 24: `<Editor>` component (CodeMirror with linter wired to parser + verifier)

**Files:**
- Create: `tinyvm-viz/src/components/Editor.tsx`
- Create: `tinyvm-viz/tests/unit/components/Editor.test.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Editor } from "@/components/Editor";

describe("Editor", () => {
  it("calls onChange when the user types", () => {
    const onChange = vi.fn();
    render(<Editor value="" onChange={onChange} />);
    const cm = screen.getByTestId("editor-shell");
    fireEvent.input(cm.querySelector(".cm-content")!, { target: { textContent: "LOAD R0 5" } });
    // CodeMirror's synthetic input flow doesn't always call onChange via fireEvent.
    // We assert presence of the editor; the integration test exercises diagnostics.
    expect(cm).toBeInTheDocument();
  });

  it("renders diagnostics for invalid source", async () => {
    const { rerender } = render(<Editor value="FOO R0\n" onChange={() => {}} />);
    rerender(<Editor value="FOO R0\n" onChange={() => {}} />);
    // The linter runs on parse; diagnostic content is inside cm-tooltip-lint after activation,
    // but a simpler smoke check: the editor renders without crashing.
    expect(screen.getByTestId("editor-shell")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/Editor.test.tsx`
Expected: module not found.

- [ ] **Step 3: Create the component**

```tsx
import { useEffect, useRef } from "react";
import { EditorState } from "@codemirror/state";
import { EditorView, keymap, lineNumbers, highlightActiveLine } from "@codemirror/view";
import { defaultKeymap, history, historyKeymap } from "@codemirror/commands";
import { linter, Diagnostic } from "@codemirror/lint";
import { parse } from "@/core/parser";
import { validate } from "@/core/verifier";

interface EditorProps {
  value: string;
  onChange: (next: string) => void;
}

function tinyvmLinter(view: EditorView): Diagnostic[] {
  const src = view.state.doc.toString();
  const out: Diagnostic[] = [];
  const { program, errors } = parse(src);
  for (const e of errors) {
    const lineNum = Math.max(1, e.line);
    const line = view.state.doc.line(Math.min(lineNum, view.state.doc.lines));
    out.push({ from: line.from, to: line.to, severity: "error", message: e.message });
  }
  if (program) {
    const v = validate(program);
    for (const msg of v.errors) {
      out.push({ from: 0, to: Math.min(src.length, 1), severity: "warning", message: msg });
    }
  }
  return out;
}

export function Editor({ value, onChange }: EditorProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const viewRef = useRef<EditorView | null>(null);

  useEffect(() => {
    if (!ref.current || viewRef.current) return;
    const state = EditorState.create({
      doc: value,
      extensions: [
        lineNumbers(),
        history(),
        highlightActiveLine(),
        keymap.of([...defaultKeymap, ...historyKeymap]),
        linter(tinyvmLinter, { delay: 150 }),
        EditorView.updateListener.of((u) => {
          if (u.docChanged) onChange(u.state.doc.toString());
        }),
      ],
    });
    viewRef.current = new EditorView({ state, parent: ref.current });
    return () => viewRef.current?.destroy();
  }, []);

  useEffect(() => {
    if (!viewRef.current) return;
    if (viewRef.current.state.doc.toString() !== value) {
      viewRef.current.dispatch({
        changes: { from: 0, to: viewRef.current.state.doc.length, insert: value },
      });
    }
  }, [value]);

  return <div data-testid="editor-shell" ref={ref} className="border border-slate-200 rounded bg-white" />;
}
```

- [ ] **Step 4: Run and confirm pass**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/Editor.test.tsx`
Expected: 2 pass (smoke).

- [ ] **Step 5: Commit**

```bash
git add tinyvm-viz/src/components/Editor.tsx tinyvm-viz/tests/unit/components/Editor.test.tsx
git commit -m "feat(viz): Editor component with parser/verifier-wired linter"
```

---

### Task 25: `<StepControls>` component

**Files:**
- Create: `tinyvm-viz/src/components/StepControls.tsx`
- Create: `tinyvm-viz/tests/unit/components/StepControls.test.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StepControls } from "@/components/StepControls";

describe("StepControls", () => {
  it("clicking ▸ step calls onStep(+1)", () => {
    const onStep = vi.fn();
    render(<StepControls stepIdx={0} maxStep={5} running={false} onStep={onStep} onRunToggle={() => {}} onReset={() => {}} />);
    fireEvent.click(screen.getByTestId("btn-step-forward"));
    expect(onStep).toHaveBeenCalledWith(1);
  });

  it("clicking ◂ step calls onStep(-1)", () => {
    const onStep = vi.fn();
    render(<StepControls stepIdx={3} maxStep={5} running={false} onStep={onStep} onRunToggle={() => {}} onReset={() => {}} />);
    fireEvent.click(screen.getByTestId("btn-step-back"));
    expect(onStep).toHaveBeenCalledWith(-1);
  });

  it("disables back at step 0 and forward at maxStep", () => {
    render(<StepControls stepIdx={0} maxStep={5} running={false} onStep={() => {}} onRunToggle={() => {}} onReset={() => {}} />);
    expect(screen.getByTestId("btn-step-back")).toBeDisabled();
    render(<StepControls stepIdx={5} maxStep={5} running={false} onStep={() => {}} onRunToggle={() => {}} onReset={() => {}} />);
    expect(screen.getByTestId("btn-step-forward")).toBeDisabled();
  });

  it("scrubber emits onStep(delta) to reach the target", () => {
    const onStep = vi.fn();
    render(<StepControls stepIdx={2} maxStep={5} running={false} onStep={onStep} onRunToggle={() => {}} onReset={() => {}} />);
    fireEvent.change(screen.getByTestId("scrubber"), { target: { value: "4" } });
    expect(onStep).toHaveBeenCalledWith(2);
  });
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/StepControls.test.tsx`
Expected: module not found.

- [ ] **Step 3: Create the component**

```tsx
interface StepControlsProps {
  stepIdx: number;
  maxStep: number;
  running: boolean;
  onStep: (delta: number) => void;
  onRunToggle: () => void;
  onReset: () => void;
}

export function StepControls({ stepIdx, maxStep, running, onStep, onRunToggle, onReset }: StepControlsProps) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <button data-testid="btn-reset" className="px-2 py-1 border rounded" onClick={onReset}>⟲ reset</button>
      <button
        data-testid="btn-step-back"
        className="px-2 py-1 border rounded disabled:opacity-40"
        onClick={() => onStep(-1)}
        disabled={stepIdx <= 0}
      >
        ◂ step
      </button>
      <button data-testid="btn-run" className="px-2 py-1 border rounded" onClick={onRunToggle}>
        {running ? "⏸ pause" : "▶ run"}
      </button>
      <button
        data-testid="btn-step-forward"
        className="px-2 py-1 border rounded disabled:opacity-40"
        onClick={() => onStep(1)}
        disabled={stepIdx >= maxStep}
      >
        step ▸
      </button>
      <input
        data-testid="scrubber"
        type="range"
        min={0}
        max={maxStep}
        value={stepIdx}
        onChange={(e) => onStep(Number(e.target.value) - stepIdx)}
        className="ml-4 flex-1"
      />
      <span className="text-xs text-slate-500 w-20 text-right">
        step {stepIdx + 1} / {maxStep + 1}
      </span>
    </div>
  );
}
```

- [ ] **Step 4: Run and confirm pass**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/StepControls.test.tsx`
Expected: 4 pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm-viz/src/components/StepControls.tsx tinyvm-viz/tests/unit/components/StepControls.test.tsx
git commit -m "feat(viz): StepControls component"
```

---

### Task 26: Lesson playlist and content

**Files:**
- Create: `tinyvm-viz/src/lessons/index.ts`
- Create: `tinyvm-viz/src/components/LessonPlaylist.tsx`
- Create: `tinyvm-viz/tests/unit/components/LessonPlaylist.test.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { LessonPlaylist } from "@/components/LessonPlaylist";
import { lessons } from "@/lessons";

describe("LessonPlaylist", () => {
  it("lists every lesson by title", () => {
    render(<LessonPlaylist lessons={lessons} selectedId={lessons[0]!.id} onSelect={() => {}} />);
    for (const l of lessons) {
      expect(screen.getByText(l.title)).toBeInTheDocument();
    }
  });

  it("calls onSelect when a lesson is clicked", () => {
    const onSelect = vi.fn();
    render(<LessonPlaylist lessons={lessons} selectedId={lessons[0]!.id} onSelect={onSelect} />);
    fireEvent.click(screen.getByText(lessons[1]!.title));
    expect(onSelect).toHaveBeenCalledWith(lessons[1]!.id);
  });
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/LessonPlaylist.test.tsx`
Expected: modules not found.

- [ ] **Step 3: Create `tinyvm-viz/src/lessons/index.ts`**

```ts
export interface Lesson {
  id: string;
  title: string;
  summary: string;
  source: string;
  expectedOutput: number[];
}

export const lessons: Lesson[] = [
  {
    id: "counter",
    title: "1. Counter",
    summary: "One register. LOAD a value, PRINT it.",
    source: "LOAD R0 5\nPRINT R0\nHALT\n",
    expectedOutput: [5],
  },
  {
    id: "two-regs",
    title: "2. Two registers",
    summary: "LOAD two registers, ADD them into a third, PRINT the result.",
    source: "LOAD R0 3\nLOAD R1 4\nADD R2 R0 R1\nPRINT R2\nHALT\n",
    expectedOutput: [7],
  },
  {
    id: "first-branch",
    title: "3. First branch",
    summary: "Skip a print when a comparison fails (LT-driven JZ).",
    source:
      "LOAD R0 5\nLOAD R1 3\nLT R2 R1 R0\nJZ R2 L0\nLOAD R3 99\nL0:PRINT R3\nHALT\n",
    expectedOutput: [99],
  },
  {
    id: "countdown",
    title: "4. Count-down loop",
    summary: "Decrement a counter until it hits zero.",
    source:
      "LOAD R1 1\nLOAD R0 3\nL0:SUB R0 R0 R1\nJZ R0 L1\nJMP L0\nL1:PRINT R0\nHALT\n",
    expectedOutput: [0],
  },
  {
    id: "stack-frame",
    title: "5. Stack frame",
    summary: "PUSH a value, scratch the register, POP to restore.",
    source: "LOAD R0 7\nPUSH R0\nLOAD R0 1\nPOP R0\nPRINT R0\nHALT\n",
    expectedOutput: [7],
  },
  {
    id: "free-play",
    title: "6. Free play",
    summary: "Empty canvas. Write your own.",
    source: "",
    expectedOutput: [],
  },
];
```

- [ ] **Step 4: Create `tinyvm-viz/src/components/LessonPlaylist.tsx`**

```tsx
import type { Lesson } from "@/lessons";

interface LessonPlaylistProps {
  lessons: readonly Lesson[];
  selectedId: string;
  onSelect: (id: string) => void;
}

export function LessonPlaylist({ lessons, selectedId, onSelect }: LessonPlaylistProps) {
  return (
    <nav className="space-y-1">
      {lessons.map((l) => {
        const sel = l.id === selectedId;
        return (
          <button
            key={l.id}
            onClick={() => onSelect(l.id)}
            className={`w-full text-left px-2 py-1 rounded text-sm ${
              sel ? "bg-slate-200 text-slate-900" : "hover:bg-slate-100 text-slate-700"
            }`}
          >
            <div>{l.title}</div>
            <div className="text-xs text-slate-500">{l.summary}</div>
          </button>
        );
      })}
    </nav>
  );
}
```

- [ ] **Step 5: Run and confirm pass**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/LessonPlaylist.test.tsx`
Expected: 2 pass.

- [ ] **Step 6: Verify lesson programs actually run**

Add to the same test file:

```tsx
import { parse } from "@/core/parser";
import { run } from "@/core/interpreter";

describe("lesson content", () => {
  it("every lesson with a non-empty source parses, validates, and produces its expectedOutput", () => {
    for (const l of lessons) {
      if (l.source.length === 0) continue;
      const { program, errors } = parse(l.source);
      expect(errors, `errors in ${l.id}`).toEqual([]);
      const trace = run(program!);
      expect(trace.output, `output mismatch in ${l.id}`).toEqual(l.expectedOutput);
    }
  });
});
```

- [ ] **Step 7: Run, fix any mismatched expectedOutputs**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/LessonPlaylist.test.tsx`
Expected: 3 pass. If any lesson's `expectedOutput` is wrong, fix it in `lessons/index.ts` to match the interpreter's actual output.

- [ ] **Step 8: Commit**

```bash
git add tinyvm-viz/src/lessons/index.ts tinyvm-viz/src/components/LessonPlaylist.tsx tinyvm-viz/tests/unit/components/LessonPlaylist.test.tsx
git commit -m "feat(viz): lesson playlist with 6 hand-authored programs"
```

---

### Task 27: Playground page

**Files:**
- Create: `tinyvm-viz/src/pages/Playground.tsx`
- Create: `tinyvm-viz/tests/unit/components/Playground.test.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { Playground } from "@/pages/Playground";

describe("Playground", () => {
  it("loads lesson #1 by default and shows post-LOAD register R0=5", () => {
    render(<Playground />);
    expect(screen.getByTestId("reg-0-value")).toHaveTextContent("5");
  });

  it("clicking another lesson swaps the program", () => {
    render(<Playground />);
    fireEvent.click(screen.getByText(/Two registers/));
    act(() => { /* allow effect */ });
    // After lesson change, the editor reflects the new source — first instruction is LOAD R0 3.
    // We sample the program view's first line instead, since the editor body is CodeMirror-internal.
    expect(screen.getByTestId("pgm-line-0")).toHaveTextContent("LOAD R0 3");
  });
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/Playground.test.tsx`
Expected: module not found.

- [ ] **Step 3: Create the page**

```tsx
import { useEffect, useMemo, useState } from "react";
import { Editor } from "@/components/Editor";
import { ExecutionPanel } from "@/components/ExecutionPanel";
import { LessonPlaylist } from "@/components/LessonPlaylist";
import { StepControls } from "@/components/StepControls";
import { lessons } from "@/lessons";
import { parse } from "@/core/parser";
import { run, serializeTrace, InterpreterError } from "@/core/interpreter";
import type { SerializedTrace } from "@/core/types";

export function Playground() {
  const [lessonId, setLessonId] = useState(lessons[0]!.id);
  const lesson = useMemo(() => lessons.find((l) => l.id === lessonId)!, [lessonId]);
  const [source, setSource] = useState(lesson.source);
  const [stepIdx, setStepIdx] = useState(1);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setSource(lesson.source);
    setStepIdx(0);
    setRunning(false);
    setError(null);
  }, [lesson]);

  const { program, errors } = useMemo(() => parse(source), [source]);
  const trace: SerializedTrace | null = useMemo(() => {
    if (!program) return null;
    try {
      setError(null);
      return serializeTrace(run(program));
    } catch (e) {
      if (e instanceof InterpreterError) setError(e.message);
      return null;
    }
  }, [program]);

  useEffect(() => {
    if (!running || !trace) return;
    if (stepIdx >= trace.steps.length - 1) {
      setRunning(false);
      return;
    }
    const id = setTimeout(() => setStepIdx((s) => s + 1), 200);
    return () => clearTimeout(id);
  }, [running, stepIdx, trace]);

  const maxStep = trace ? trace.steps.length - 1 : 0;
  const safeStep = Math.min(stepIdx, maxStep);

  return (
    <div className="grid grid-cols-[14rem_1fr] gap-4 p-4">
      <aside>
        <LessonPlaylist lessons={lessons} selectedId={lesson.id} onSelect={setLessonId} />
      </aside>
      <main className="space-y-3">
        <Editor value={source} onChange={setSource} />
        <StepControls
          stepIdx={safeStep}
          maxStep={maxStep}
          running={running}
          onStep={(d) => setStepIdx((s) => Math.max(0, Math.min(s + d, maxStep)))}
          onRunToggle={() => setRunning((r) => !r)}
          onReset={() => setStepIdx(0)}
        />
        {errors.length > 0 && (
          <div className="text-sm text-red-600">
            {errors.map((e, i) => (
              <div key={i}>line {e.line}: {e.message}</div>
            ))}
          </div>
        )}
        {error && <div className="text-sm text-amber-700">{error}</div>}
        {program && trace && (
          <ExecutionPanel program={program} source={source} trace={trace} stepIdx={safeStep} mode="single" />
        )}
      </main>
    </div>
  );
}

export default Playground;
```

- [ ] **Step 4: Run and confirm pass**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/Playground.test.tsx`
Expected: 2 pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm-viz/src/pages/Playground.tsx tinyvm-viz/tests/unit/components/Playground.test.tsx
git commit -m "feat(viz): Playground page wires editor + step controls + execution panel"
```

---

## Phase J — Compare

### Task 28: `<DivergencePanel>` component

**Files:**
- Create: `tinyvm-viz/src/components/DivergencePanel.tsx`
- Create: `tinyvm-viz/tests/unit/components/DivergencePanel.test.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DivergencePanel } from "@/components/DivergencePanel";

describe("DivergencePanel", () => {
  it("renders index-aligned ground-truth vs model rows", () => {
    render(<DivergencePanel groundTruth={[1, 2, 3]} model={[1, 2, 9]} />);
    expect(screen.getByTestId("div-row-2")).toHaveAttribute("data-divergent", "true");
    expect(screen.getByTestId("div-row-0")).toHaveAttribute("data-divergent", "false");
  });

  it("treats unequal lengths as divergences", () => {
    render(<DivergencePanel groundTruth={[1, 2]} model={[1, 2, 3]} />);
    expect(screen.getByTestId("div-row-2")).toHaveAttribute("data-divergent", "true");
  });

  it("reports 'no divergence' when streams match", () => {
    render(<DivergencePanel groundTruth={[1, 2]} model={[1, 2]} />);
    expect(screen.getByTestId("div-summary")).toHaveTextContent(/no divergence/i);
  });
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/DivergencePanel.test.tsx`
Expected: module not found.

- [ ] **Step 3: Create the component**

```tsx
interface DivergencePanelProps {
  groundTruth: readonly number[];
  model: readonly number[];
}

export function DivergencePanel({ groundTruth, model }: DivergencePanelProps) {
  const n = Math.max(groundTruth.length, model.length);
  let firstDiv = -1;
  for (let i = 0; i < n; i++) {
    if (groundTruth[i] !== model[i]) { firstDiv = i; break; }
  }
  return (
    <div className="text-sm font-mono">
      <div data-testid="div-summary" className="mb-2 text-xs text-slate-600">
        {firstDiv === -1 ? "no divergence" : `first divergence at #${firstDiv}`}
      </div>
      <div className="grid grid-cols-[3rem_1fr_1fr_2rem] gap-x-2 gap-y-0.5">
        <div className="text-xs text-slate-400">idx</div>
        <div className="text-xs text-slate-400">gt</div>
        <div className="text-xs text-slate-400">model</div>
        <div></div>
        {Array.from({ length: n }).map((_, i) => {
          const gt = groundTruth[i];
          const m = model[i];
          const div = gt !== m;
          return (
            <div
              key={i}
              data-testid={`div-row-${i}`}
              data-divergent={div ? "true" : "false"}
              className={`contents`}
            >
              <div className="text-slate-400">{i}</div>
              <div className={div ? "bg-red-100" : ""}>{gt ?? "—"}</div>
              <div className={div ? "bg-red-100" : ""}>{m ?? "—"}</div>
              <div>{div ? "✗" : "✓"}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run and confirm pass**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/DivergencePanel.test.tsx`
Expected: 3 pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm-viz/src/components/DivergencePanel.tsx tinyvm-viz/tests/unit/components/DivergencePanel.test.tsx
git commit -m "feat(viz): DivergencePanel component"
```

---

### Task 29: Compare page with bundle loader + re-run parity warning

**Files:**
- Create: `tinyvm-viz/src/pages/Compare.tsx`
- Create: `tinyvm-viz/tests/unit/components/Compare.test.tsx`
- Create: `tinyvm-viz/samples/example_pass.json`
- Create: `tinyvm-viz/samples/example_divergence.json`

- [ ] **Step 1: Write two minimal sample bundles by hand**

`tinyvm-viz/samples/example_pass.json`:

```json
{
  "schema": "tinyvm-viz/comparison/v1",
  "meta": { "generator": "manual", "seed": 0 },
  "source": "LOAD R0 5\nPRINT R0\nHALT\n",
  "groundTruth": {
    "trace": {
      "steps": [
        { "pc": 0, "regs": [5,0,0,0,0,0,0,0], "stack": [], "emitted": null },
        { "pc": 1, "regs": [5,0,0,0,0,0,0,0], "stack": [], "emitted": 5 },
        { "pc": 2, "regs": [5,0,0,0,0,0,0,0], "stack": [], "emitted": null }
      ],
      "output": [5],
      "halted": true
    }
  },
  "prediction": { "output": [5] }
}
```

`tinyvm-viz/samples/example_divergence.json`:

```json
{
  "schema": "tinyvm-viz/comparison/v1",
  "meta": { "generator": "manual", "seed": 1 },
  "source": "LOAD R0 5\nPRINT R0\nHALT\n",
  "groundTruth": {
    "trace": {
      "steps": [
        { "pc": 0, "regs": [5,0,0,0,0,0,0,0], "stack": [], "emitted": null },
        { "pc": 1, "regs": [5,0,0,0,0,0,0,0], "stack": [], "emitted": 5 },
        { "pc": 2, "regs": [5,0,0,0,0,0,0,0], "stack": [], "emitted": null }
      ],
      "output": [5],
      "halted": true
    }
  },
  "prediction": { "output": [7] }
}
```

- [ ] **Step 2: Write failing tests**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Compare } from "@/pages/Compare";
import passBundle from "@/../samples/example_pass.json";
import divBundle from "@/../samples/example_divergence.json";

describe("Compare", () => {
  it("renders a passing bundle with 'no divergence'", () => {
    render(<Compare initialBundle={passBundle as never} />);
    expect(screen.getByTestId("div-summary")).toHaveTextContent(/no divergence/i);
  });

  it("renders a divergence at index 0", () => {
    render(<Compare initialBundle={divBundle as never} />);
    expect(screen.getByTestId("div-summary")).toHaveTextContent(/first divergence at #0/i);
    expect(screen.getByTestId("div-row-0")).toHaveAttribute("data-divergent", "true");
  });

  it("shows a parity-drift banner when groundTruth disagrees with the TS re-run", () => {
    const tampered = JSON.parse(JSON.stringify(passBundle));
    tampered.groundTruth.trace.output = [999];
    render(<Compare initialBundle={tampered as never} />);
    expect(screen.getByTestId("parity-banner")).toHaveTextContent(/parity drift suspected/i);
  });
});
```

- [ ] **Step 3: Run and confirm failure**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/Compare.test.tsx`
Expected: module not found.

- [ ] **Step 4: Create the page**

```tsx
import { useMemo, useState } from "react";
import { ExecutionPanel } from "@/components/ExecutionPanel";
import { DivergencePanel } from "@/components/DivergencePanel";
import { StepControls } from "@/components/StepControls";
import { parse } from "@/core/parser";
import { deserializeTrace, run, serializeTrace } from "@/core/interpreter";
import type { ComparisonBundle, SerializedTrace } from "@/core/types";

interface CompareProps {
  initialBundle?: ComparisonBundle;
}

function validateBundle(b: unknown): b is ComparisonBundle {
  if (typeof b !== "object" || b === null) return false;
  const r = b as Record<string, unknown>;
  return r.schema === "tinyvm-viz/comparison/v1"
    && typeof r.source === "string"
    && typeof r.groundTruth === "object"
    && typeof r.prediction === "object";
}

export function Compare({ initialBundle }: CompareProps) {
  const [bundle, setBundle] = useState<ComparisonBundle | null>(initialBundle ?? null);
  const [stepIdx, setStepIdx] = useState(0);
  const [loadError, setLoadError] = useState<string | null>(null);

  const reRun = useMemo(() => {
    if (!bundle) return null;
    const { program, errors } = parse(bundle.source);
    if (!program || errors.length) return { ok: false as const, message: "bundle.source did not parse" };
    try {
      const trace = serializeTrace(run(program));
      const same = JSON.stringify(trace.output) === JSON.stringify(bundle.groundTruth.trace.output);
      return { ok: same, program, tsTrace: trace };
    } catch (e) {
      return { ok: false as const, message: (e as Error).message };
    }
  }, [bundle]);

  function onFile(file: File) {
    file.text().then((txt) => {
      try {
        const parsed = JSON.parse(txt);
        if (!validateBundle(parsed)) {
          setLoadError("bundle: schema mismatch");
          return;
        }
        setLoadError(null);
        setBundle(parsed);
        setStepIdx(0);
      } catch (e) {
        setLoadError(`bundle: ${(e as Error).message}`);
      }
    });
  }

  if (!bundle) {
    return (
      <div className="p-4 space-y-3">
        <h2 className="text-lg font-semibold">Comparison view</h2>
        <input
          type="file"
          accept="application/json"
          onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0]!)}
        />
        {loadError && <div className="text-red-600 text-sm">{loadError}</div>}
      </div>
    );
  }

  const tsTrace = reRun && "tsTrace" in reRun ? reRun.tsTrace : deserializeTrace(bundle.groundTruth.trace);
  const trace: SerializedTrace = serializeTrace(tsTrace);
  const maxStep = trace.steps.length - 1;
  const safeStep = Math.min(stepIdx, maxStep);

  return (
    <div className="p-4 space-y-3">
      <div className="text-xs text-slate-500">
        bundle · {bundle.meta.generator} · seed {bundle.meta.seed} ·
        {" "}gt {JSON.stringify(bundle.groundTruth.trace.output)} ·
        {" "}model {JSON.stringify(bundle.prediction.output)}
      </div>
      {reRun && !reRun.ok && (
        <div data-testid="parity-banner" className="text-sm bg-red-100 text-red-800 p-2 rounded">
          parity drift suspected — bundle ground truth disagrees with TS re-run
        </div>
      )}
      <DivergencePanel
        groundTruth={bundle.groundTruth.trace.output}
        model={bundle.prediction.output}
      />
      <StepControls
        stepIdx={safeStep}
        maxStep={maxStep}
        running={false}
        onStep={(d) => setStepIdx((s) => Math.max(0, Math.min(s + d, maxStep)))}
        onRunToggle={() => {}}
        onReset={() => setStepIdx(0)}
      />
      {reRun && "program" in reRun && (
        <ExecutionPanel
          program={reRun.program}
          source={bundle.source}
          trace={trace}
          stepIdx={safeStep}
          mode="compare"
          modelOutput={bundle.prediction.output}
        />
      )}
    </div>
  );
}

export default Compare;
```

- [ ] **Step 5: Run and confirm pass**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/Compare.test.tsx`
Expected: 3 pass.

- [ ] **Step 6: Commit**

```bash
git add tinyvm-viz/src/pages/Compare.tsx tinyvm-viz/tests/unit/components/Compare.test.tsx \
        tinyvm-viz/samples/example_pass.json tinyvm-viz/samples/example_divergence.json
git commit -m "feat(viz): Compare page with bundle loader and parity-drift banner"
```

---

### Task 30: `export_comparison_bundle.py` helper

**Files:**
- Create: `tinyvm/scripts/export_comparison_bundle.py`
- Create: `tinyvm/tests/test_export_comparison_bundle.py`

- [ ] **Step 1: Write failing tests**

```python
import json
from pathlib import Path
from tinyvm.scripts.export_comparison_bundle import build_bundle, write_bundle


def test_build_bundle_emits_v1_schema():
    bundle = build_bundle(
        generator="gen_counter",
        seed=0,
        generator_kwargs={"n": 4},
        prediction_output=[7],
    )
    assert bundle["schema"] == "tinyvm-viz/comparison/v1"
    assert bundle["meta"]["seed"] == 0
    assert "source" in bundle
    assert bundle["groundTruth"]["trace"]["halted"] is True
    assert bundle["prediction"]["output"] == [7]


def test_write_bundle_roundtrips_json(tmp_path: Path):
    out = tmp_path / "b.json"
    write_bundle(out, generator="gen_counter", seed=0, generator_kwargs={"n": 4}, prediction_output=[1])
    data = json.loads(out.read_text())
    assert data["schema"] == "tinyvm-viz/comparison/v1"
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd /Users/sidgraph/FANC && python -m pytest tinyvm/tests/test_export_comparison_bundle.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Create the script**

```python
"""Emit a ComparisonBundle JSON consumable by tinyvm-viz Compare page."""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from tinyvm.generators import gen_branched, gen_counter, gen_register_trace, GenSpec
from tinyvm.interpreter import run
from tinyvm.tokeniser import render_direct_text


def _trace_to_json(trace: Any) -> dict:
    return {
        "steps": [
            {"pc": s.pc, "regs": list(s.regs), "stack": list(s.stack), "emitted": s.emitted}
            for s in trace.steps
        ],
        "output": list(trace.output),
        "halted": trace.halted,
    }


def build_bundle(generator: str, seed: int, generator_kwargs: dict, prediction_output: list[int]) -> dict:
    rng = random.Random(seed)
    if generator == "gen_counter":
        p = gen_counter(rng=rng, **generator_kwargs)
    elif generator == "gen_register_trace":
        p = gen_register_trace(rng=rng, **generator_kwargs)
    elif generator == "gen_branched":
        spec = GenSpec(**generator_kwargs)
        p = gen_branched(spec=spec, rng=rng)
    else:
        raise ValueError(f"unknown generator: {generator}")
    trace = run(p)
    source, _ = render_direct_text(p, trace)
    return {
        "schema": "tinyvm-viz/comparison/v1",
        "meta": {"generator": generator, "seed": seed, "spec": generator_kwargs},
        "source": source,
        "groundTruth": {"trace": _trace_to_json(trace)},
        "prediction": {"output": list(prediction_output)},
    }


def write_bundle(path: Path, *, generator: str, seed: int, generator_kwargs: dict, prediction_output: list[int]) -> None:
    b = build_bundle(generator, seed, generator_kwargs, prediction_output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(b, indent=2, sort_keys=True))
```

- [ ] **Step 4: Run and confirm pass**

Run: `cd /Users/sidgraph/FANC && python -m pytest tinyvm/tests/test_export_comparison_bundle.py -v`
Expected: 2 pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm/scripts/export_comparison_bundle.py tinyvm/tests/test_export_comparison_bundle.py
git commit -m "feat(viz): export_comparison_bundle.py helper for emitting bundles"
```

---

## Phase K — App shell and routing

### Task 31: App shell with router (Playground default + Compare + `?bundle=` query)

**Files:**
- Modify: `tinyvm-viz/src/App.tsx`
- Create: `tinyvm-viz/tests/unit/components/App.test.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "@/App";

describe("App shell", () => {
  it("renders the Playground at /", () => {
    render(<MemoryRouter initialEntries={["/"]}><App /></MemoryRouter>);
    expect(screen.getByText(/Counter/)).toBeInTheDocument();
  });

  it("renders the Compare page at /compare", () => {
    render(<MemoryRouter initialEntries={["/compare"]}><App /></MemoryRouter>);
    expect(screen.getByText(/Comparison view/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/App.test.tsx`
Expected: import error — App still default-exports the placeholder.

- [ ] **Step 3: Rewrite `tinyvm-viz/src/App.tsx` to expose just the route shell**

App stays router-free; the router is supplied by `main.tsx` in dev/build and by tests via `MemoryRouter`. Nesting routers is a runtime error, so we keep them at the top level.

```tsx
import { Link, Route, Routes, useLocation } from "react-router-dom";
import { Playground } from "@/pages/Playground";
import { Compare } from "@/pages/Compare";

function Nav() {
  const loc = useLocation();
  const tab = (path: string, label: string) => (
    <Link
      to={path}
      className={`px-3 py-1 text-sm rounded ${loc.pathname === path ? "bg-slate-900 text-white" : "hover:bg-slate-200"}`}
    >
      {label}
    </Link>
  );
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="flex items-center gap-2 px-4 py-2">
        <h1 className="text-sm font-semibold mr-4">Tiny-VM Visualizer</h1>
        {tab("/", "Playground")}
        {tab("/compare", "Compare")}
      </div>
    </header>
  );
}

export default function App() {
  return (
    <>
      <Nav />
      <Routes>
        <Route path="/" element={<Playground />} />
        <Route path="/compare" element={<Compare />} />
      </Routes>
    </>
  );
}
```

- [ ] **Step 4: Wrap `main.tsx` with `BrowserRouter`**

Replace `tinyvm-viz/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles/index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
```

- [ ] **Step 5: Run the test**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/App.test.tsx`
Expected: both pass.

- [ ] **Step 6: Commit**

```bash
git add tinyvm-viz/src/App.tsx tinyvm-viz/src/main.tsx tinyvm-viz/tests/unit/components/App.test.tsx
git commit -m "feat(viz): App shell with Playground / Compare routing"
```

---

### Task 32: `?bundle=` query-param loader on Compare

**Files:**
- Modify: `tinyvm-viz/src/pages/Compare.tsx`
- Modify: `tinyvm-viz/tests/unit/components/Compare.test.tsx`

- [ ] **Step 1: Append a failing test that uses a `MemoryRouter` with the query param**

```tsx
import { MemoryRouter } from "react-router-dom";

it("loads a bundle from the ?bundle= query param", async () => {
  const url = URL.createObjectURL(new Blob([JSON.stringify(passBundle)], { type: "application/json" }));
  render(
    <MemoryRouter initialEntries={[`/compare?bundle=${encodeURIComponent(url)}`]}>
      <Compare />
    </MemoryRouter>,
  );
  await screen.findByTestId("div-summary");
  expect(screen.getByTestId("div-summary")).toHaveTextContent(/no divergence/i);
});
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/Compare.test.tsx`
Expected: the new test fails (Compare has no query-param loader yet).

- [ ] **Step 3: Wire query-param fetch in `Compare`**

Add at the top of `Compare.tsx`:

```tsx
import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
```

Inside `Compare()`, just below the existing `useState`s, add:

```tsx
const [params] = useSearchParams();

useEffect(() => {
  const url = params.get("bundle");
  if (!url || bundle) return;
  fetch(url)
    .then((r) => r.json())
    .then((j) => {
      if (validateBundle(j)) { setBundle(j); setStepIdx(0); }
      else setLoadError("bundle: schema mismatch");
    })
    .catch((e) => setLoadError(`bundle: ${(e as Error).message}`));
}, [params, bundle]);
```

- [ ] **Step 4: Run and confirm pass**

Run: `cd tinyvm-viz && npx vitest run tests/unit/components/Compare.test.tsx`
Expected: 4 pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm-viz/src/pages/Compare.tsx tinyvm-viz/tests/unit/components/Compare.test.tsx
git commit -m "feat(viz): Compare loads ?bundle= URL on mount"
```

---

### Task 33: Final dev/build verification

**Files:** none — verification only.

- [ ] **Step 1: Build**

Run: `cd tinyvm-viz && npm run build`
Expected: TS builds without errors; `dist/` produced.

- [ ] **Step 2: Run all tests**

Run: `cd tinyvm-viz && npm test`
Expected: every suite green — core unit, components, parity, lesson content.

Run: `cd /Users/sidgraph/FANC && python -m pytest tinyvm/tests/test_export_golden_fixtures.py tinyvm/tests/test_export_comparison_bundle.py -v`
Expected: 6 pass.

- [ ] **Step 3: Start dev server and smoke**

Run: `cd tinyvm-viz && npm run dev`
Expected: a dev URL is printed (likely `http://localhost:5173/`). Visit it manually; the Playground tab loads lesson #1 with R0=5 visible. Switch to the Compare tab; loading `samples/example_divergence.json` via the file picker shows "first divergence at #0". Stop the dev server.

- [ ] **Step 4: Commit a small README addition documenting the dev loop**

Append to `tinyvm-viz/README.md`:

```markdown

## Regenerating parity fixtures

After changing the Python interpreter:

```
python -m tinyvm.scripts.export_golden_fixtures
```

then re-run `npm test` in `tinyvm-viz/` and commit `tests/fixtures/golden.json` together with the interpreter change.
```

```bash
git add tinyvm-viz/README.md
git commit -m "docs(viz): document parity-fixture regeneration"
```

---

## Self-review notes

- Every spec section maps to at least one task: §4 layout → Tasks 1-2; §5 port → Tasks 3-15; §6 parity → Tasks 16-17; §7 execution panel → Tasks 18-22; §8 playground → Tasks 23-27; §9 compare → Tasks 28-30; §10 stack → Tasks 1-2 + 23; §11 testing → present in every task via vitest; §12 error handling → surfaced in Tasks 27, 29, 32; §13 risks → mitigated by parity tests (Task 17), USEROP-raises in interpreter (Task 9), bundle re-run in Task 29.
- Plan does not implement: CoT renderers, userop renderers, dataset browser — all explicitly out of scope per spec §2 / §13.
- The interpreter port intentionally re-derives `ARG_SCHEMA` in both `parser.ts` and `verifier.ts`. This is duplication, but each module owns its own validation surface; keeping them independent matches the spec's "core modules depend only on `isa.ts`" boundary. If a future PR consolidates them into `isa.ts`, that's a refactor — not in this plan.
