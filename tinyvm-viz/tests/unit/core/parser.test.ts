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
