import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ExecutionPanel } from "@/components/ExecutionPanel";
import { buildProgram, Op } from "@/core/isa";
import { run, serializeTrace } from "@/core/interpreter";
import { renderProgramText } from "@/core/tokeniser";

describe("ExecutionPanel", () => {
  function fixture() {
    const p = buildProgram([
      { op: Op.LOAD, args: [0, 5] },
      { op: Op.PRINT, args: [0] },
      { op: Op.HALT, args: [] },
    ]);
    return { program: p, trace: serializeTrace(run(p)), source: renderProgramText(p) };
  }

  it("renders RegisterFile, ProgramView, OutputStream, StackView at stepIdx=0", () => {
    const f = fixture();
    render(
      <ExecutionPanel program={f.program} source={f.source} trace={f.trace} stepIdx={0} mode="single" />,
    );
    expect(screen.getByTestId("pgm-line-0")).toHaveAttribute("data-active", "true");
    expect(screen.getByTestId("reg-0-value")).toHaveTextContent("5");
    expect(screen.getByTestId("stack-depth")).toHaveTextContent("0 / 16");
  });

  it("renders model output column in compare mode", () => {
    const f = fixture();
    render(
      <ExecutionPanel
        program={f.program}
        source={f.source}
        trace={f.trace}
        stepIdx={1}
        mode="compare"
        modelOutput={[5]}
      />,
    );
    expect(screen.getByTestId("out-model-0")).toHaveTextContent("5");
  });
});
