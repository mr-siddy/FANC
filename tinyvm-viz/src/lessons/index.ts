export interface Lesson {
  id: string;
  title: string;
  summary: string;
  source: string;
  expectedOutput: number[];
}

export const lessons: Lesson[] = [
  {
    id: "counter",
    title: "1. Counter",
    summary: "One register. LOAD a value, PRINT it.",
    source: "LOAD R0 5\nPRINT R0\nHALT\n",
    expectedOutput: [5],
  },
  {
    id: "two-regs",
    title: "2. Two registers",
    summary: "LOAD two registers, ADD them into a third, PRINT the result.",
    source: "LOAD R0 3\nLOAD R1 4\nADD R2 R0 R1\nPRINT R2\nHALT\n",
    expectedOutput: [7],
  },
  {
    id: "first-branch",
    title: "3. First branch",
    summary: "Skip a print when a comparison fails (LT-driven JZ).",
    source:
      "LOAD R0 5\nLOAD R1 3\nLT R2 R1 R0\nJZ R2 L0\nLOAD R3 99\nL0:PRINT R3\nHALT\n",
    expectedOutput: [99],
  },
  {
    id: "countdown",
    title: "4. Count-down loop",
    summary: "Decrement a counter until it hits zero.",
    source:
      "LOAD R1 1\nLOAD R0 3\nL0:SUB R0 R0 R1\nJZ R0 L1\nJMP L0\nL1:PRINT R0\nHALT\n",
    expectedOutput: [0],
  },
  {
    id: "stack-frame",
    title: "5. Stack frame",
    summary: "PUSH a value, scratch the register, POP to restore.",
    source: "LOAD R0 7\nPUSH R0\nLOAD R0 1\nPOP R0\nPRINT R0\nHALT\n",
    expectedOutput: [7],
  },
  {
    id: "free-play",
    title: "6. Free play",
    summary: "Empty canvas. Write your own.",
    source: "",
    expectedOutput: [],
  },
];
