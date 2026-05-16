import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { Playground } from "@/pages/Playground";

describe("Playground", () => {
  it("loads lesson #1 by default and shows post-LOAD register R0=5", () => {
    render(<Playground />);
    expect(screen.getByTestId("reg-0-value")).toHaveTextContent("5");
  });

  it("clicking another lesson swaps the program", () => {
    render(<Playground />);
    fireEvent.click(screen.getByText(/Two registers/));
    act(() => { /* allow effect */ });
    expect(screen.getByTestId("pgm-line-0")).toHaveTextContent("LOAD R0 3");
  });
});
