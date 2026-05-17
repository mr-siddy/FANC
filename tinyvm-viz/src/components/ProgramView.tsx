interface ProgramViewProps {
  source: string;
  activeInstIdx: number | null;
  lineToInstIdx: readonly (number | null)[];
}

export function ProgramView({ source, activeInstIdx, lineToInstIdx }: ProgramViewProps) {
  const lines = source.split("\n");
  return (
    <pre className="text-sm font-mono leading-6 bg-white border border-slate-200 rounded p-3 overflow-auto">
      {lines.map((line, i) => {
        const instIdx = lineToInstIdx[i] ?? null;
        const active = instIdx !== null && instIdx === activeInstIdx;
        const dim = instIdx === null;
        return (
          <div
            key={i}
            data-testid={`pgm-line-${i}`}
            data-active={active ? "true" : "false"}
            className={`flex gap-2 ${active ? "bg-amber-50" : ""} ${dim ? "text-slate-400" : "text-slate-800"}`}
          >
            <span className="w-4 text-amber-600">{active ? "▶" : " "}</span>
            <span>{line}</span>
          </div>
        );
      })}
    </pre>
  );
}
