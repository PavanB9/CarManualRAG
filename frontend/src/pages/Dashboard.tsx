export default function Dashboard() {
  return (
    <div className="mx-auto max-w-3xl p-4">
      <h1 className="mb-2 text-lg font-semibold text-neutral-100">Eval Dashboard</h1>
      <p className="text-sm text-neutral-500">
        No eval runs yet. Run <code className="rounded bg-neutral-800 px-1">python eval/runner.py</code> to
        populate this page.
      </p>
    </div>
  );
}
