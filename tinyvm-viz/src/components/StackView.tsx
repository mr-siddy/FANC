interface StackViewProps {
  stack: readonly number[];
  maxDepth: number;
}

export function StackView({ stack, maxDepth }: StackViewProps) {
  const reversed = [...stack].reverse();
  return (
    <div className="text-sm font-mono">
      <div className="space-y-1">
        {reversed.map((v, i) => (
          <div
            key={i}
            data-testid={`stack-item-${i}`}
            className="px-2 py-1 rounded border bg-white border-slate-200"
          >
            {v}
          </div>
        ))}
      </div>
      <div data-testid="stack-depth" className="mt-2 text-xs text-slate-500">
        {stack.length} / {maxDepth}
      </div>
    </div>
  );
}
