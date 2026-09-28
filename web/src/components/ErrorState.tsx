import { DatasetError } from "../data/load";

const TITLES: Record<string, string> = {
  "validation-failed": "This dataset failed validation",
  unreachable: "The dataset could not be loaded",
  malformed: "The dataset is malformed",
  "unsupported-schema": "Unsupported data format",
  integrity: "Dataset integrity check failed",
  inconsistent: "The dataset is inconsistent",
};

export function ErrorState({ error }: { error: unknown }) {
  const e = error instanceof DatasetError ? error : null;
  return (
    <main className="card state error" role="alert">
      <h1>{e ? TITLES[e.kind] : "Something went wrong"}</h1>
      <p>{e ? e.message : String(error)}</p>
      {e && e.failedChecks.length > 0 && (
        <>
          <p className="hint">Failed checks reported by the generator:</p>
          <ul>
            {e.failedChecks.map((c) => (
              <li key={c.id}><code>{c.id}</code>: {c.message}</li>
            ))}
          </ul>
        </>
      )}
      <p className="hint">
        No metrics are shown for a dataset that did not pass validation. Regenerate the data with{" "}
        <code>python -m autoharness_data build</code> and check it with <code>python -m autoharness_data verify</code>.
      </p>
    </main>
  );
}
