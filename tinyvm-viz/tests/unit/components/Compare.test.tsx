import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Compare } from "@/pages/Compare";
import passBundle from "../../../samples/example_pass.json";
import divBundle from "../../../samples/example_divergence.json";

describe("Compare", () => {
  it("renders a passing bundle with 'no divergence'", () => {
    render(<Compare initialBundle={passBundle as never} />);
    expect(screen.getByTestId("div-summary")).toHaveTextContent(/no divergence/i);
  });

  it("renders a divergence at index 0", () => {
    render(<Compare initialBundle={divBundle as never} />);
    expect(screen.getByTestId("div-summary")).toHaveTextContent(/first divergence at #0/i);
    expect(screen.getByTestId("div-row-0")).toHaveAttribute("data-divergent", "true");
  });

  it("shows a parity-drift banner when groundTruth disagrees with the TS re-run", () => {
    const tampered = JSON.parse(JSON.stringify(passBundle));
    tampered.groundTruth.trace.output = [999];
    render(<Compare initialBundle={tampered as never} />);
    expect(screen.getByTestId("parity-banner")).toHaveTextContent(/parity drift suspected/i);
  });
});
