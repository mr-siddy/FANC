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
