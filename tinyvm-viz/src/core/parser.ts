import { buildProgram, Instruction, Op, Program } from "./isa";

export interface ParseError {
  line: number;
  message: string;
}

export interface ParseResult {
  program?: Program;
  errors: ParseError[];
  /** lineToInstIdx[i] = instruction index for source line i (0-indexed),
   *  or null if the line is blank, comment-only, or unparseable. */
  lineToInstIdx: (number | null)[];
}

interface ArgSchema {
  regs: number;
  lits: number;
  hasTarget: boolean;
}

const SCHEMA: Record<Op, ArgSchema> = {
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

const OP_BY_NAME: Record<string, Op> = Object.fromEntries(
  Object.keys(Op)
    .filter((k) => isNaN(Number(k)) && !k.startsWith("USEROP"))
    .map((k) => [k, Op[k as keyof typeof Op] as Op]),
);

function stripComment(line: string): string {
  const ci = line.indexOf(";");
  return ci >= 0 ? line.slice(0, ci) : line;
}

function tokenise(line: string): string[] {
  // Split on whitespace first, then further split any token at an embedded '-'
  // that is not at position 0.  This handles the Python renderer's MINUS-attachment
  // style where e.g. "LOAD R0-93" is emitted instead of "LOAD R0 -93".
  const raw = stripComment(line).trim().split(/\s+/).filter((t) => t.length > 0);
  const out: string[] = [];
  for (const tok of raw) {
    const dashIdx = tok.indexOf("-", 1); // skip position 0 (leading minus is fine)
    if (dashIdx > 0) {
      out.push(tok.slice(0, dashIdx));
      out.push(tok.slice(dashIdx));
    } else {
      out.push(tok);
    }
  }
  return out;
}

function parseReg(tok: string): number | null {
  if (!/^R[0-7]$/.test(tok)) return null;
  return Number(tok.slice(1));
}

function parseIntLit(tok: string): number | null {
  if (!/^-?\d+$/.test(tok)) return null;
  return Number(tok);
}

function parseLabelRef(tok: string): string | null {
  return /^L\d+$/.test(tok) ? tok : null;
}

export function parse(source: string): ParseResult {
  const errors: ParseError[] = [];
  const insts: Instruction[] = [];
  const lines = source.split("\n");
  const lineToInstIdx: (number | null)[] = [];

  for (let li = 0; li < lines.length; li++) {
    const raw = lines[li]!;
    let label: string | undefined;
    const stripped = stripComment(raw).trim();
    if (stripped.length === 0) {
      lineToInstIdx.push(null);
      continue;
    }

    let rest = stripped;
    const labelMatch = stripped.match(/^(L\d+)\s*:\s*(.*)$/);
    if (labelMatch) {
      label = labelMatch[1]!;
      rest = labelMatch[2]!;
    }

    const tokens = tokenise(rest);
    if (tokens.length === 0) {
      // label-only line: emit a NOP carrying the label
      lineToInstIdx.push(insts.length);
      insts.push({ op: Op.NOP, args: [], label, target: undefined });
      continue;
    }

    const opName = tokens[0]!.toUpperCase();
    const op = OP_BY_NAME[opName];
    if (op === undefined) {
      errors.push({ line: li + 1, message: `unknown opcode: ${opName}` });
      lineToInstIdx.push(null);
      continue;
    }

    const schema = SCHEMA[op];
    const expected = schema.regs + schema.lits + (schema.hasTarget ? 1 : 0);
    const got = tokens.length - 1;
    if (got !== expected) {
      errors.push({ line: li + 1, message: `${opName} (arity) expects ${expected} operands, got ${got}` });
      lineToInstIdx.push(null);
      continue;
    }

    const args: number[] = [];
    let target: string | undefined;
    let cursor = 1;
    let lineHasError = false;

    for (let i = 0; i < schema.regs; i++) {
      const r = parseReg(tokens[cursor]!);
      if (r === null) {
        errors.push({ line: li + 1, message: `expected register, got '${tokens[cursor]}'` });
        lineHasError = true;
      } else {
        args.push(r);
      }
      cursor++;
    }

    for (let i = 0; i < schema.lits; i++) {
      const v = parseIntLit(tokens[cursor]!);
      if (v === null) {
        errors.push({ line: li + 1, message: `expected integer literal, got '${tokens[cursor]}'` });
        lineHasError = true;
      } else {
        args.push(v);
      }
      cursor++;
    }

    if (schema.hasTarget) {
      const t = parseLabelRef(tokens[cursor]!);
      if (t === null) {
        errors.push({ line: li + 1, message: `expected label target, got '${tokens[cursor]}'` });
        lineHasError = true;
      } else {
        target = t;
      }
      cursor++;
    }

    if (lineHasError) {
      lineToInstIdx.push(null);
    } else {
      lineToInstIdx.push(insts.length);
      insts.push({ op, args, label, target });
    }
  }

  if (errors.length > 0) return { errors, lineToInstIdx };

  try {
    return { program: buildProgram(insts), errors: [], lineToInstIdx };
  } catch (e) {
    const msg = (e as Error).message;
    const m = msg.match(/duplicate label: (L\d+)/);
    if (m) {
      const lbl = m[1]!;
      const lineNum = lines.findIndex((l, idx) => idx > 0 && stripComment(l).trim().startsWith(`${lbl}:`)) + 1;
      return { errors: [{ line: lineNum || 0, message: msg }], lineToInstIdx };
    }
    return { errors: [{ line: 0, message: msg }], lineToInstIdx };
  }
}
