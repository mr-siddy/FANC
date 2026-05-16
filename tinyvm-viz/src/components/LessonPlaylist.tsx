import type { Lesson } from "@/lessons";

interface LessonPlaylistProps {
  lessons: readonly Lesson[];
  selectedId: string;
  onSelect: (id: string) => void;
}

export function LessonPlaylist({ lessons, selectedId, onSelect }: LessonPlaylistProps) {
  return (
    <nav className="space-y-1">
      {lessons.map((l) => {
        const sel = l.id === selectedId;
        return (
          <button
            key={l.id}
            onClick={() => onSelect(l.id)}
            className={`w-full text-left px-2 py-1 rounded text-sm ${
              sel ? "bg-slate-200 text-slate-900" : "hover:bg-slate-100 text-slate-700"
            }`}
          >
            <div>{l.title}</div>
            <div className="text-xs text-slate-500">{l.summary}</div>
          </button>
        );
      })}
    </nav>
  );
}
