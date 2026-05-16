import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { LessonPlaylist } from "@/components/LessonPlaylist";
import { lessons } from "@/lessons";
import { parse } from "@/core/parser";
import { run } from "@/core/interpreter";

describe("LessonPlaylist", () => {
  it("lists every lesson by title", () => {
    render(<LessonPlaylist lessons={lessons} selectedId={lessons[0]!.id} onSelect={() => {}} />);
    for (const l of lessons) {
      expect(screen.getByText(l.title)).toBeInTheDocument();
    }
  });

  it("calls onSelect when a lesson is clicked", () => {
    const onSelect = vi.fn();
    render(<LessonPlaylist lessons={lessons} selectedId={lessons[0]!.id} onSelect={onSelect} />);
    fireEvent.click(screen.getByText(lessons[1]!.title));
    expect(onSelect).toHaveBeenCalledWith(lessons[1]!.id);
  });
});

describe("lesson content", () => {
  it("every lesson with a non-empty source parses, validates, and produces its expectedOutput", () => {
    for (const l of lessons) {
      if (l.source.length === 0) continue;
      const { program, errors } = parse(l.source);
      expect(errors, `errors in ${l.id}`).toEqual([]);
      const trace = run(program!);
      expect(trace.output, `output mismatch in ${l.id}`).toEqual(l.expectedOutput);
    }
  });
});
