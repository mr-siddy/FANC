import { Link, Route, Routes, useLocation } from "react-router-dom";
import { Playground } from "@/pages/Playground";
import { Compare } from "@/pages/Compare";

function Nav() {
  const loc = useLocation();
  const tab = (path: string, label: string) => (
    <Link
      to={path}
      className={`px-3 py-1 text-sm rounded ${loc.pathname === path ? "bg-slate-900 text-white" : "hover:bg-slate-200"}`}
    >
      {label}
    </Link>
  );
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="flex items-center gap-2 px-4 py-2">
        <h1 className="text-sm font-semibold mr-4">Tiny-VM Visualizer</h1>
        {tab("/", "Playground")}
        {tab("/compare", "Compare")}
      </div>
    </header>
  );
}

export default function App() {
  return (
    <>
      <Nav />
      <Routes>
        <Route path="/" element={<Playground />} />
        <Route path="/compare" element={<Compare />} />
      </Routes>
    </>
  );
}
