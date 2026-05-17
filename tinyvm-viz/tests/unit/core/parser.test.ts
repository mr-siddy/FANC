import { describe, it, expect } from "vitest";
import { parse } from "@/core/parser";
import { Op } from "@/core/isa";
import { run } from "@/core/interpreter";

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

describe("parser: lineToInstIdx", () => {
  it("maps a clean multi-line program one-to-one", () => {
    const src = "LOAD R0 5\nADD R0 R0 R0\nPRINT R0\nHALT\n";
    const { program, errors, lineToInstIdx } = parse(src);
    expect(errors).toEqual([]);
    expect(program!.instructions).toHaveLength(4);
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
