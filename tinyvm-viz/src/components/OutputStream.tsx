interface OutputStreamProps {
  groundTruth: readonly number[];
  model: readonly number[] | null;
}

export function OutputStream({ groundTruth, model }: OutputStreamProps) {
  const n = Math.max(groundTruth.length, model ? model.length : 0);
  return (
    <div className="text-sm font-mono">
      <div className="grid grid-cols-[auto_1fr_1fr] gap-x-2 gap-y-0.5">
        <div className="text-xs uppercase text-slate-400">#</div>
        <div className="text-xs uppercase text-slate-400">gt</div>
        <div className="text-xs uppercase text-slate-400">{model ? "model" : ""}</div>
        {Array.from({ length: n }).map((_, i) => {
          const gt = groundTruth[i];
          const m = model ? model[i] : undefined;
          const divergent = model !== null && gt !== m;
          return (
            <div
              key={i}
              data-testid={`out-row-${i}`}
              data-divergent={divergent ? "true" : "false"}
              className="contents"
            >
              <div className="text-slate-400">{i}</div>
              <div data-testid={`out-gt-${i}`} className={divergent ? "bg-red-100" : ""}>
                {gt ?? "—"}
              </div>
              <div data-testid={`out-model-${i}`} className={divergent ? "bg-red-100" : ""}>
                {model ? (m ?? "—") : ""}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
