import { useEffect, useMemo, useState } from "react";
import { Card, Swatch } from "../components/Common";
import type { CrateShard, Dataset, FunctionRecord } from "../data/contract";
import { categoryRows, nf } from "../data/derive";
import { loadCrate } from "../data/load";
import { replaceParams, type Route } from "../router";

export const PAGE_SIZE = 50;
const ALL = "all";

interface Row extends FunctionRecord {
  crate: string;
}

type Load = { state: "loading"; crates: string[] } | { state: "ready"; rows: Row[] } | { state: "error"; message: string };

export function Functions({ ds, route }: { ds: Dataset; route: Route }) {
  const cratesBySize = useMemo(
    () => [...ds.index.crates].sort((a, b) => b.generated + b.skipped - (a.generated + a.skipped)),
    [ds],
  );
  const rows = categoryRows(ds);
  const slotOf = new Map(rows.map((r) => [r.category.id, r]));

  const p = route.params;
  const crate = p.get("crate") ?? cratesBySize[0]?.crate ?? ALL;
  const status = p.get("status") ?? ALL;
  const category = status === "generated" ? ALL : p.get("category") ?? ALL;
  const q = p.get("q") ?? "";
  const page = Math.max(1, Number(p.get("page") ?? "1") || 1);
  const [query, setQuery] = useState(q);

  const set = (patch: Record<string, string | undefined>) => {
    const next = { crate, status, category, q, page: undefined as string | undefined, ...patch };
    replaceParams("functions", {
      crate: next.crate,
      status: next.status === ALL ? undefined : next.status,
      category: next.category === ALL ? undefined : next.category,
      q: next.q || undefined,
      page: next.page && next.page !== "1" ? next.page : undefined,
    });
  };

  // Debounce free-text search into the URL.
  useEffect(() => {
    if (query === q) return;
    const t = setTimeout(() => set({ q: query }), 200);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  // Lazily load the selected crate file(s).
  const wanted = crate === ALL ? cratesBySize.map((c) => c.crate) : [crate];
  const wantedKey = wanted.join("|");
  const [load, setLoad] = useState<Load>({ state: "loading", crates: wanted });
  useEffect(() => {
    let cancelled = false;
    setLoad({ state: "loading", crates: wanted });
    Promise.all(wanted.map((c) => loadCrate(ds, c)))
      .then((shards: CrateShard[]) => {
        if (cancelled) return;
        const all: Row[] = [];
        for (const s of shards) for (const f of s.functions) all.push({ ...f, crate: s.crate });
        setLoad({ state: "ready", rows: all });
      })
      .catch((e: Error) => !cancelled && setLoad({ state: "error", message: e.message }));
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ds, wantedKey]);

  const filtered = useMemo(() => {
    if (load.state !== "ready") return [];
    const needle = q.trim().toLowerCase();
    return load.rows.filter((r) =>
      (status === ALL || r.status === status) &&
      (category === ALL || r.category === category) &&
      (!needle || r.name.toLowerCase().includes(needle) || (r.detail ?? "").toLowerCase().includes(needle)),
    );
  }, [load, status, category, q]);

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, pages);
  const visible = filtered.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE);
  const wantedBytes = ds.manifest.files.filter((f) => wanted.some((c) => f.path === `functions/${c}.json`)).reduce((n, f) => n + f.bytes, 0);

  return (
    <main className="page">
      <div className="page-head">
        <div>
          <h1>Functions</h1>
          <p>Every function in the listing, with Kani's verbatim reason for each skip. Crate files load on demand.</p>
        </div>
      </div>

      <Card>
        <div className="filters" role="search">
          <div className="field">
            <label htmlFor="f-q">Search function or reason</label>
            <input id="f-q" type="search" placeholder="e.g. ptr::, Formatter, ByteStr" value={query}
                   onChange={(e) => setQuery(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="f-crate">Crate</label>
            <select id="f-crate" value={crate} onChange={(e) => set({ crate: e.target.value })}>
              <option value={ALL}>All crates ({ds.index.crates.length} files)</option>
              {cratesBySize.map((c) => (
                <option key={c.crate} value={c.crate}>{c.crate} ({nf.format(c.generated + c.skipped)})</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="f-status">Status</label>
            <select id="f-status" value={status} onChange={(e) => set({ status: e.target.value })}>
              <option value={ALL}>Generated and skipped</option>
              <option value="generated">Generated</option>
              <option value="skipped">Skipped</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="f-cat">Skip category</label>
            <select id="f-cat" value={category} disabled={status === "generated"}
                    onChange={(e) => set({ category: e.target.value, status: e.target.value === ALL ? status : "skipped" })}>
              <option value={ALL}>All categories</option>
              {rows.map((r) => <option key={r.category.id} value={r.category.id}>{r.category.label}</option>)}
            </select>
          </div>
        </div>

        <div className="results-bar" aria-live="polite">
          <span data-testid="result-count">
            {load.state === "loading"
              ? `Loading ${load.crates.length === 1 ? load.crates[0] : `${load.crates.length} crate files`} (${(wantedBytes / 1e6).toFixed(1)} MB)…`
              : load.state === "error"
                ? "Could not load function data."
                : `${nf.format(filtered.length)} of ${nf.format(load.rows.length)} functions`}
          </span>
          {load.state === "ready" && pages > 1 && (
            <span className="pager">
              <button className="icon-btn" disabled={current <= 1} onClick={() => set({ page: String(current - 1) })}>← Prev</button>
              <span>Page {current} of {nf.format(pages)}</span>
              <button className="icon-btn" disabled={current >= pages} onClick={() => set({ page: String(current + 1) })}>Next →</button>
            </span>
          )}
        </div>

        {load.state === "error" && <p className="card-pad" role="alert" style={{ color: "var(--critical)" }}>{load.message}</p>}
        {load.state === "loading" && <div className="loading">Loading function data…</div>}
        {load.state === "ready" && (
          <table className="fn-table">
            <colgroup>
              <col style={{ width: "38%" }} /><col style={{ width: "11%" }} /><col style={{ width: "10%" }} />
              <col style={{ width: "16%" }} /><col className="col-detail" style={{ width: "25%" }} />
            </colgroup>
            <thead>
              <tr><th>Function</th><th>Crate</th><th>Status</th><th>Category</th><th className="col-detail">Kani reason</th></tr>
            </thead>
            <tbody>
              {visible.map((r) => {
                const cat = r.category ? slotOf.get(r.category) : undefined;
                return (
                  <tr key={`${r.crate}::${r.name}`}>
                    <td>
                      <div className="fn-name">{r.name}</div>
                      {r.args && r.args.length > 0 && (
                        <div className="args" aria-label="Parsed arguments">
                          {r.args.map((a, i) => <span className="arg" key={i}><b>{a.name}</b>: {a.type}</span>)}
                        </div>
                      )}
                    </td>
                    <td><code>{r.crate}</code></td>
                    <td>
                      <span className="status-dot">
                        <Swatch color={r.status === "generated" ? "var(--generated)" : "var(--skipped)"} />
                        {r.status === "generated" ? "Generated" : "Skipped"}
                      </span>
                    </td>
                    <td>{cat ? <span className="status-dot"><Swatch slot={cat.slot} />{cat.category.label}</span> : <span className="hint">—</span>}</td>
                    <td className="col-detail"><span className="fn-detail">{r.detail ?? ""}</span></td>
                  </tr>
                );
              })}
              {visible.length === 0 && (
                <tr><td colSpan={5} className="loading">No functions match these filters.</td></tr>
              )}
            </tbody>
          </table>
        )}
      </Card>
    </main>
  );
}
