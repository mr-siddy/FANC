import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { parse } from "@/core/parser";
import { run, serializeTrace } from "@/core/interpreter";

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

      const tsInsts = program!.instructions.map((i) => ({
        op: i.op,
        args: i.args,
        label: i.label ?? null,
        target: i.target ?? null,
      }));
      expect(tsInsts).toEqual(f.program_ir.instructions);

      const trace = serializeTrace(run(program!));
      expect(trace).toEqual(f.expected_trace);
    });
  }
});
