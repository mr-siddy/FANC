import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ExecutionPanel } from "@/components/ExecutionPanel";
import { DivergencePanel } from "@/components/DivergencePanel";
import { StepControls } from "@/components/StepControls";
import { parse } from "@/core/parser";
import { deserializeTrace, run, serializeTrace } from "@/core/interpreter";
import type { ComparisonBundle, SerializedTrace } from "@/core/types";

const sampleModules = import.meta.glob<ComparisonBundle>(
  "/samples/*.json",
  { eager: true, import: "default" },
);
const samples = Object.entries(sampleModules)
  .map(([path, bundle]) => ({ filename: path.split("/").pop()!, bundle }))
  .sort((a, b) => a.filename.localeCompare(b.filename));

interface CompareProps {
  initialBundle?: ComparisonBundle;
}

export function validateBundle(b: unknown): b is ComparisonBundle {
  if (typeof b !== "object" || b === null) return false;
  const r = b as Record<string, unknown>;
  if (r.schema !== "tinyvm-viz/comparison/v1") return false;
  if (typeof r.source !== "string") return false;
  const gt = r.groundTruth as Record<string, unknown> | null | undefined;
  const pred = r.prediction as Record<string, unknown> | null | undefined;
  if (!gt || typeof gt !== "object") return false;
  const trace = gt.trace as Record<string, unknown> | null | undefined;
  if (!trace || typeof trace !== "object") return false;
  if (!Array.isArray(trace.steps)) return false;
  if (!Array.isArray(trace.output)) return false;
  if (typeof trace.halted !== "boolean") return false;
  if (!pred || typeof pred !== "object") return false;
  if (!Array.isArray(pred.output)) return false;
  return true;
}

export function Compare({ initialBundle }: CompareProps) {
  const [bundle, setBundle] = useState<ComparisonBundle | null>(initialBundle ?? null);
  const [stepIdx, setStepIdx] = useState(0);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [params] = useSearchParams();

  useEffect(() => {
    const url = params.get("bundle");
    if (!url || bundle) return;
    fetch(url)
      .then((r) => r.json())
      .then((j) => {
        if (validateBundle(j)) { setBundle(j); setStepIdx(0); }
        else setLoadError("bundle: schema mismatch");
      })
      .catch((e) => setLoadError(`bundle: ${(e as Error).message}`));
  }, [params, bundle]);

  type ReRunResult =
    | null
    | { ok: false; message: string; lineToInstIdx: (number | null)[] }
    | { ok: true; program: import("@/core/isa").Program; tsTrace: SerializedTrace; lineToInstIdx: (number | null)[]; faulted: true }
    | { ok: boolean; program: import("@/core/isa").Program; tsTrace: SerializedTrace; lineToInstIdx: (number | null)[]; faulted: false };

  const reRun = useMemo<ReRunResult>(() => {
    if (!bundle) return null;
    if (bundle.groundTruth.trace.halted === false) {
      const { program, errors, lineToInstIdx } = parse(bundle.source);
      if (!program || errors.length) return { ok: false as const, message: "bundle.source did not parse", lineToInstIdx };
      return { ok: true as const, program, tsTrace: bundle.groundTruth.trace, lineToInstIdx, faulted: true as const };
    }
    const { program, errors, lineToInstIdx } = parse(bundle.source);
    if (!program || errors.length) return { ok: false as const, message: "bundle.source did not parse", lineToInstIdx };
    try {
      const trace = serializeTrace(run(program));
      const same = JSON.stringify(trace.output) === JSON.stringify(bundle.groundTruth.trace.output);
      return { ok: same, program, tsTrace: trace, lineToInstIdx, faulted: false as const };
    } catch (e) {
      return { ok: false as const, message: (e as Error).message, lineToInstIdx };
    }
  }, [bundle]);

  function onFile(file: File) {
    file.text().then((txt) => {
      try {
        const parsed = JSON.parse(txt);
        if (!validateBundle(parsed)) {
          setLoadError("bundle: schema mismatch");
          return;
        }
        setLoadError(null);
        setBundle(parsed);
        setStepIdx(0);
      } catch (e) {
        setLoadError(`bundle: ${(e as Error).message}`);
      }
    });
  }

  if (!bundle) {
    return (
      <div className="p-4 space-y-3">
        <h2 className="text-lg font-semibold">Comparison view</h2>
        <div className="flex items-center gap-3">
          <label className="text-sm">Load a sample:</label>
          <select
            data-testid="samples-select"
            className="border border-slate-200 rounded px-2 py-1 text-sm"
            defaultValue=""
            onChange={(e) => {
              const choice = samples.find((s) => s.filename === e.target.value);
              if (choice) { setBundle(choice.bundle); setStepIdx(0); }
            }}
          >
            <option value="" disabled>Choose a sample…</option>
            {samples.map((s) => (
              <option key={s.filename} value={s.filename}>{s.filename}</option>
            ))}
          </select>
          <span className="text-xs text-slate-500">or drop a file:</span>
          <input
            type="file"
            accept="application/json"
            onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0]!)}
          />
        </div>
        {loadError && <div className="text-red-600 text-sm">{loadError}</div>}
      </div>
    );
  }

  const reRunSuccess = reRun && "tsTrace" in reRun ? reRun : null;
  const trace: SerializedTrace = reRunSuccess
    ? reRunSuccess.tsTrace
    : serializeTrace(deserializeTrace(bundle.groundTruth.trace));
  const maxStep = trace.steps.length - 1;
  const safeStep = Math.min(stepIdx, maxStep);

  return (
    <div className="p-4 space-y-3">
      <div className="text-xs text-slate-500">
        bundle · {bundle.meta.generator} · seed {bundle.meta.seed} ·
        {" "}gt {JSON.stringify(bundle.groundTruth.trace.output)} ·
        {" "}model {JSON.stringify(bundle.prediction.output)}
      </div>
      {reRun && "faulted" in reRun && reRun.faulted && (
        <div data-testid="fault-banner" className="text-sm bg-amber-100 text-amber-900 p-2 rounded">
          interpreter halted with: {bundle.meta.interpreterError ?? "halted before completion"}
        </div>
      )}
      {reRun && !reRun.ok && !("faulted" in reRun && reRun.faulted) && (
        <div data-testid="parity-banner" className="text-sm bg-red-100 text-red-800 p-2 rounded">
          parity drift suspected — bundle ground truth disagrees with TS re-run
        </div>
      )}
      <DivergencePanel
        groundTruth={bundle.groundTruth.trace.output}
        model={bundle.prediction.output}
      />
      <StepControls
        stepIdx={safeStep}
        maxStep={maxStep}
        running={false}
        onStep={(d) => setStepIdx((s) => Math.max(0, Math.min(s + d, maxStep)))}
        onRunToggle={() => {}}
        onReset={() => setStepIdx(0)}
      />
      {reRunSuccess && (
        <ExecutionPanel
          program={reRunSuccess.program}
          source={bundle.source}
          trace={trace}
          stepIdx={safeStep}
          mode="compare"
          modelOutput={bundle.prediction.output}
          lineToInstIdx={reRunSuccess.lineToInstIdx}
        />
      )}
    </div>
  );
}

export default Compare;
