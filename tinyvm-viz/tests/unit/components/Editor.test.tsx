import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Editor } from "@/components/Editor";

describe("Editor", () => {
  it("renders the CodeMirror editor shell", () => {
    render(<Editor value="" onChange={() => {}} />);
    expect(screen.getByTestId("editor-shell")).toBeInTheDocument();
  });

  it("renders without crashing on invalid source", () => {
    render(<Editor value="FOO R0\n" onChange={() => {}} />);
    expect(screen.getByTestId("editor-shell")).toBeInTheDocument();
  });
});
