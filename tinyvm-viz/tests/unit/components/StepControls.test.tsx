import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StepControls } from "@/components/StepControls";

describe("StepControls", () => {
  it("clicking ▸ step calls onStep(+1)", () => {
    const onStep = vi.fn();
    render(<StepControls stepIdx={0} maxStep={5} running={false} onStep={onStep} onRunToggle={() => {}} onReset={() => {}} />);
    fireEvent.click(screen.getByTestId("btn-step-forward"));
    expect(onStep).toHaveBeenCalledWith(1);
  });

  it("clicking ◂ step calls onStep(-1)", () => {
    const onStep = vi.fn();
    render(<StepControls stepIdx={3} maxStep={5} running={false} onStep={onStep} onRunToggle={() => {}} onReset={() => {}} />);
    fireEvent.click(screen.getByTestId("btn-step-back"));
    expect(onStep).toHaveBeenCalledWith(-1);
  });

  it("disables back at step 0 and forward at maxStep", () => {
    const { unmount } = render(<StepControls stepIdx={0} maxStep={5} running={false} onStep={() => {}} onRunToggle={() => {}} onReset={() => {}} />);
    expect(screen.getByTestId("btn-step-back")).toBeDisabled();
    unmount();
    render(<StepControls stepIdx={5} maxStep={5} running={false} onStep={() => {}} onRunToggle={() => {}} onReset={() => {}} />);
    expect(screen.getByTestId("btn-step-forward")).toBeDisabled();
  });

  it("scrubber emits onStep(delta) to reach the target", () => {
    const onStep = vi.fn();
    render(<StepControls stepIdx={2} maxStep={5} running={false} onStep={onStep} onRunToggle={() => {}} onReset={() => {}} />);
    fireEvent.change(screen.getByTestId("scrubber"), { target: { value: "4" } });
    expect(onStep).toHaveBeenCalledWith(2);
  });
});
