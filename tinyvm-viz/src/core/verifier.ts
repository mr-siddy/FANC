export function scoreOutput(predicted: number[], target: number[]): number {
  if (predicted.length !== target.length) return 0;
  for (let i = 0; i < predicted.length; i++) {
    if (predicted[i] !== target[i]) return 0;
  }
  return 1;
}

import { NUM_REGS, Op, Program, STACK_DEPTH } from "./isa";
import type { Instruction } from "./isa";

const ARG_SCHEMA: Record<Op, { regs: number; lits: number; hasTarget: boolean }> = {
  [Op.LOAD]: { regs: 1, lits: 1, hasTarget: false },
  [Op.MOV]: { regs: 2, lits: 0, hasTarget: false },
  [Op.ADD]: { regs: 3, lits: 0, hasTarget: false },
  [Op.SUB]: { regs: 3, lits: 0, hasTarget: false },
  [Op.MUL]: { regs: 3, lits: 0, hasTarget: false },
  [Op.DIV]: { regs: 3, lits: 0, hasTarget: false },
  [Op.NEG]: { regs: 2, lits: 0, hasTarget: false },
  [Op.EQ]: { regs: 3, lits: 0, hasTarget: false },
  [Op.LT]: { regs: 3, lits: 0, hasTarget: false },
  [Op.JZ]: { regs: 1, lits: 0, hasTarget: true },
  [Op.JMP]: { regs: 0, lits: 0, hasTarget: true },
  [Op.PUSH]: { regs: 1, lits: 0, hasTarget: false },
  [Op.POP]: { regs: 1, lits: 0, hasTarget: false },
  [Op.PRINT]: { regs: 1, lits: 0, hasTarget: false },
  [Op.NOP]: { regs: 0, lits: 0, hasTarget: false },
  [Op.HALT]: { regs: 0, lits: 0, hasTarget: false },
  [Op.USEROP_0]: { regs: 2, lits: 0, hasTarget: false },
  [Op.USEROP_1]: { regs: 3, lits: 0, hasTarget: false },
  [Op.USEROP_2]: { regs: 2, lits: 0, hasTarget: false },
  [Op.USEROP_3]: { regs: 3, lits: 0, hasTarget: false },
  [Op.USEROP_4]: { regs: 2, lits: 0, hasTarget: false },
};

const WRITES_ONE_REG = new Set([Op.LOAD, Op.MOV, Op.ADD, Op.SUB, Op.MUL, Op.DIV, Op.NEG, Op.EQ, Op.LT, Op.POP]);

export interface ValidationResult {
  ok: boolean;
  errors: string[];
}

function successors(program: Program, idx: number): number[] {
  const inst = program.instructions[idx]!;
  const n = program.instructions.length;
  if (inst.op === Op.HALT) return [];
  if (inst.op === Op.JMP) return [program.labelIndex.get(inst.target!)!];
  if (inst.op === Op.JZ) {
    const out: number[] = [];
    if (idx + 1 < n) out.push(idx + 1);
    out.push(program.labelIndex.get(inst.target!)!);
    return out;
  }
  return idx + 1 < n ? [idx + 1] : [];
}

function checkArity(program: Program, errors: string[]): void {
  for (let i = 0; i < program.instructions.length; i++) {
    const inst = program.instructions[i]!;
    const s = ARG_SCHEMA[inst.op];
    const expected = s.regs + s.lits;
    if (inst.args.length !== expected) {
      errors.push(`${Op[inst.op]} at idx ${i} expects ${expected} args, got ${inst.args.length}`);
    }
    if (s.hasTarget && inst.target === undefined) {
      errors.push(`${Op[inst.op]} at idx ${i} requires target label`);
    }
  }
}

function checkLabelTargets(program: Program, errors: string[]): void {
  for (let i = 0; i < program.instructions.length; i++) {
    const inst = program.instructions[i]!;
    if (inst.target !== undefined && !program.labelIndex.has(inst.target)) {
      errors.push(`unknown label target: ${inst.target}`);
    }
  }
}

function writesOf(inst: Instruction): Set<number> {
  return WRITES_ONE_REG.has(inst.op) ? new Set([inst.args[0]!]) : new Set();
}

