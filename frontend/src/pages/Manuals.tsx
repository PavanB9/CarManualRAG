import { useCallback, useEffect, useRef, useState } from "react";
import { deleteManual, listManuals, uploadManual } from "../api";
import type { Manual } from "../types";

export default function Manuals() {
  const [manuals, setManuals] = useState<Manual[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<number | null>(null);

  const refresh = useCallback(() => {
    listManuals().then(setManuals);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    const anyProcessing = manuals.some((m) => m.status === "processing");
    if (anyProcessing && pollRef.current === null) {
      pollRef.current = window.setInterval(refresh, 2000);
    } else if (!anyProcessing && pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current !== null) {
        window.clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [manuals, refresh]);

  async function handleFile(file: File) {
    setUploadError(null);
    try {
      await uploadManual(file);
      refresh();
    } catch (err) {
      setUploadError((err as Error).message);
    }
  }

  async function handleDelete(id: string) {
    await deleteManual(id);
    refresh();
  }

  return (
    <div className="mx-auto max-w-3xl p-4">
      <h1 className="mb-4 text-lg font-semibold text-neutral-100">Manuals</h1>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const file = e.dataTransfer.files?.[0];
          if (file) handleFile(file);
        }}
        onClick={() => fileInputRef.current?.click()}
        className={`mb-4 cursor-pointer rounded-lg border-2 border-dashed p-8 text-center text-sm transition-colors ${
          dragOver
            ? "border-blue-500 bg-blue-500/10 text-blue-300"
            : "border-neutral-700 text-neutral-400 hover:border-neutral-500"
        }`}
      >
        Drop a PDF here, or click to choose a file
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
            e.target.value = "";
          }}
        />
      </div>
      {uploadError && <p className="mb-4 text-sm text-red-400">{uploadError}</p>}

      <div className="space-y-2">
        {manuals.length === 0 && (
          <p className="text-sm text-neutral-500">No manuals uploaded yet.</p>
        )}
        {manuals.map((m) => (
          <div
            key={m.id}
            className="flex items-center justify-between rounded border border-neutral-800 bg-neutral-950 p-3"
          >
            <div>
              <div className="text-sm font-medium text-neutral-100">{m.title}</div>
              <div className="text-xs text-neutral-500">
                {m.status === "ready" && `${m.num_pages} pages · ${m.num_chunks} chunks`}
                {m.status === "processing" && (
                  <span className="text-yellow-400">Processing… {m.progress}%</span>
                )}
                {m.status === "error" && (
                  <span className="text-red-400">{m.error_message ?? "Error"}</span>
                )}
              </div>
              {m.status === "processing" && (
                <div className="mt-1 h-1 w-48 overflow-hidden rounded bg-neutral-800">
                  <div
                    className="h-full bg-blue-500 transition-all"
                    style={{ width: `${m.progress}%` }}
                  />
                </div>
              )}
            </div>
            <button
              onClick={() => handleDelete(m.id)}
              className="rounded px-2 py-1 text-xs text-neutral-500 hover:bg-red-500/10 hover:text-red-400"
            >
              Delete
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
