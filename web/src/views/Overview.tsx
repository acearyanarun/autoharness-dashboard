import { Badge, Card, StatusBadge, Swatch } from "../components/Common";
import { DataNotice } from "../components/DataNotice";
import type { Dataset } from "../data/contract";
import { categoryRows, commitUrl, formatRunDate, nf, pct, runLabel, shortSha } from "../data/derive";
import { href } from "../router";

const TOP_CRATES = 8;

function Commit({ repo, commit, full }: { repo: string | null; commit: string; full: boolean }) {
  const url = full ? commitUrl(repo, commit) : null;
  const text = <code>{shortSha(commit)}</code>;
  return (
    <>
      {url ? <a href={url} target="_blank" rel="noreferrer">{text}</a> : text}
      {!full && <span className="hint"> (short SHA)</span>}
    </>
  );
}

export function Overview({ ds }: { ds: Dataset }) {
  const { totals } = ds.summary;
  const rows = categoryRows(ds);
  const v = ds.validation;
  const crates = [...ds.summary.by_crate].sort((a, b) => b.generated + b.skipped - (a.generated + a.skipped));
  const top = crates.slice(0, TOP_CRATES);
  const rest = crates.slice(TOP_CRATES);
  const restRow = rest.length
    ? { crate: `${rest.length} other crates`, generated: rest.reduce((n, c) => n + c.generated, 0), skipped: rest.reduce((n, c) => n + c.skipped, 0), other: true }
    : null;
  const maxCrate = Math.max(...[...top, ...(restRow ? [restRow] : [])].map((c) => c.generated + c.skipped), 1);

  return (
    <main className="page">
      <div className="page-head">
        <div>
          <h1>AutoHarness coverage of the Rust standard library</h1>
          <p>
            For every function in verify-rust-std's library, Kani's AutoHarness either generates a proof harness
            or skips the function with a reason. Generated means a harness could be built; it does not mean the
            function verified.
          </p>
        </div>
        <Badge kind="neutral">{runLabel(ds.run)}</Badge>
      </div>

      <DataNotice run={ds.run} />

      <div className="grid-tiles" role="list" aria-label="Key metrics">
        <div className="card tile" role="listitem" data-testid="tile-candidates">
          <span className="tile-label">Candidates</span>
          <span className="tile-value">{nf.format(totals.candidates)}</span>
          <span className="tile-note">functions AutoHarness considered</span>
        </div>
        <div className="card tile" role="listitem" data-testid="tile-generated">
          <span className="tile-label"><Swatch color="var(--generated)" />Generated</span>
          <span className="tile-value">{nf.format(totals.generated)}</span>
          <span className="tile-note">harness produced</span>
        </div>
        <div className="card tile" role="listitem" data-testid="tile-skipped">
          <span className="tile-label">Skipped</span>
          <span className="tile-value">{nf.format(totals.skipped)}</span>
          <span className="tile-note">across {rows.length} root causes</span>
        </div>
        <div className="card tile" role="listitem" data-testid="tile-rate">
          <span className="tile-label">Generation rate</span>
          <span className="tile-value">{pct(totals.generated, totals.candidates)}</span>
          <span className="tile-note">generated ÷ candidates</span>
        </div>
        <div className="card tile" role="listitem" data-testid="tile-validation">
          <span className="tile-label">Validation</span>
          <span className="tile-value" style={{ fontSize: 20 }}><StatusBadge status={v.status} /></span>
          <span className="tile-note">
            {v.counts.pass} checks passed{v.counts.skipped ? `, ${v.counts.skipped} not applicable` : ""} ·{" "}
            <a href={href("about")}>details</a>
          </span>
        </div>
      </div>

      <div className="grid-2">
        <Card title="Where the candidates went" subtitle="Each segment is a share of all candidates.">
          <div className="card-pad" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div className="stack" role="img"
                 aria-label={`Generated ${nf.format(totals.generated)}; ` + rows.map((r) => `${r.category.label} ${nf.format(r.count)}`).join("; ")}>
              <span style={{ width: `${(totals.generated / totals.candidates) * 100}%`, background: "var(--generated)" }}
                    title={`Generated: ${nf.format(totals.generated)} (${pct(totals.generated, totals.candidates)})`} />
              {rows.filter((r) => r.count > 0).map((r) => (
                <span key={r.category.id} style={{ width: `${(r.count / totals.candidates) * 100}%`, background: `var(--s${r.slot})` }}
                      title={`${r.category.label}: ${nf.format(r.count)} (${pct(r.count, totals.candidates)})`} />
              ))}
            </div>
            <div className="legend">
              <span><Swatch color="var(--generated)" />Generated</span>
              {rows.map((r) => (
                <span key={r.category.id}><Swatch slot={r.slot} />{r.category.label}</span>
              ))}
            </div>
            <table className="crate-table" style={{ marginTop: 4 }}>
              <thead>
                <tr><th style={{ paddingLeft: 0 }}>Skip reason</th><th className="num">Functions</th><th className="num">of skipped</th><th>Umbrella</th></tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.category.id}>
                    <td style={{ paddingLeft: 0 }}>
                      <a href={href("coverage", { category: r.category.id })} style={{ color: "inherit", display: "inline-flex", alignItems: "center", gap: 8 }}>
                        <Swatch slot={r.slot} />{r.category.label}
                      </a>
                    </td>
                    <td className="num">{nf.format(r.count)}</td>
                    <td className="num">{pct(r.count, totals.skipped)}</td>
                    <td>{r.category.umbrella ? <a href={r.category.umbrella.url} target="_blank" rel="noreferrer">#{r.category.umbrella.number}</a> : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <a className="btn" href={href("coverage")} style={{ alignSelf: "flex-start" }}>Explore the coverage tree →</a>
          </div>
        </Card>

        <Card title="Run information" subtitle="What was measured, and with what.">
          <dl className="kv" data-testid="run-info">
            <dt>Data</dt><dd>{runLabel(ds.run)}</dd>
            <dt>Kani revision</dt>
            <dd><Commit repo={ds.run.kani.repo} commit={ds.run.kani.commit} full={ds.run.kani.commit_is_full} />
              {ds.run.kani.version && <span className="hint"> · Kani {ds.run.kani.version}</span>}</dd>
            <dt>verify-rust-std</dt>
            <dd><Commit repo={ds.run.library.repo} commit={ds.run.library.commit} full={ds.run.library.commit_is_full} />
              {ds.run.library.ref && <span className="hint"> · {ds.run.library.ref}</span>}</dd>
            <dt>Toolchain</dt><dd>{ds.run.toolchain ?? "not recorded"}</dd>
            <dt>Target</dt><dd><code>{ds.run.target}</code></dd>
            <dt>Run date</dt><dd>{formatRunDate(ds.run.finished_at)}</dd>
            <dt>Bounded arguments</dt><dd>{ds.run.flags.bounded_arguments ? "Enabled" : "Disabled"}</dd>
            <dt>Provenance</dt><dd>{ds.run.provenance === "manual" ? "Manual (recorded by hand)" : "CI"}</dd>
            <dt>Data schema</dt><dd>v{ds.manifest.schema_version} · generator {ds.manifest.generator.version}</dd>
          </dl>
        </Card>
      </div>

      <Card title="By crate" subtitle={`The ${Math.min(TOP_CRATES, crates.length)} largest crates by candidate count${rest.length ? `; ${rest.length} smaller crates combined` : ""}.`}>
        <table className="crate-table" style={{ marginTop: 8 }}>
          <thead>
            <tr><th>Crate</th><th style={{ width: "40%" }}>Generated / skipped</th><th className="num">Generated</th><th className="num">Skipped</th><th className="num">Rate</th></tr>
          </thead>
          <tbody>
            {[...top, ...(restRow ? [restRow] : [])].map((c) => {
              const total = c.generated + c.skipped;
              const isOther = "other" in c;
              return (
                <tr key={c.crate}>
                  <td>{isOther ? <span className="hint">{c.crate}</span> : <a href={href("functions", { crate: c.crate })}><code>{c.crate}</code></a>}</td>
                  <td>
                    <div className="minibar" style={{ width: `${(total / maxCrate) * 100}%` }} title={`${nf.format(c.generated)} generated, ${nf.format(c.skipped)} skipped`}>
                      <span style={{ width: `${(c.generated / total) * 100}%`, background: "var(--generated)" }} />
                      <span style={{ width: `${(c.skipped / total) * 100}%`, background: "var(--skipped)" }} />
                    </div>
                  </td>
                  <td className="num">{nf.format(c.generated)}</td>
                  <td className="num">{nf.format(c.skipped)}</td>
                  <td className="num">{pct(c.generated, total)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <div className="legend" style={{ padding: "10px 18px 14px" }}>
          <span><Swatch color="var(--generated)" />Generated</span>
          <span><Swatch color="var(--skipped)" />Skipped (all reasons)</span>
        </div>
      </Card>
    </main>
  );
}
