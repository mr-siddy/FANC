import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProgramView } from "@/components/ProgramView";

describe("ProgramView", () => {
  it("renders each instruction as a row and marks the active PC with ▶", () => {
    const source = "LOAD R0 5\nADD R0 R0 R0\nPRINT R0\nHALT\n";
    render(<ProgramView source={source} activePc={1} />);
    expect(screen.getByTestId("pgm-line-0")).toHaveTextContent("LOAD R0 5");
    const active = screen.getByTestId("pgm-line-1");
    expect(active).toHaveTextContent("ADD R0 R0 R0");
    expect(active).toHaveAttribute("data-active", "true");
    expect(screen.getByTestId("pgm-line-2")).toHaveAttribute("data-active", "false");
  });
});
