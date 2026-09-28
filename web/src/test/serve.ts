// Serves the fixture dataset (built by the Python generator from tests/fixtures_small) through a
// mocked fetch, optionally with per-file overrides to simulate broken or tampered datasets.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { vi } from "vitest";

export const BASE = "http://dashboard.test/data/";
const DIR = join(dirname(fileURLToPath(import.meta.url)), "fixtures", "data");

export function fixtureText(path: string): string {
  return readFileSync(join(DIR, path), "utf-8");
}
export function fixtureJson<T = any>(path: string): T {
  return JSON.parse(fixtureText(path));
}

type Override = string | { status: number } | ((original: string) => string);

/** Install a fetch mock. Returns the list of requested paths (to assert lazy loading). */
export function serveFixture(overrides: Record<string, Override> = {}) {
  const requested: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (!url.startsWith(BASE)) return new Response("not found", { status: 404 });
    const path = url.slice(BASE.length);
    requested.push(path);
    const o = overrides[path];
    if (o && typeof o === "object") return new Response("error", { status: o.status });
    let body: string;
    try {
      body = fixtureText(path);
    } catch {
      return new Response("not found", { status: 404 });
    }
    if (typeof o === "string") body = o;
    if (typeof o === "function") body = o(body);
    return new Response(body, { status: 200 });
  }));
  return requested;
}
