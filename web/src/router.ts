// Minimal hash router: "#/functions?category=no_body&crate=all".
// Hash routing keeps every URL relative, so the site works under any base path
// (GitHub Pages project sites, subdirectories) with no server rewrites.
import { useEffect, useState } from "react";

export type View = "overview" | "coverage" | "functions" | "about";
const VIEWS: View[] = ["overview", "coverage", "functions", "about"];

export interface Route {
  view: View;
  params: URLSearchParams;
}

export function parseHash(hash: string): Route {
  const raw = hash.replace(/^#\/?/, "");
  const [path, query = ""] = raw.split("?", 2);
  const view = (VIEWS as string[]).includes(path) ? (path as View) : "overview";
  return { view, params: new URLSearchParams(query) };
}

export function href(view: View, params?: Record<string, string | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params ?? {})) if (v) q.set(k, v);
  const s = q.toString();
  return `#/${view}${s ? `?${s}` : ""}`;
}

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parseHash(window.location.hash));
  useEffect(() => {
    const on = () => setRoute(parseHash(window.location.hash));
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}

/** Update query params of the current view without adding history entries. */
export function replaceParams(view: View, params: Record<string, string | undefined>) {
  const next = href(view, params);
  if (window.location.hash !== next) {
    history.replaceState(null, "", next);
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  }
}
