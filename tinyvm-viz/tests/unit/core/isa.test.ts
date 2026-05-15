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
