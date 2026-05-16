import { describe, it, expect } from "vitest";
import { renderProgramText } from "@/core/tokeniser";
import { buildProgram, Op } from "@/core/isa";
import { parse } from "@/core/parser";

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
