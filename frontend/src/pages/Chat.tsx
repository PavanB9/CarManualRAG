import { useEffect, useRef, useState } from "react";
import { listManuals, queryManual } from "../api";
import PageImageModal from "../components/PageImageModal";
import type { ChatMessage, Manual } from "../types";

function uid() {
  return Math.random().toString(36).slice(2);
}

export default function Chat() {
  const [manuals, setManuals] = useState<Manual[]>([]);
  const [manualId, setManualId] = useState<string>("");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [openPage, setOpenPage] = useState<number | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const listEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listManuals().then((all) => {
      const ready = all.filter((m) => m.status === "ready");
      setManuals(ready);
      if (ready.length > 0) setManualId((prev) => prev || ready[0].id);
    });
  }, []);

  useEffect(() => {
    listEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    const q = question.trim();
    if (!q || !manualId) return;
    setQuestion("");

    const userMsg: ChatMessage = { id: uid(), role: "user", question: q };
    const pendingMsg: ChatMessage = { id: uid(), role: "assistant", pending: true };
    setMessages((prev) => [...prev, userMsg, pendingMsg]);

    try {
      const result = await queryManual(manualId, q);
      setMessages((prev) =>
        prev.map((m) => (m.id === pendingMsg.id ? { ...m, pending: false, result } : m))
      );
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === pendingMsg.id
            ? { ...m, pending: false, error: (err as Error).message }
            : m
        )
      );
    }
  }

  const selectedManual = manuals.find((m) => m.id === manualId);

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col gap-4 p-4">
      <div className="flex items-center gap-2">
        <label className="text-sm text-neutral-400">Manual</label>
        <select
          value={manualId}
          onChange={(e) => setManualId(e.target.value)}
          className="flex-1 rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm text-neutral-100"
        >
          {manuals.length === 0 && <option value="">No manuals ready yet</option>}
          {manuals.map((m) => (
            <option key={m.id} value={m.id}>
              {m.title}
            </option>
          ))}
        </select>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto rounded border border-neutral-800 bg-neutral-950 p-4">
        {messages.length === 0 && (
          <p className="text-sm text-neutral-500">
            Ask a question about {selectedManual?.title ?? "the manual"}.
          </p>
        )}
        {messages.map((m) =>
          m.role === "user" ? (
            <div key={m.id} className="flex justify-end">
              <div className="max-w-[80%] rounded-lg bg-blue-600 px-3 py-2 text-sm text-white">
                {m.question}
              </div>
            </div>
          ) : (
            <div key={m.id} className="flex justify-start">
              <div className="max-w-[85%] rounded-lg bg-neutral-800 px-3 py-2 text-sm text-neutral-100">
                {m.pending && <span className="text-neutral-400">Thinking…</span>}
                {m.error && <span className="text-red-400">{m.error}</span>}
                {m.result && (
                  <>
                    <p className="whitespace-pre-wrap">{m.result.answer}</p>
                    {m.result.cited_pages.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {m.result.cited_pages.map((p) => (
                          <button
                            key={p}
                            onClick={() => setOpenPage(p)}
                            className="rounded-full border border-blue-500 px-2 py-0.5 text-xs text-blue-400 hover:bg-blue-500/10"
                          >
                            p. {p}
                          </button>
                        ))}
                      </div>
                    )}
                    <div className="mt-2 flex items-center justify-between text-xs text-neutral-500">
                      <span>
                        {m.result.latency_ms} ms · ${m.result.cost_usd.toFixed(4)} ·{" "}
                        {m.result.provider}/{m.result.model}
                      </span>
                      <button
                        className="underline"
                        onClick={() => setExpanded((e) => ({ ...e, [m.id]: !e[m.id] }))}
                      >
                        {expanded[m.id] ? "hide excerpts" : "show excerpts"}
                      </button>
                    </div>
                    {expanded[m.id] && (
                      <div className="mt-2 space-y-2 border-t border-neutral-700 pt-2">
                        {m.result.chunks.map((c, i) => (
                          <div key={i} className="rounded bg-neutral-900 p-2 text-xs text-neutral-400">
                            <div className="mb-1 text-neutral-500">
                              page(s) {c.pages} · distance {c.distance.toFixed(3)}
                            </div>
                            <div className="whitespace-pre-wrap">{c.text.slice(0, 400)}…</div>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          )
        )}
        <div ref={listEndRef} />
      </div>

      <div className="flex gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask about tire pressure, oil type, warning lights…"
          disabled={!manualId}
          className="flex-1 rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={!manualId || !question.trim()}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Send
        </button>
      </div>

      {openPage !== null && manualId && (
        <PageImageModal manualId={manualId} page={openPage} onClose={() => setOpenPage(null)} />
      )}
    </div>
  );
}
