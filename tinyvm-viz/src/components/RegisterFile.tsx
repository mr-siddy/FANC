interface RegisterFileProps {
  regs: readonly number[];
  highlightedReg: number | null;
}

export function RegisterFile({ regs, highlightedReg }: RegisterFileProps) {
  return (
    <div className="grid grid-cols-2 gap-1 text-sm font-mono">
      {regs.map((v, i) => {
        const highlighted = i === highlightedReg;
        return (
          <div
            key={i}
            data-testid={`reg-${i}`}
            data-highlighted={highlighted ? "true" : "false"}
            className={`flex items-center justify-between px-2 py-1 rounded border ${
              highlighted ? "bg-amber-100 border-amber-300" : "bg-white border-slate-200"
            }`}
          >
            <span className="text-slate-500">R{i}</span>
            <span data-testid={`reg-${i}-value`} className="text-slate-900">
              {v}
            </span>
          </div>
        );
      })}
    </div>
  );
}
