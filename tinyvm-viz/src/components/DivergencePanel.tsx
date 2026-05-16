interface DivergencePanelProps {
  groundTruth: readonly number[];
  model: readonly number[];
}

export function DivergencePanel({ groundTruth, model }: DivergencePanelProps) {
  const n = Math.max(groundTruth.length, model.length);
  let firstDiv = -1;
  for (let i = 0; i < n; i++) {
    if (groundTruth[i] !== model[i]) { firstDiv = i; break; }
  }
  return (
    <div className="text-sm font-mono">
      <div data-testid="div-summary" className="mb-2 text-xs text-slate-600">
        {firstDiv === -1 ? "no divergence" : `first divergence at #${firstDiv}`}
      </div>
      <div className="grid grid-cols-[3rem_1fr_1fr_2rem] gap-x-2 gap-y-0.5">
        <div className="text-xs text-slate-400">idx</div>
        <div className="text-xs text-slate-400">gt</div>
        <div className="text-xs text-slate-400">model</div>
        <div></div>
        {Array.from({ length: n }).map((_, i) => {
          const gt = groundTruth[i];
          const m = model[i];
          const div = gt !== m;
          return (
            <div
              key={i}
              data-testid={`div-row-${i}`}
              data-divergent={div ? "true" : "false"}
              className={`contents`}
            >
              <div className="text-slate-400">{i}</div>
              <div className={div ? "bg-red-100" : ""}>{gt ?? "—"}</div>
              <div className={div ? "bg-red-100" : ""}>{m ?? "—"}</div>
              <div>{div ? "✗" : "✓"}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
