import { Program } from "@/core/isa";
import { SerializedTrace } from "@/core/types";
import { RegisterFile } from "./RegisterFile";
import { StackView } from "./StackView";
import { ProgramView } from "./ProgramView";
import { OutputStream } from "./OutputStream";

interface ExecutionPanelProps {
  program: Program;
  source: string;
  trace: SerializedTrace;
  stepIdx: number;
  mode: "single" | "compare";
  modelOutput?: readonly number[];
  lineToInstIdx: readonly (number | null)[];
}

export function ExecutionPanel({
  program: _program,
  source,
  trace,
  stepIdx,
  mode,
  modelOutput,
  lineToInstIdx,
}: ExecutionPanelProps) {
  const step = trace.steps[Math.max(0, Math.min(stepIdx, trace.steps.length - 1))]!;
  const prev = stepIdx > 0 ? trace.steps[stepIdx - 1]! : null;
  const highlighted = prev
    ? step.regs.findIndex((v, i) => v !== prev.regs[i])
    : -1;
  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_18rem] gap-4">
      <div className="space-y-4">
        <ProgramView source={source} activeInstIdx={step.pc} lineToInstIdx={lineToInstIdx} />
        <OutputStream
          groundTruth={trace.output}
          model={mode === "compare" ? (modelOutput ?? []) : null}
        />
      </div>
      <div className="space-y-4">
        <RegisterFile regs={step.regs} highlightedReg={highlighted >= 0 ? highlighted : null} />
        <StackView stack={step.stack} maxDepth={16} />
        <div className="text-xs text-slate-500">
          step {stepIdx + 1} / {trace.steps.length}
        </div>
      </div>
    </div>
  );
}
