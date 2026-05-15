import { DEFAULT_STEP_CAP, NUM_REGS, Op, Program, STACK_DEPTH, VAL_MAX, VAL_MIN, isUserop } from "./isa";

export class InterpreterError extends Error {}

export interface StepRecord {
  pc: number;
  regs: number[];
  stack: number[];
  emitted: number | null;
}

export interface ExecutionTrace {
  steps: StepRecord[];
  output: number[];
  halted: boolean;
}

function clamp(v: number): number {
  if (v < VAL_MIN) return VAL_MIN;
  if (v > VAL_MAX) return VAL_MAX;
  return v;
}

function truncDiv(a: number, b: number): number {
  const q = Math.floor(Math.abs(a) / Math.abs(b));
  return (a < 0) !== (b < 0) ? -q : q;
}

export function run(program: Program, stepCap: number | null = DEFAULT_STEP_CAP): ExecutionTrace {
  const regs = new Array<number>(NUM_REGS).fill(0);
  const stack: number[] = [];
  const steps: StepRecord[] = [];
  const output: number[] = [];
  let pc = 0;
  let stepCount = 0;
  const n = program.instructions.length;

  while (pc < n) {
    if (stepCap !== null && stepCount >= stepCap) {
      throw new InterpreterError(`step cap ${stepCap} exceeded`);
    }
    stepCount += 1;
    const executedPc = pc;
    const inst = program.instructions[pc]!;
    let nextPc = pc + 1;
    let emitted: number | null = null;

    switch (inst.op) {
      case Op.LOAD: {
        const [i, lit] = inst.args as [number, number];
        regs[i] = clamp(lit);
        break;
      }
      case Op.MOV: {
        const [i, j] = inst.args as [number, number];
        regs[i] = regs[j]!;
        break;
      }
      case Op.ADD: {
        const [i, j, k] = inst.args as [number, number, number];
        regs[i] = clamp(regs[j]! + regs[k]!);
        break;
      }
      case Op.SUB: {
        const [i, j, k] = inst.args as [number, number, number];
        regs[i] = clamp(regs[j]! - regs[k]!);
        break;
      }
      case Op.MUL: {
        const [i, j, k] = inst.args as [number, number, number];
        regs[i] = clamp(regs[j]! * regs[k]!);
        break;
      }
      case Op.DIV: {
        const [i, j, k] = inst.args as [number, number, number];
        const divisor = regs[k]!;
        regs[i] = divisor === 0 ? 0 : clamp(truncDiv(regs[j]!, divisor));
        break;
      }
      case Op.NEG: {
        const [i, j] = inst.args as [number, number];
        regs[i] = clamp(-regs[j]!);
        break;
      }
      case Op.JZ: {
        const [i] = inst.args as [number];
        if (regs[i]! === 0) {
          const t = inst.target!;
          nextPc = program.labelIndex.get(t)!;
        }
        break;
      }
      case Op.JMP: {
        const t = inst.target!;
        nextPc = program.labelIndex.get(t)!;
        break;
      }
      case Op.NOP:
        break;
      case Op.EQ: {
        const [i, j, k] = inst.args as [number, number, number];
        regs[i] = regs[j]! === regs[k]! ? 1 : 0;
        break;
      }
      case Op.LT: {
        const [i, j, k] = inst.args as [number, number, number];
        regs[i] = regs[j]! < regs[k]! ? 1 : 0;
        break;
      }
      case Op.HALT: {
        steps.push({ pc: executedPc, regs: [...regs], stack: [...stack], emitted: null });
        return { steps, output, halted: true };
      }
      default:
        throw new InterpreterError(`unhandled op in this task: ${Op[inst.op]}`);
    }

    steps.push({ pc: executedPc, regs: [...regs], stack: [...stack], emitted });
    pc = nextPc;
  }

  return { steps, output, halted: true };
}
