export interface SerializedStep {
  pc: number;
  regs: number[];                  // length 8
  stack: number[];                 // 0..16
  emitted: number | null;
}

export interface SerializedTrace {
  steps: SerializedStep[];
  output: number[];
  halted: boolean;
}

export interface BundleMeta {
  generator: string;
  seed: number;
  spec?: Record<string, unknown>;
  tier?: string;
  interpreterError?: string;
}

export interface ComparisonBundle {
  schema: "tinyvm-viz/comparison/v1";
  meta: BundleMeta;
  source: string;
  groundTruth: { trace: SerializedTrace };
  prediction: {
    output: number[];
    model?: string;
    decodeWarnings?: string[];
  };
}
