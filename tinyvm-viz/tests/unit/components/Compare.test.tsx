import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Compare, validateBundle } from "@/pages/Compare";
import passBundle from "../../../samples/example_pass.json";
import divBundle from "../../../samples/example_divergence.json";

function renderInRouter(ui: React.ReactElement) {
  return render(<MemoryRouter initialEntries={["/compare"]}>{ui}</MemoryRouter>);
}

const faultBundle = {
  schema: "tinyvm-viz/comparison/v1" as const,
  meta: { generator: "manual", seed: 2, interpreterError: "stack underflow at step 0" },
  source: "POP R0\n",
  groundTruth: {
    trace: {
      steps: [{ pc: 0, regs: [0,0,0,0,0,0,0,0], stack: [], emitted: null }],
      output: [],
      halted: false,
    },
  },
  prediction: { output: [] },
};

describe("Compare", () => {
  it("renders a passing bundle with 'no divergence'", () => {
    renderInRouter(<Compare initialBundle={passBundle as never} />);
    expect(screen.getByTestId("div-summary")).toHaveTextContent(/no divergence/i);
  });

  it("renders a divergence at index 0", () => {
    renderInRouter(<Compare initialBundle={divBundle as never} />);
    expect(screen.getByTestId("div-summary")).toHaveTextContent(/first divergence at #0/i);
    expect(screen.getByTestId("div-row-0")).toHaveAttribute("data-divergent", "true");
  });

  it("shows a parity-drift banner when groundTruth disagrees with the TS re-run", () => {
    const tampered = JSON.parse(JSON.stringify(passBundle));
    tampered.groundTruth.trace.output = [999];
    renderInRouter(<Compare initialBundle={tampered as never} />);
    expect(screen.getByTestId("parity-banner")).toHaveTextContent(/parity drift suspected/i);
  });

  it("loads a bundle from the ?bundle= query param", async () => {
    const mockResponse = { json: () => Promise.resolve(passBundle) };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(mockResponse as Response);
    render(
      <MemoryRouter initialEntries={[`/compare?bundle=http://example/test.json`]}>
        <Compare />
      </MemoryRouter>,
    );
    await screen.findByTestId("div-summary");
    expect(screen.getByTestId("div-summary")).toHaveTextContent(/no divergence/i);
  });

  it("validateBundle rejects bundle missing groundTruth.trace.output", () => {
    const bad = JSON.parse(JSON.stringify(passBundle));
    delete bad.groundTruth.trace.output;
    expect(validateBundle(bad)).toBe(false);
  });

  it("renders a fault-bundle (halted=false) with an amber 'interpreter halted' banner", () => {
    renderInRouter(<Compare initialBundle={faultBundle as never} />);
    expect(screen.getByTestId("fault-banner")).toHaveTextContent(/stack underflow at step 0/);
    expect(screen.queryByTestId("parity-banner")).toBeNull();
  });

  it("falls back to generic 'halted before completion' when meta.interpreterError absent", () => {
    const noErrMeta = { ...faultBundle, meta: { generator: "manual", seed: 3 } };
    renderInRouter(<Compare initialBundle={noErrMeta as never} />);
    expect(screen.getByTestId("fault-banner")).toHaveTextContent(/halted before completion/i);
  });
});
