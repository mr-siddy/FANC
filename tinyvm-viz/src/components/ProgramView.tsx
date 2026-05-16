interface ProgramViewProps {
  source: string;
  activePc: number | null;
}

export function ProgramView({ source, activePc }: ProgramViewProps) {
  const lines = source.split("\n").filter((l) => l.length > 0);
  return (
    <pre className="text-sm font-mono leading-6 bg-white border border-slate-200 rounded p-3 overflow-auto">
      {lines.map((line, i) => {
        const active = i === activePc;
        return (
          <div
            key={i}
            data-testid={`pgm-line-${i}`}
            data-active={active ? "true" : "false"}
            className={`flex gap-2 ${active ? "bg-amber-50" : ""}`}
          >
            <span className="w-4 text-amber-600">{active ? "▶" : " "}</span>
            <span className="text-slate-800">{line}</span>
          </div>
        );
      })}
    </pre>
  );
}
