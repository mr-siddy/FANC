import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { RegisterFile } from "@/components/RegisterFile";

describe("RegisterFile", () => {
  it("renders 8 registers with given values", () => {
    render(<RegisterFile regs={[1, 2, 3, 4, 5, 6, 7, 8]} highlightedReg={null} />);
    for (let i = 0; i < 8; i++) {
      expect(screen.getByTestId(`reg-${i}`)).toHaveTextContent(`R${i}`);
      expect(screen.getByTestId(`reg-${i}-value`)).toHaveTextContent(String(i + 1));
    }
  });

  it("highlights the register passed in highlightedReg", () => {
    render(<RegisterFile regs={[0, 0, 0, 0, 0, 0, 0, 0]} highlightedReg={3} />);
    expect(screen.getByTestId("reg-3")).toHaveAttribute("data-highlighted", "true");
    expect(screen.getByTestId("reg-2")).toHaveAttribute("data-highlighted", "false");
  });
});
