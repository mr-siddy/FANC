import { useEffect, useMemo, useState } from "react";
import { Editor } from "@/components/Editor";
import { ExecutionPanel } from "@/components/ExecutionPanel";
import { LessonPlaylist } from "@/components/LessonPlaylist";
import { StepControls } from "@/components/StepControls";
import { lessons } from "@/lessons";
import { parse } from "@/core/parser";
import { run, serializeTrace, InterpreterError } from "@/core/interpreter";
import type { SerializedTrace } from "@/core/types";

export function Playground() {
  const [lessonId, setLessonId] = useState(lessons[0]!.id);
  const lesson = useMemo(() => lessons.find((l) => l.id === lessonId)!, [lessonId]);
  const [source, setSource] = useState(lesson.source);
  const [stepIdx, setStepIdx] = useState(0);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    setSource(lesson.source);
    setRunning(false);
    setStepIdx(0);
  }, [lesson]);

  const { program, errors, lineToInstIdx } = useMemo(() => parse(source), [source]);
  const traceResult = useMemo<{ trace: SerializedTrace | null; error: string | null }>(() => {
    if (!program) return { trace: null, error: null };
    try {
      return { trace: serializeTrace(run(program)), error: null };
    } catch (e) {
      if (e instanceof InterpreterError) return { trace: null, error: e.message };
      return { trace: null, error: (e as Error).message };
    }
  }, [program]);
  const trace = traceResult.trace;
  const error = traceResult.error;

  useEffect(() => {
    if (!running || !trace) return;
    if (stepIdx >= trace.steps.length - 1) {
      setRunning(false);
      return;
    }
    const id = setTimeout(() => setStepIdx((s) => s + 1), 200);
    return () => clearTimeout(id);
  }, [running, stepIdx, trace]);

  const maxStep = trace ? trace.steps.length - 1 : 0;
  const safeStep = Math.min(stepIdx, maxStep);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const active = document.activeElement as HTMLElement | null;
      if (active && (active.closest(".cm-editor") || active.tagName === "INPUT" || active.tagName === "TEXTAREA")) return;
      switch (e.key) {
        case "ArrowRight":
          e.preventDefault();
          setStepIdx((s) => Math.min(s + 1, maxStep));
          break;
        case "ArrowLeft":
          e.preventDefault();
          setStepIdx((s) => Math.max(s - 1, 0));
          break;
        case " ":
          e.preventDefault();
          setRunning((r) => !r);
          break;
        case "r":
        case "R":
          if (e.metaKey || e.ctrlKey) return;
          e.preventDefault();
          setStepIdx(0);
          break;
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [maxStep]);

  return (
    <div className="grid grid-cols-[14rem_1fr] gap-4 p-4">
      <aside>
        <LessonPlaylist lessons={lessons} selectedId={lesson.id} onSelect={setLessonId} />
      </aside>
      <main className="space-y-3">
        <Editor value={source} onChange={setSource} />
        <StepControls
          stepIdx={safeStep}
          maxStep={maxStep}
          running={running}
          onStep={(d) => setStepIdx((s) => Math.max(0, Math.min(s + d, maxStep)))}
          onRunToggle={() => setRunning((r) => !r)}
          onReset={() => setStepIdx(0)}
        />
        {errors.length > 0 && (
          <div className="text-sm text-red-600">
            {errors.map((e, i) => (
              <div key={i}>line {e.line}: {e.message}</div>
            ))}
          </div>
        )}
        {error && <div className="text-sm text-amber-700">{error}</div>}
        {program && trace && (
          <ExecutionPanel
            program={program}
            source={source}
            trace={trace}
            stepIdx={safeStep}
            mode="single"
            lineToInstIdx={lineToInstIdx}
          />
        )}
      </main>
    </div>
  );
}

export default Playground;
