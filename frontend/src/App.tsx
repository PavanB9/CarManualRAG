import { useState } from "react";
import Chat from "./pages/Chat";
import Manuals from "./pages/Manuals";
import Dashboard from "./pages/Dashboard";

type Tab = "chat" | "manuals" | "dashboard";

const TABS: { id: Tab; label: string }[] = [
  { id: "chat", label: "Chat" },
  { id: "manuals", label: "Manuals" },
  { id: "dashboard", label: "Dashboard" },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("chat");

  return (
    <div className="flex h-screen flex-col bg-neutral-950">
      <header className="flex items-center gap-1 border-b border-neutral-800 px-4 py-2">
        <span className="mr-4 text-sm font-semibold text-neutral-100">CarManualRAG</span>
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`rounded px-3 py-1.5 text-sm ${
              tab === t.id
                ? "bg-neutral-800 text-white"
                : "text-neutral-400 hover:text-neutral-200"
            }`}
          >
            {t.label}
          </button>
        ))}
      </header>
      <main className="flex-1 overflow-hidden">
        {tab === "chat" && <Chat />}
        {tab === "manuals" && <Manuals />}
        {tab === "dashboard" && <Dashboard />}
      </main>
    </div>
  );
}
