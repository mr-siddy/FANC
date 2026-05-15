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
