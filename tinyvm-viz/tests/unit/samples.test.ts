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
      const b = raw as unknown as { source: string; groundTruth: { trace: { output: number[]; halted: boolean } } };
      const { program, errors } = parse(b.source);
      expect(errors, `parse errors in ${filename}`).toEqual([]);
      if (b.groundTruth.trace.halted) {
        const trace = run(program!);
        expect(trace.output, `output mismatch in ${filename}`).toEqual(b.groundTruth.trace.output);
      }
    });
  }
});
