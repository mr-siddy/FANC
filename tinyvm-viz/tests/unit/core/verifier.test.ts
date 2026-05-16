import { describe, it, expect } from "vitest";
import { scoreOutput, validate } from "@/core/verifier";
import { buildProgram, Op } from "@/core/isa";

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
