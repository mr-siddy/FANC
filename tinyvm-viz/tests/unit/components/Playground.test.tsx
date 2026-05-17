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

describe("Playground: keyboard shortcuts", () => {
  it("ArrowRight advances stepIdx when no input is focused", () => {
    render(<Playground />);
    const before = screen.getByTestId("reg-0-value").textContent;
    fireEvent.keyDown(document, { key: "ArrowRight" });
    expect(before).toBe("5");
    expect(screen.getByTestId("scrubber")).toHaveValue("1");
  });

  it("ArrowLeft retreats stepIdx", () => {
    render(<Playground />);
    fireEvent.keyDown(document, { key: "ArrowRight" });
    fireEvent.keyDown(document, { key: "ArrowRight" });
    expect(screen.getByTestId("scrubber")).toHaveValue("2");
    fireEvent.keyDown(document, { key: "ArrowLeft" });
    expect(screen.getByTestId("scrubber")).toHaveValue("1");
  });

  it("r resets stepIdx to 0", () => {
    render(<Playground />);
    fireEvent.keyDown(document, { key: "ArrowRight" });
    fireEvent.keyDown(document, { key: "ArrowRight" });
    expect(screen.getByTestId("scrubber")).toHaveValue("2");
    fireEvent.keyDown(document, { key: "r" });
    expect(screen.getByTestId("scrubber")).toHaveValue("0");
  });

  it("Cmd+R does not reset (browser refresh shortcut)", () => {
    render(<Playground />);
    fireEvent.keyDown(document, { key: "ArrowRight" });
    expect(screen.getByTestId("scrubber")).toHaveValue("1");
    fireEvent.keyDown(document, { key: "r", metaKey: true });
    expect(screen.getByTestId("scrubber")).toHaveValue("1");
  });

  it("ignores keys when an input has focus", () => {
    render(<Playground />);
    fireEvent.keyDown(document, { key: "ArrowRight" });
    expect(screen.getByTestId("scrubber")).toHaveValue("1");
    const input = document.createElement("input");
    document.body.appendChild(input);
    input.focus();
    fireEvent.keyDown(document, { key: "ArrowRight" });
    expect(screen.getByTestId("scrubber")).toHaveValue("1");
    input.remove();
  });
});
