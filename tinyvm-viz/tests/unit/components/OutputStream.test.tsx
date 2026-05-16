import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { OutputStream } from "@/components/OutputStream";

describe("OutputStream", () => {
  it("renders ground-truth values as rows", () => {
    render(<OutputStream groundTruth={[1, 2, 3]} model={null} />);
    expect(screen.getByTestId("out-gt-0")).toHaveTextContent("1");
    expect(screen.getByTestId("out-gt-2")).toHaveTextContent("3");
  });

  it("renders a second 'model' column with diff markers when supplied", () => {
    render(<OutputStream groundTruth={[1, 2, 3]} model={[1, 2, 9]} />);
    expect(screen.getByTestId("out-model-2")).toHaveTextContent("9");
    expect(screen.getByTestId("out-row-2")).toHaveAttribute("data-divergent", "true");
    expect(screen.getByTestId("out-row-1")).toHaveAttribute("data-divergent", "false");
  });
});
