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
      { op: Op.ADD, args: [2, 0, 1] },
      { op: Op.SUB, args: [3, 1, 0] },
      { op: Op.MUL, args: [4, 0, 1] },
      { op: Op.NEG, args: [5, 0] },
      { op: Op.HALT, args: [] },
    ]);
    const regs = run(p).steps.at(-1)!.regs;
    expect([regs[2], regs[3], regs[4], regs[5]]).toEqual([7, 1, 12, -3]);
  });

  it("clamps to [VAL_MIN, VAL_MAX]", () => {
    const p = buildProgram([
      { op: Op.LOAD, args: [0, 100] },
      { op: Op.MUL, args: [0, 0, 0] },
      { op: Op.HALT, args: [] },
    ]);
    expect(run(p).steps.at(-1)!.regs[0]).toBe(1023);
  });

  it("DIV by 0 returns 0", () => {
    const p = buildProgram([
      { op: Op.LOAD, args: [0, 10] },
      { op: Op.DIV, args: [1, 0, 2] },
      { op: Op.HALT, args: [] },
    ]);
    expect(run(p).steps.at(-1)!.regs[1]).toBe(0);
  });

  it("DIV truncates toward zero", () => {
    const p = buildProgram([
      { op: Op.LOAD, args: [0, -7] },
      { op: Op.LOAD, args: [1, 2] },
      { op: Op.DIV, args: [2, 0, 1] },
      { op: Op.HALT, args: [] },
    ]);
    expect(run(p).steps.at(-1)!.regs[2]).toBe(-3);
  });
});

describe("interpreter: comparisons", () => {
  it("EQ → 1 if equal else 0", () => {
    const p = buildProgram([
      { op: Op.LOAD, args: [0, 4] },
      { op: Op.LOAD, args: [1, 4] },
      { op: Op.LOAD, args: [2, 5] },
      { op: Op.EQ, args: [3, 0, 1] },
      { op: Op.EQ, args: [4, 0, 2] },
      { op: Op.HALT, args: [] },
    ]);
    const regs = run(p).steps.at(-1)!.regs;
    expect([regs[3], regs[4]]).toEqual([1, 0]);
  });

  it("LT is strict", () => {
    const p = buildProgram([
      { op: Op.LOAD, args: [0, 2] },
      { op: Op.LOAD, args: [1, 5] },
      { op: Op.LT, args: [2, 0, 1] },
      { op: Op.LT, args: [3, 1, 0] },
      { op: Op.LT, args: [4, 0, 0] },
      { op: Op.HALT, args: [] },
    ]);
    const regs = run(p).steps.at(-1)!.regs;
    expect([regs[2], regs[3], regs[4]]).toEqual([1, 0, 0]);
  });
});

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
    const p = buildProgram([{ op: Op.LOAD, args: [0, 5] }]);
    const trace = run(p);
    expect(trace.halted).toBe(true);
    expect(trace.steps.at(-1)!.regs[0]).toBe(5);
  });
});
