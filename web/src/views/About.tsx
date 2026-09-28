import { Badge, Card, StatusBadge } from "../components/Common";
import { DataNotice } from "../components/DataNotice";
import type { Dataset } from "../data/contract";
import { formatRunDate, nf, runLabel } from "../data/derive";

const AUTOMATED_TODAY = [
  "Parsing Kani's AutoHarness listing into per-function records",
  "Classifying every skip into exactly one category (unknown Kani wording fails the build)",
  "Validating counts, schemas and consistency; refusing to publish a failed dataset",
  "Emitting deterministic, hashed, versioned JSON (the contract this page reads)",
  "Rendering this dashboard from that JSON, with no numbers in the UI code",
  "Tests, data verification, frontend build and Pages deployment are configured in GitHub Actions (.github/workflows/ci.yml)",
];

const NOT_YET = [
  ["Automated Kani measurement", "Running AutoHarness on verify-rust-std in GitHub Actions at chosen Kani / library revisions."],
  ["Live GitHub issue & PR sync", "Fetching umbrella and child issue state and linked PRs. Issue links on this site are static."],
  ["History and run comparison", "Keeping past runs and showing what changed between comparable runs."],
  ["Reliability view", "Crashes/ICEs, soundness and tooling issues from the #4879 index."],
];

export function About({ ds }: { ds: Dataset }) {
  const v = ds.validation;
  const notApplicable = v.checks.filter((c) => c.status === "skipped");
  const failed = v.checks.filter((c) => c.status === "fail");
  const groups = new Map<string, number>();
  for (const c of v.checks.filter((c) => c.status === "pass")) {
    const g = c.id.split(/[.:]/)[0];
    groups.set(g, (groups.get(g) ?? 0) + 1);
  }
  const src = ds.run.source_files;

  return (
    <main className="page">
      <div className="page-head">
        <div>
          <h1>About this data</h1>
          <p>Where the numbers come from, how they were checked, and what is and is not automated yet.</p>
        </div>
      </div>

      <DataNotice run={ds.run} />

      <div className="grid-2">
        <Card>
          <div className="card-pad prose">
            <h2>What AutoHarness measures</h2>
            <p>
              Kani's <code>autoharness</code> subcommand tries to generate a proof harness for every function it finds.
              For each function it either generates a harness or records a reason for skipping it. This dashboard
              counts those outcomes for the Rust standard library (verify-rust-std) and groups every skip reason
              into one of the categories tracked by an umbrella issue in the Kani repository.
            </p>

            <h2>Where this dataset came from</h2>
            <ul>
              <li><b>{runLabel(ds.run)}</b> ({ds.run.provenance === "manual" ? "recorded by hand, not by CI" : "CI run"}).</li>
              <li>Kani <code>{ds.run.kani.commit}</code>{ds.run.kani.version ? ` (${ds.run.kani.version})` : ""} on verify-rust-std <code>{ds.run.library.commit}</code>{ds.run.library.ref ? ` (${ds.run.library.ref})` : ""}, target <code>{ds.run.target}</code>, toolchain {ds.run.toolchain ?? "not recorded"}.</li>
              <li>Command: {ds.run.command ? <code>{ds.run.command}</code> : <span>not recorded for this run</span>}. Bounded arguments: {ds.run.flags.bounded_arguments ? "enabled" : "disabled"}.</li>
              <li>
                Generator input: <code>{ds.run.adapter}</code>
                {src.map((s) => <span key={s.name}> · {s.name} (<code>{s.sha256.slice(0, 12)}…</code>)</span>)}.
                {ds.run.adapter === "per-function-json-v1" && (
                  <> This dataset was rebuilt from the baseline's per-function output because the original raw Kani
                  listing has not been located yet; checks against Kani's own printed totals are therefore not applicable.</>
                )}
              </li>
            </ul>

            <h2>How the generator works</h2>
            <div className="pipeline" aria-label="Pipeline">
              <span>Kani AutoHarness output</span><i>→</i><span>parse</span><i>→</i><span>classify</span><i>→</i>
              <span>validate</span><i>→</i><span>versioned JSON</span><i>→</i><span>this dashboard</span>
            </div>
            <p>
              The generator is a Python package (<code>autoharness_data</code>). It never guesses: a skip reason that
              matches no configured category, a filtered run, a count that differs from Kani's own totals, or a file
              that breaks its JSON Schema fails the build. The dashboard is a separate static app that reads only the
              published JSON and refuses to show a dataset whose manifest status is not "pass".
            </p>
          </div>
        </Card>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card title="Validation" actions={<StatusBadge status={v.status} />}>
            <div className="card-pad prose" data-testid="validation-summary">
              <p>{v.counts.pass} checks passed, {v.counts.fail} failed, {v.counts.skipped} not applicable.</p>
              <ul className="checklist">
                {[...groups].map(([g, n]) => (
                  <li key={g}><Badge kind="pass">✓</Badge><span><code>{g}</code> checks: {n} passed</span></li>
                ))}
                {failed.map((c) => (
                  <li key={c.id}><Badge kind="fail">✕</Badge><span><code>{c.id}</code>: {c.message}</span></li>
                ))}
                {notApplicable.map((c) => (
                  <li key={c.id}><Badge kind="neutral">n/a</Badge><span><code>{c.id}</code>: {c.message}</span></li>
                ))}
              </ul>
              <p className="hint">
                Integrity: {ds.integrity === "verified"
                  ? "every file this page loaded matched the sha256 in manifest.json."
                  : "not checked (the browser does not allow hashing on this origin)."}
              </p>
            </div>
          </Card>

          <Card title="Automation status">
            <div className="card-pad prose">
              <h3>Automated today</h3>
              <ul className="checklist">
                {AUTOMATED_TODAY.map((t) => <li key={t}><Badge kind="pass">✓</Badge><span>{t}</span></li>)}
              </ul>
              <h3 style={{ marginTop: 8 }}>Not automated yet</h3>
              <ul className="checklist">
                {NOT_YET.map(([t, d]) => (
                  <li key={t}><Badge kind="soon">Coming next</Badge><span><b>{t}.</b> {d}</span></li>
                ))}
              </ul>
            </div>
          </Card>
        </div>
      </div>

      <Card title="Dataset files" subtitle={`Schema v${ds.manifest.schema_version} · generator ${ds.manifest.generator.name} ${ds.manifest.generator.version} · run ${ds.manifest.run_id} · generated ${formatRunDate(ds.manifest.generated_at)}`}>
        <table className="hash-table" style={{ marginTop: 8 }}>
          <thead><tr><th>File</th><th>Size</th><th>sha256</th></tr></thead>
          <tbody>
            {ds.manifest.files.map((f) => (
              <tr key={f.path}>
                <td><a href={new URL(f.path, ds.baseUrl).toString()}><code>{f.path}</code></a></td>
                <td>{nf.format(f.bytes)} B</td>
                <td className="mono">{f.sha256}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </main>
  );
}
