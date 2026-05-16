interface StepControlsProps {
  stepIdx: number;
  maxStep: number;
  running: boolean;
  onStep: (delta: number) => void;
  onRunToggle: () => void;
  onReset: () => void;
}

export function StepControls({ stepIdx, maxStep, running, onStep, onRunToggle, onReset }: StepControlsProps) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <button data-testid="btn-reset" className="px-2 py-1 border rounded" onClick={onReset}>⟲ reset</button>
      <button
        data-testid="btn-step-back"
        className="px-2 py-1 border rounded disabled:opacity-40"
        onClick={() => onStep(-1)}
        disabled={stepIdx <= 0}
      >
        ◂ step
      </button>
      <button data-testid="btn-run" className="px-2 py-1 border rounded" onClick={onRunToggle}>
        {running ? "⏸ pause" : "▶ run"}
      </button>
      <button
        data-testid="btn-step-forward"
        className="px-2 py-1 border rounded disabled:opacity-40"
        onClick={() => onStep(1)}
        disabled={stepIdx >= maxStep}
      >
        step ▸
      </button>
      <input
        data-testid="scrubber"
        type="range"
        min={0}
        max={maxStep}
        value={stepIdx}
        onChange={(e) => onStep(Number(e.target.value) - stepIdx)}
        className="ml-4 flex-1"
      />
      <span className="text-xs text-slate-500 w-20 text-right">
        step {stepIdx + 1} / {maxStep + 1}
      </span>
    </div>
  );
}
