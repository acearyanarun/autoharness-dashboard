// Pure presentation helpers: everything computed from the contract lives here, so views
// never hard-code numbers and tests can check the arithmetic directly.

import type { Category, Dataset, Run } from "./contract";

export const nf = new Intl.NumberFormat("en-US");

/** Percentage with one decimal; "–" when the denominator is zero. */
export function pct(part: number, whole: number): string {
  if (!whole) return "–";
  return `${((part / whole) * 100).toFixed(1)}%`;
}

export interface CategoryRow {
  category: Category;
  count: number;
  slot: number; // 1-based categorical color slot, by config order (color follows the entity)
}

/** Categories in the contract's order, each with its count (zero if absent). */
export function categoryRows(ds: Dataset): CategoryRow[] {
  const counts = new Map(ds.summary.by_category.map((c) => [c.id, c.count]));
  return ds.categories.categories.map((category, i) => ({
    category,
    count: counts.get(category.id) ?? 0,
    slot: (i % 8) + 1,
  }));
}

export function shortSha(commit: string): string {
  return commit.length > 12 ? commit.slice(0, 12) : commit;
}

const MONTHS = ["Jan.", "Feb.", "Mar.", "Apr.", "May", "Jun.", "Jul.", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."];

/** "2026-09-17" -> "Sept. 17, 2026"; datetimes keep their UTC time. */
export function formatRunDate(value: string | null): string {
  if (!value) return "unknown date";
  const m = /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?/.exec(value);
  if (!m) return value;
  const date = `${MONTHS[Number(m[2]) - 1]} ${Number(m[3])}, ${m[1]}`;
  return m[4] ? `${date}, ${m[4]}:${m[5]} UTC` : date;
}

/** Human label for where the data came from. Never claims "live". */
export function runLabel(run: Run): string {
  const when = formatRunDate(run.finished_at);
  return run.provenance === "manual" ? `Controlled baseline — ${when}` : `Automated run — ${when}`;
}

export function commitUrl(repo: string | null, commit: string): string | null {
  return repo ? `https://github.com/${repo}/commit/${commit}` : null;
}
