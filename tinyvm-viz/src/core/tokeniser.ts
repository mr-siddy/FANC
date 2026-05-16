import { Instruction, Op, Program } from "./isa";

const SCHEMA: Record<Op, { regs: number; lits: number; hasTarget: boolean }> = {
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

function renderInstruction(inst: Instruction): string {
  const parts: string[] = [];
  const opName = Op[inst.op];
  parts.push(opName);
  const schema = SCHEMA[inst.op];
  let cursor = 0;
  for (let i = 0; i < schema.regs; i++) {
    parts.push(`R${inst.args[cursor]}`);
    cursor++;
  }
  for (let i = 0; i < schema.lits; i++) {
    parts.push(String(inst.args[cursor]));
    cursor++;
  }
  if (schema.hasTarget) parts.push(inst.target!);
  const body = parts.join(" ");
  return inst.label !== undefined ? `${inst.label}:${body}` : body;
}

export function renderProgramText(program: Program): string {
  return program.instructions.map(renderInstruction).map((l) => l + "\n").join("");
}
