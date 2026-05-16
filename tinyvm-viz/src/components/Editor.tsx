import { useEffect, useRef } from "react";
import { EditorState } from "@codemirror/state";
import { EditorView, keymap, lineNumbers, highlightActiveLine } from "@codemirror/view";
import { defaultKeymap, history, historyKeymap } from "@codemirror/commands";
import { linter, Diagnostic } from "@codemirror/lint";
import { parse } from "@/core/parser";
import { validate } from "@/core/verifier";

interface EditorProps {
  value: string;
  onChange: (next: string) => void;
}

function tinyvmLinter(view: EditorView): Diagnostic[] {
  const src = view.state.doc.toString();
  const out: Diagnostic[] = [];
  const { program, errors } = parse(src);
  for (const e of errors) {
    const lineNum = Math.max(1, e.line);
    const line = view.state.doc.line(Math.min(lineNum, view.state.doc.lines));
    out.push({ from: line.from, to: line.to, severity: "error", message: e.message });
  }
  if (program) {
    const v = validate(program);
    for (const msg of v.errors) {
      out.push({ from: 0, to: Math.min(src.length, 1), severity: "warning", message: msg });
    }
  }
  return out;
}

export function Editor({ value, onChange }: EditorProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const viewRef = useRef<EditorView | null>(null);

  useEffect(() => {
    if (!ref.current || viewRef.current) return;
    const state = EditorState.create({
      doc: value,
      extensions: [
        lineNumbers(),
        history(),
        highlightActiveLine(),
        keymap.of([...defaultKeymap, ...historyKeymap]),
        linter(tinyvmLinter, { delay: 150 }),
        EditorView.updateListener.of((u) => {
          if (u.docChanged) onChange(u.state.doc.toString());
        }),
      ],
    });
    viewRef.current = new EditorView({ state, parent: ref.current });
    return () => viewRef.current?.destroy();
  }, []);

  useEffect(() => {
    if (!viewRef.current) return;
    if (viewRef.current.state.doc.toString() !== value) {
      viewRef.current.dispatch({
        changes: { from: 0, to: viewRef.current.state.doc.length, insert: value },
      });
    }
  }, [value]);

  return <div data-testid="editor-shell" ref={ref} className="border border-slate-200 rounded bg-white" />;
}
