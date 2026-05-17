import { describe, it, expect } from "vitest";
import { tinyvm } from "@/core/cmLanguage";

describe("cmLanguage: token function", () => {
  // We drive the StreamLanguage token function manually to get tag sequences.
  function tokens(line: string): string[] {
    const ts = (tinyvm as any).streamParser.token;
    const out: string[] = [];
    const stream: any = {
      pos: 0,
      string: line,
      eatSpace() {
        const m = this.string.slice(this.pos).match(/^\s+/);
        if (!m) return false;
        this.pos += m[0].length;
        return true;
      },
      match(re: RegExp) {
        const s = this.string.slice(this.pos);
        const m = s.match(re);
        if (!m || m.index !== 0) return null;
        this.pos += m[0].length;
        this._lastMatch = m[0];
        return m;
      },
      next() {
        this._lastMatch = this.string[this.pos];
        this.pos += 1;
      },
      current() { return this._lastMatch ?? ""; },
      sol() { return this.pos === 0; },
      eol() { return this.pos >= this.string.length; },
    };
    while (!stream.eol()) {
      const tag = ts(stream, null);
      if (tag !== null) out.push(tag);
    }
    return out;
  }

  it("tags LOAD opcode + register + integer literal", () => {
    expect(tokens("LOAD R3 -42")).toEqual(["keyword", "variableName", "number"]);
  });

  it("tags a label-defined line and arg registers", () => {
    expect(tokens("L3:ADD R0 R1 R2")).toEqual(["labelName", "keyword", "variableName", "variableName", "variableName"]);
  });

  it("tags JZ with a label reference", () => {
    expect(tokens("JZ R1 L7")).toEqual(["keyword", "variableName", "labelName"]);
  });

  it("tags a comment line", () => {
    expect(tokens("; this is a comment")).toEqual(["lineComment"]);
  });

  it("tags an unknown all-caps word as invalid", () => {
    expect(tokens("FOO R0")).toEqual(["invalid", "variableName"]);
  });

  it("tags a userop symbol (e.g. DOUBLE) as invalid in v1", () => {
    expect(tokens("DOUBLE R0 R1")).toEqual(["invalid", "variableName", "variableName"]);
  });
});
