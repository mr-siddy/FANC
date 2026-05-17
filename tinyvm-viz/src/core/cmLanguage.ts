import { StreamLanguage, StringStream } from "@codemirror/language";

const OPCODES = new Set([
  "LOAD", "MOV", "ADD", "SUB", "MUL", "DIV", "NEG", "EQ", "LT",
  "JZ", "JMP", "PUSH", "POP", "PRINT", "NOP", "HALT",
]);

export const tinyvm = StreamLanguage.define({
  token(stream: StringStream) {
    if (stream.eatSpace()) return null;

    // Comment: consumes to end of line
    if (stream.match(/^;.*/)) return "lineComment";

    // Label definition: L<digits>: — consume label name, colon is consumed separately (no tag)
    // We need to emit "labelName" for the L<digits> part, then swallow the colon without a tag.
    // Approach: match L<digits> then peek for ":"
    const labelDefMatch = (stream as any).match(/^L\d+(?=:)/);
    if (labelDefMatch) {
      // Consume the colon that follows (no tag)
      (stream as any).match(/^:/);
      return "labelName";
    }

    // Label reference: L<digits> not followed by ":"
    if ((stream as any).match(/^L\d+/)) return "labelName";

    // Register: R0–R7
    if ((stream as any).match(/^R[0-7]\b/)) return "variableName";

    // Number literal (signed integer)
    if ((stream as any).match(/^-?\d+\b/)) return "number";

    // All-caps word — opcode or invalid
    const wordMatch = (stream as any).match(/^[A-Z]+\b/);
    if (wordMatch) {
      const word = (stream as any).current();
      return OPCODES.has(word) ? "keyword" : "invalid";
    }

    // Consume any other character without a tag
    stream.next();
    return null;
  },
  languageData: { commentTokens: { line: ";" } },
});
