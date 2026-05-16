import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StackView } from "@/components/StackView";

describe("StackView", () => {
  it("renders the stack top-down with depth label", () => {
    render(<StackView stack={[1, 2, 3]} maxDepth={16} />);
    expect(screen.getByTestId("stack-depth")).toHaveTextContent("3 / 16");
    const items = screen.getAllByTestId(/stack-item-/);
    expect(items[0]).toHaveTextContent("3");
    expect(items[2]).toHaveTextContent("1");
  });

  it("renders an empty stack with depth 0", () => {
    render(<StackView stack={[]} maxDepth={16} />);
    expect(screen.getByTestId("stack-depth")).toHaveTextContent("0 / 16");
    expect(screen.queryAllByTestId(/stack-item-/)).toHaveLength(0);
  });
});
