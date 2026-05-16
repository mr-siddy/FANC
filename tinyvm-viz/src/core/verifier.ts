export function scoreOutput(predicted: number[], target: number[]): number {
  if (predicted.length !== target.length) return 0;
  for (let i = 0; i < predicted.length; i++) {
    if (predicted[i] !== target[i]) return 0;
  }
  return 1;
}
