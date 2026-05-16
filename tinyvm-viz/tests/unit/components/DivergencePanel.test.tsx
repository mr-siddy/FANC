import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DivergencePanel } from "@/components/DivergencePanel";

describe("DivergencePanel", () => {
  it("renders index-aligned ground-truth vs model rows", () => {
    render(<DivergencePanel groundTruth={[1, 2, 3]} model={[1, 2, 9]} />);
    expect(screen.getByTestId("div-row-2")).toHaveAttribute("data-divergent", "true");
    expect(screen.getByTestId("div-row-0")).toHaveAttribute("data-divergent", "false");
  });

  it("treats unequal lengths as divergences", () => {
    render(<DivergencePanel groundTruth={[1, 2]} model={[1, 2, 3]} />);
    expect(screen.getByTestId("div-row-2")).toHaveAttribute("data-divergent", "true");
  });

  it("reports 'no divergence' when streams match", () => {
    render(<DivergencePanel groundTruth={[1, 2]} model={[1, 2]} />);
    expect(screen.getByTestId("div-summary")).toHaveTextContent(/no divergence/i);
  });
});
