import type React from "react";
import { Badge, Card, IssueChip, Swatch } from "../components/Common";
import type { Dataset } from "../data/contract";
import { categoryRows, nf, pct, type CategoryRow } from "../data/derive";
import { explain } from "../data/explanations";
import { href, replaceParams, type Route } from "../router";

type Guide = "none" | "line" | "tee" | "elbow";

/** One row of the flat tree. Guides draw the connector for each ancestor level, so every
 *  row keeps the same column grid regardless of depth. */
function TreeRow({ depth, guides, selected, onSelect, testId, children }: {
  depth: number; guides: Guide[]; selected?: boolean; onSelect?: () => void; testId?: string; children: React.ReactNode;
}) {
  const inner = (
    <>
      <span className="guides" aria-hidden="true">
        {guides.map((g, i) => <span key={i} className={`guide guide-${g}`} style={{ left: i * 22 }} />)}
      </span>
      {children}
    </>
  );
  const style = { ["--depth" as string]: depth } as React.CSSProperties;
  return (
    <div role="treeitem" aria-level={depth + 1} aria-selected={selected ?? false}>
      {onSelect ? (
        <button className="node" style={style} aria-pressed={selected} onClick={onSelect} data-testid={testId}>{inner}</button>
      ) : (
        <div className="node" style={style}>{inner}</div>
      )}
    </div>
  );
}

type Selection = { kind: "generated" } | { kind: "category"; row: CategoryRow } | null;

function Bar({ value, whole, color, label }: { value: number; whole: number; color: string; label: string }) {
  const w = whole ? (value / whole) * 100 : 0;
  return (
    <span className="node-bar" aria-label={label}>
      <span className="track"><span className="fill" style={{ display: "block", width: `${w}%`, background: color }} /></span>
      <span className="share">{pct(value, whole)}</span>
    </span>
  );
}

export function Coverage({ ds, route }: { ds: Dataset; route: Route }) {
  const { totals } = ds.summary;
  const rows = categoryRows(ds);
  const selectedId = route.params.get("category");
  const sel: Selection =
    selectedId === "generated"
      ? { kind: "generated" }
      : (() => {
          const row = rows.find((r) => r.category.id === selectedId);
          return row ? { kind: "category", row } : null;
        })();
  const select = (id: string | undefined) => replaceParams("coverage", { category: id });
  const umbrellas = rows.filter((r) => r.category.umbrella).length;

  return (
    <main className="page">
      <div className="page-head">
        <div>
          <h1>Coverage decision tree</h1>
          <p>
            From measurement to root cause to the engineering issue that owns it. Every count comes from the
            generated dataset; percentages are computed here. Select a node for details.
          </p>
        </div>
      </div>

      <div className="card card-pad" aria-label="Measurement to issue" style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
        <div className="pipeline">
          <span><b>Measurement</b> · {nf.format(totals.candidates)} candidates</span><i>→</i>
          <span><b>Root cause</b> · {nf.format(totals.skipped)} skipped in {rows.length} categories</span><i>→</i>
          <span><b>Engineering issue</b> · {umbrellas} umbrella issues</span>
        </div>
      </div>

      <div className="grid-coverage">
        <Card>
          <div className="flow-head" aria-hidden="true">
            <span>Measurement / root cause</span>
            <span>Share of parent</span>
            <span>Engineering issue</span>
          </div>
          <div className="tree" role="tree" aria-label="AutoHarness coverage tree">
            <TreeRow depth={0} guides={[]}>
              <span className="node-label"><strong>All candidates</strong><span className="count">{nf.format(totals.candidates)}</span></span>
              <span className="hint">functions considered</span>
              <span />
            </TreeRow>
            <TreeRow depth={1} guides={["tee"]} selected={sel?.kind === "generated"} onSelect={() => select("generated")}>
              <span className="node-label"><Swatch color="var(--generated)" /><strong>Generated</strong><span className="count">{nf.format(totals.generated)}</span></span>
              <Bar value={totals.generated} whole={totals.candidates} color="var(--generated)" label={`Generated: ${pct(totals.generated, totals.candidates)} of candidates`} />
              <span className="hint">harness built</span>
            </TreeRow>
            <TreeRow depth={1} guides={["elbow"]}>
              <span className="node-label"><Swatch color="var(--skipped)" /><strong>Skipped</strong><span className="count">{nf.format(totals.skipped)}</span></span>
              <Bar value={totals.skipped} whole={totals.candidates} color="var(--skipped)" label={`Skipped: ${pct(totals.skipped, totals.candidates)} of candidates`} />
              <span />
            </TreeRow>
            {rows.map((r, i) => {
              const active = sel?.kind === "category" && sel.row.category.id === r.category.id;
              return (
                <TreeRow key={r.category.id} depth={2} guides={["none", i === rows.length - 1 ? "elbow" : "tee"]}
                         selected={active} onSelect={() => select(r.category.id)} testId={`node-${r.category.id}`}>
                  <span className="node-label">
                    <Swatch slot={r.slot} />
                    <strong>{r.category.label}</strong>
                    <span className="count">{nf.format(r.count)}</span>
                  </span>
                  <Bar value={r.count} whole={totals.skipped} color={`var(--s${r.slot})`}
                       label={`${r.category.label}: ${pct(r.count, totals.skipped)} of skipped`} />
                  <span className="issue-cell">
                    <IssueChip category={r.category} />
                    {r.category.expected_behavior && <span className="tag-expected">expected</span>}
                  </span>
                </TreeRow>
              );
            })}
          </div>
        </Card>

        <DetailPanel ds={ds} sel={sel} onClose={() => select(undefined)} />
      </div>
    </main>
  );
}

