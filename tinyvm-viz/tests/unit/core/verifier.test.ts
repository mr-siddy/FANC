import { describe, it, expect } from "vitest";
import { scoreOutput } from "@/core/verifier";

describe("verifier: scoreOutput", () => {
  it("returns 1 on exact match", () => {
    expect(scoreOutput([1, 2, 3], [1, 2, 3])).toBe(1);
  });
  it("returns 0 on mismatch", () => {
    expect(scoreOutput([1, 2, 3], [1, 2, 4])).toBe(0);
  });
  it("returns 0 on length mismatch", () => {
    expect(scoreOutput([1, 2], [1, 2, 3])).toBe(0);
  });
  it("handles negatives", () => {
    expect(scoreOutput([-5, 0, 5], [-5, 0, 5])).toBe(1);
  });
});