function checkPrintPredecessors(program: Program, errors: string[]): void {
  const n = program.instructions.length;
  if (n === 0) return;
  const UNIVERSE = new Set<number>();
  for (let r = 0; r < NUM_REGS; r++) UNIVERSE.add(r);
  const writtenIn: Set<number>[] = Array.from({ length: n }, () => new Set(UNIVERSE));
  writtenIn[0] = new Set();
  const preds: number[][] = Array.from({ length: n }, () => []);
  for (let i = 0; i < n; i++) {
    for (const j of successors(program, i)) preds[j]!.push(i);
  }
  let changed = true;
  while (changed) {
    changed = false;
    for (let i = 1; i < n; i++) {
      const p = preds[i]!;
      let next: Set<number>;
      if (p.length === 0) {
        next = new Set();
      } else {
        const first = new Set([...writtenIn[p[0]!]!, ...writesOf(program.instructions[p[0]!]!)]);
        next = first;
        for (let k = 1; k < p.length; k++) {
          const s = new Set([...writtenIn[p[k]!]!, ...writesOf(program.instructions[p[k]!]!)]);
          next = new Set([...next].filter((x) => s.has(x)));
        }
      }
      if (next.size !== writtenIn[i]!.size || ![...next].every((x) => writtenIn[i]!.has(x))) {
        writtenIn[i] = next;
        changed = true;
      }
    }
  }
  for (let i = 0; i < n; i++) {
    const inst = program.instructions[i]!;
    if (inst.op === Op.PRINT && !writtenIn[i]!.has(inst.args[0]!)) {
      errors.push(`PRINT R${inst.args[0]} at idx ${i} not preceded by write on all paths`);
    }
  }
}

function checkStackBalance(program: Program, errors: string[]): void {
  const n = program.instructions.length;
  if (n === 0) return;

  const delta = (op: Op): number => (op === Op.PUSH ? 1 : op === Op.POP ? -1 : 0);

  // Idx-0 check: if the first instruction is POP, depth=0+delta(-1)=-1 → underflow.
  const d0After = 0 + delta(program.instructions[0]!.op);
  if (d0After < 0) {
    errors.push(`POP at idx 0 underflows`);
    return;
  }
  if (d0After > STACK_DEPTH) {
    errors.push(`PUSH at idx 0 overflows (depth ${d0After} > ${STACK_DEPTH})`);
    return;
  }

  const depthIn: (number | null)[] = new Array(n).fill(null);
  depthIn[0] = 0;
  const preds: number[][] = Array.from({ length: n }, () => []);
  for (let i = 0; i < n; i++) {
    for (const j of successors(program, i)) preds[j]!.push(i);
  }
  let changed = true;
  while (changed) {
    changed = false;
    for (let i = 1; i < n; i++) {
      const p = preds[i]!;
      if (p.length === 0) continue;
      let merged: number | null = null;
      for (const pi of p) {
        if (depthIn[pi] === null) continue;
        const d = depthIn[pi]! + delta(program.instructions[pi]!.op);
        if (d < 0) { errors.push(`POP at idx ${pi} underflows`); return; }
        if (d > STACK_DEPTH) { errors.push(`PUSH at idx ${pi} overflows (depth ${d} > ${STACK_DEPTH})`); return; }
        const dAfter = d + delta(program.instructions[i]!.op);
        if (dAfter < 0) { errors.push(`POP at idx ${i} underflows`); return; }
        if (dAfter > STACK_DEPTH) { errors.push(`PUSH at idx ${i} overflows (depth ${dAfter} > ${STACK_DEPTH})`); return; }
        if (merged === null) merged = d;
        else if (merged !== d) { errors.push(`stack depth at idx ${i} not balanced across paths: ${merged} vs ${d}`); return; }
      }
      if (merged !== null && depthIn[i] !== merged) {
        depthIn[i] = merged;
        changed = true;
      }
    }
  }
}

export function validate(program: Program): ValidationResult {
  const errors: string[] = [];
  checkArity(program, errors);
  if (errors.length === 0) checkLabelTargets(program, errors);
  if (errors.length === 0) checkPrintPredecessors(program, errors);
  if (errors.length === 0) checkStackBalance(program, errors);
  return { ok: errors.length === 0, errors };
}
