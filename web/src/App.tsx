import { useEffect, useState } from "react";
import { ErrorState } from "./components/ErrorState";
import type { Dataset } from "./data/contract";
import { loadDataset, resolveDataBase } from "./data/load";
import { href, useRoute, type View } from "./router";
import { About } from "./views/About";
import { Coverage } from "./views/Coverage";
import { Functions } from "./views/Functions";
import { Overview } from "./views/Overview";

const NAV: [View, string][] = [
  ["overview", "Overview"],
  ["coverage", "Coverage"],
  ["functions", "Functions"],
  ["about", "About / Data"],
];

type State = { status: "loading" } | { status: "ready"; ds: Dataset } | { status: "error"; error: unknown };

function readTheme(): "light" | "dark" | null {
  try {
    const t = localStorage.getItem("theme");
    return t === "light" || t === "dark" ? t : null;
  } catch {
    return null;
  }
}

function ThemeToggle() {
  const [theme, setTheme] = useState(readTheme);
  useEffect(() => {
    if (theme) document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);
  const isDark = theme ? theme === "dark" : window.matchMedia?.("(prefers-color-scheme: dark)").matches;
  const next = isDark ? "light" : "dark";
  return (
    <button className="icon-btn" aria-label={`Switch to ${next} theme`} title={`Switch to ${next} theme`}
            onClick={() => {
              setTheme(next);
              try { localStorage.setItem("theme", next); } catch { /* storage unavailable */ }
            }}>
      {isDark ? "☀" : "☾"}
    </button>
  );
}

export default function App({ dataBase }: { dataBase?: string }) {
  const route = useRoute();
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    loadDataset(dataBase ?? resolveDataBase(window.location))
      .then((ds) => !cancelled && setState({ status: "ready", ds }))
      .catch((error) => !cancelled && setState({ status: "error", error }));
    return () => { cancelled = true; };
  }, [dataBase]);

  useEffect(() => { window.scrollTo?.(0, 0); }, [route.view]);

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <a className="brand" href={href("overview")} style={{ color: "inherit", textDecoration: "none" }}>
            <span className="brand-mark" aria-hidden="true">K</span>
            AutoHarness Coverage <small>Rust std · Kani</small>
          </a>
          <nav className="nav" aria-label="Views">
            {NAV.map(([v, label]) => (
              <a key={v} href={href(v)} aria-current={route.view === v ? "page" : undefined}>{label}</a>
            ))}
            <span className="soon" aria-disabled="true" title="Not implemented yet">Issue status<em>next</em></span>
            <span className="soon" aria-disabled="true" title="Not implemented yet">History<em>next</em></span>
          </nav>
          <ThemeToggle />
        </div>
      </header>

      {state.status === "loading" && <div className="loading" role="status">Loading dataset…</div>}
      {state.status === "error" && <ErrorState error={state.error} />}
      {state.status === "ready" && (
        <>
          {route.view === "overview" && <Overview ds={state.ds} />}
          {route.view === "coverage" && <Coverage ds={state.ds} route={route} />}
          {route.view === "functions" && <Functions ds={state.ds} route={route} />}
          {route.view === "about" && <About ds={state.ds} />}
          <footer className="foot">
            <div>
              <span>Run <code>{state.ds.manifest.run_id}</code> · data schema v{state.ds.manifest.schema_version} · generator {state.ds.manifest.generator.version}</span>
              <span>Kani issue index: <a href="https://github.com/model-checking/kani/issues/4879" target="_blank" rel="noreferrer">kani#4879</a></span>
            </div>
          </footer>
        </>
      )}
    </div>
  );
}