function DetailPanel({ ds, sel, onClose }: { ds: Dataset; sel: Selection; onClose: () => void }) {
  const { totals } = ds.summary;
  if (!sel) {
    return (
      <Card className="detail">
        <div className="empty-detail">
          <p><b>Select a category</b> in the tree to see its count, share, explanation, umbrella issue and affected functions.</p>
        </div>
      </Card>
    );
  }

  if (sel.kind === "generated") {
    return (
      <Card className="detail">
        <div className="detail-head" data-testid="detail-panel">
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span className="hint">Measurement</span>
            <button className="icon-btn" onClick={onClose} aria-label="Close details">✕</button>
          </div>
          <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}><Swatch color="var(--generated)" />Generated</h2>
        </div>
        <div className="detail-body">
          <div className="detail-stats">
            <div><b>{nf.format(totals.generated)}</b><span>functions</span></div>
            <div><b>{pct(totals.generated, totals.candidates)}</b><span>of candidates</span></div>
          </div>
          <p>AutoHarness built a proof harness for these functions. This measures generation only: whether each harness then verifies is a separate question this dataset does not answer.</p>
          <div className="actions">
            <a className="btn btn-primary" href={href("functions", { status: "generated", crate: "all" })}>View generated functions</a>
          </div>
        </div>
      </Card>
    );
  }

  const { row } = sel;
  const c = row.category;
  const ex = explain(c.id);
  return (
    <Card className="detail">
      <div className="detail-head" data-testid="detail-panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span className="hint">Root cause · <code>{c.kani_variant}</code></span>
          <button className="icon-btn" onClick={onClose} aria-label="Close details">✕</button>
        </div>
        <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}><Swatch slot={row.slot} />{c.label}</h2>
        <p className="hint" style={{ color: "var(--ink-2)" }}>{ex.summary}</p>
        {c.expected_behavior && <div><Badge kind="neutral">Expected behaviour, not a bug</Badge></div>}
      </div>
      <div className="detail-body">
        <div className="detail-stats">
          <div><b data-testid="detail-count">{nf.format(row.count)}</b><span>functions</span></div>
          <div><b data-testid="detail-share">{pct(row.count, totals.skipped)}</b><span>of skipped · {pct(row.count, totals.candidates)} of candidates</span></div>
        </div>
        <p>{ex.detail(ds.run)}</p>
        <p><b style={{ color: "var(--ink)" }}>Direction:</b> {ex.fix}</p>
        <div>
          <h3 style={{ marginBottom: 6 }}>Umbrella issue</h3>
          {c.umbrella ? (
            <p><code>{c.umbrella.repo}#{c.umbrella.number}</code>
              <span className="hint"> · issue status is not synced yet; open the issue for its current state.</span></p>
          ) : <p className="hint">No umbrella issue is configured for this category.</p>}
        </div>
        <div className="actions">
          {c.umbrella && (
            <a className="btn" href={c.umbrella.url} target="_blank" rel="noreferrer">View Kani issue #{c.umbrella.number} ↗</a>
          )}
          <a className="btn btn-primary" href={href("functions", { category: c.id, crate: "all", status: "skipped" })}>
            View {nf.format(row.count)} affected functions
          </a>
        </div>
        <details>
          <summary className="hint" style={{ cursor: "pointer" }}>How functions are assigned here</summary>
          <p className="hint" style={{ marginTop: 6 }}>Kani's reason text starts with:</p>
          <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
            {c.match_prefixes.map((p) => <li key={p}><code>{p}</code></li>)}
          </ul>
        </details>
      </div>
    </Card>
  );
}
