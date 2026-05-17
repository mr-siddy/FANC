import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProgramView } from "@/components/ProgramView";

describe("ProgramView", () => {
  it("renders each source line and marks the active instruction with ▶", () => {
    const source = "LOAD R0 5\nADD R0 R0 R0\nPRINT R0\nHALT\n";
    const lineToInstIdx = [0, 1, 2, 3];
    render(<ProgramView source={source} activeInstIdx={1} lineToInstIdx={lineToInstIdx} />);
    expect(screen.getByTestId("pgm-line-0")).toHaveTextContent("LOAD R0 5");
    const active = screen.getByTestId("pgm-line-1");
    expect(active).toHaveTextContent("ADD R0 R0 R0");
    expect(active).toHaveAttribute("data-active", "true");
    expect(screen.getByTestId("pgm-line-2")).toHaveAttribute("data-active", "false");
  });

  it("dims comment-only lines and aligns PC arrow with the right instruction", () => {
    const source = "; header\nLOAD R0 5\n\nHALT\n";
    const lineToInstIdx = [null, 0, null, 1];
    render(<ProgramView source={source} activeInstIdx={1} lineToInstIdx={lineToInstIdx} />);
    expect(screen.getByTestId("pgm-line-0")).toHaveAttribute("data-active", "false");
    expect(screen.getByTestId("pgm-line-1")).toHaveAttribute("data-active", "false");
    expect(screen.getByTestId("pgm-line-3")).toHaveAttribute("data-active", "true");
  });

  it("treats trailing-newline overflow lines as dim no-ops", () => {
    const source = "LOAD R0 5\n";
    const lineToInstIdx = [0];
    render(<ProgramView source={source} activeInstIdx={0} lineToInstIdx={lineToInstIdx} />);
    expect(screen.getByTestId("pgm-line-0")).toHaveAttribute("data-active", "true");
    expect(screen.getByTestId("pgm-line-1")).toHaveAttribute("data-active", "false");
  });
});
