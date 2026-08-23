import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getEvalRun, listEvalRuns } from "../api";
import type { EvalQuestionRow, EvalRunDetail, EvalRunSummary } from "../types";

const COLOR_HIT = "#3987e5"; // categorical slot 1 (blue)
const COLOR_CORRECTNESS = "#d95926"; // categorical slot 2 (orange)
const COLOR_FAITHFUL = "#199e70"; // categorical slot 3 (aqua)
const COLOR_GOOD = "#0ca30c";
const COLOR_CRITICAL = "#d03b3b";

function fmtPct(v: number | null | undefined) {
  return v == null ? "n/a" : `${(v * 100).toFixed(1)}%`;
}

function runLabel(r: EvalRunSummary) {
  if (r.label) return r.label;
  return r.timestamp ? new Date(r.timestamp).toLocaleString() : r.id;
}

type SortKey = "category" | "correctness" | "latency_ms";

export default function Dashboard() {
  const [runs, setRuns] = useState<EvalRunSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [detail, setDetail] = useState<EvalRunDetail | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("correctness");
  const [sortAsc, setSortAsc] = useState(true);

  useEffect(() => {
    listEvalRuns().then((all) => {
      setRuns(all);
      if (all.length > 0) setSelectedId((prev) => prev || all[all.length - 1].id);
    });
  }, []);

  useEffect(() => {
    if (selectedId) getEvalRun(selectedId).then(setDetail);
  }, [selectedId]);

  const trendData = useMemo(
    () =>
      runs.map((r) => ({
        name: runLabel(r),
        hit: (r.aggregates?.retrieval_hit_rate ?? 0) * 100,
        correctness: (r.aggregates?.mean_correctness ?? 0) * 100,
        faithful: (r.aggregates?.faithfulness_rate ?? 0) * 100,
      })),
    [runs]
  );

  const sortedQuestions = useMemo(() => {
    if (!detail) return [];
    const rows = [...detail.questions];
    rows.sort((a, b) => {
      let cmp = 0;
      if (sortKey === "category") cmp = a.category.localeCompare(b.category);
      else if (sortKey === "correctness") cmp = a.correctness - b.correctness;
      else cmp = a.latency_ms - b.latency_ms;
      return sortAsc ? cmp : -cmp;
    });
    return rows;
  }, [detail, sortKey, sortAsc]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortAsc((a) => !a);
    else {
      setSortKey(key);
      setSortAsc(true);
    }
  }

  if (runs.length === 0) {
    return (
      <div className="mx-auto max-w-3xl p-4">
        <h1 className="mb-2 text-lg font-semibold text-neutral-100">Eval Dashboard</h1>
        <p className="text-sm text-neutral-500">
          No eval runs yet. Run{" "}
          <code className="rounded bg-neutral-800 px-1">python eval/runner.py</code> to
          populate this page.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto h-full max-w-4xl overflow-y-auto p-4">
      <h1 className="mb-4 text-lg font-semibold text-neutral-100">Eval Dashboard</h1>

      <div className="mb-6 rounded border border-neutral-800 bg-neutral-950 p-4">
        <h2 className="mb-3 text-sm font-medium text-neutral-300">Score trend across runs</h2>
        <div style={{ width: "100%", height: 260 }}>
          <ResponsiveContainer>
            <LineChart data={trendData} margin={{ top: 4, right: 16, left: -12, bottom: 4 }}>
              <CartesianGrid stroke="#2c2c2a" vertical={false} />
              <XAxis dataKey="name" stroke="#898781" tick={{ fontSize: 11, fill: "#898781" }} />
              <YAxis
                stroke="#898781"
                tick={{ fontSize: 11, fill: "#898781" }}
                domain={[0, 100]}
                tickFormatter={(v) => `${v}%`}
              />
              <Tooltip
                contentStyle={{
                  background: "#1a1a19",
                  border: "1px solid #383835",
                  borderRadius: 6,
                  fontSize: 12,
                }}
                formatter={(v) => `${Number(v).toFixed(1)}%`}
              />
              <Legend wrapperStyle={{ fontSize: 12, color: "#c3c2b7" }} />
              <Line
                type="monotone"
                dataKey="hit"
                name="Retrieval hit rate"
                stroke={COLOR_HIT}
                strokeWidth={2}
                dot={{ r: 4 }}
              />
              <Line
                type="monotone"
                dataKey="correctness"
                name="Correctness"
                stroke={COLOR_CORRECTNESS}
                strokeWidth={2}
                dot={{ r: 4 }}
              />
              <Line
                type="monotone"
                dataKey="faithful"
                name="Faithfulness"
                stroke={COLOR_FAITHFUL}
                strokeWidth={2}
                dot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="mb-4 flex items-center gap-2">
        <label className="text-sm text-neutral-400">Run</label>
        <select
          value={selectedId}
          onChange={(e) => setSelectedId(e.target.value)}
          className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1 text-sm text-neutral-100"
        >
          {runs.map((r) => (
            <option key={r.id} value={r.id}>
              {runLabel(r)}
            </option>
          ))}
        </select>
      </div>

      {detail && (
        <>
          <div className="mb-6 grid grid-cols-3 gap-2 sm:grid-cols-6">
            <StatTile label="Retrieval hit" value={fmtPct(detail.aggregates?.retrieval_hit_rate)} />
            <StatTile
              label="Correctness"
              value={
                detail.aggregates?.mean_correctness != null
                  ? detail.aggregates.mean_correctness.toFixed(2)
                  : "n/a"
              }
            />
            <StatTile label="Faithful" value={fmtPct(detail.aggregates?.faithfulness_rate)} />
            <StatTile label="Refusal acc." value={fmtPct(detail.aggregates?.refusal_accuracy)} />
            <StatTile
              label="Avg latency"
              value={
                detail.aggregates?.mean_latency_ms != null
                  ? `${detail.aggregates.mean_latency_ms.toFixed(0)} ms`
                  : "n/a"
              }
            />
            <StatTile
              label="Avg cost"
              value={
                detail.aggregates?.mean_query_cost_usd != null
                  ? `$${detail.aggregates.mean_query_cost_usd.toFixed(5)}`
                  : "n/a"
              }
            />
          </div>

          <div className="overflow-x-auto rounded border border-neutral-800">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-neutral-800 text-neutral-400">
                  <th
                    className="cursor-pointer select-none px-3 py-2"
                    onClick={() => toggleSort("category")}
                  >
                    Category
                  </th>
                  <th className="px-3 py-2">Question</th>
                  <th className="px-3 py-2">Hit</th>
                  <th
                    className="cursor-pointer select-none px-3 py-2"
                    onClick={() => toggleSort("correctness")}
                  >
                    Correctness
                  </th>
                  <th className="px-3 py-2">Faithful</th>
                  <th
                    className="cursor-pointer select-none px-3 py-2"
                    onClick={() => toggleSort("latency_ms")}
                  >
                    Latency
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedQuestions.map((q) => (
                  <QuestionRow key={q.id} q={q} />
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-neutral-800 bg-neutral-950 p-3">
      <div className="text-[11px] text-neutral-500">{label}</div>
      <div className="mt-1 text-base font-semibold text-neutral-100" style={{ fontVariantNumeric: "tabular-nums" }}>
        {value}
      </div>
    </div>
  );
}

function QuestionRow({ q }: { q: EvalQuestionRow }) {
  const failing = q.retrieval_hit === false || q.correctness < 1 || !q.faithful;
  return (
    <tr
      className="border-b border-neutral-900"
      style={failing ? { background: "rgba(208,59,59,0.06)" } : undefined}
    >
      <td className="px-3 py-2 text-neutral-400">{q.category}</td>
      <td className="max-w-xs px-3 py-2 text-neutral-200">{q.question}</td>
      <td className="px-3 py-2">
        <Badge
          ok={q.retrieval_hit !== false}
          label={q.retrieval_hit === null ? "n/a" : q.retrieval_hit ? "hit" : "miss"}
        />
      </td>
      <td className="px-3 py-2 text-neutral-200" style={{ fontVariantNumeric: "tabular-nums" }}>
        {q.correctness.toFixed(2)}
      </td>
      <td className="px-3 py-2">
        <Badge ok={q.faithful} label={q.faithful ? "faithful" : "issue"} />
      </td>
      <td className="px-3 py-2 text-neutral-400" style={{ fontVariantNumeric: "tabular-nums" }}>
        {q.latency_ms} ms
      </td>
    </tr>
  );
}

function Badge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className="rounded px-1.5 py-0.5 text-[11px] font-medium"
      style={{
        color: ok ? COLOR_GOOD : COLOR_CRITICAL,
        background: ok ? "rgba(12,163,12,0.12)" : "rgba(208,59,59,0.12)",
      }}
    >
      {label}
    </span>
  );
}
