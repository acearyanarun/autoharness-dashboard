// TypeScript view of the autoharness-data JSON contract (schema v1).
// Source of truth: generator/autoharness_data/schema/*.schema.json and docs/data-contract.md.
// The UI reads only these shapes; it never parses Kani output.

export const SUPPORTED_SCHEMA_MAJOR = 1;

export interface ManifestFile {
  path: string;
  schema: string;
  bytes: number;
  sha256: string;
}

export interface Manifest {
  schema_version: string;
  generator: { name: string; version: string };
  run_id: string;
  generated_at: string | null;
  status: "pass" | "fail";
  files: ManifestFile[];
}

export interface GitRef {
  repo: string | null;
  ref: string | null;
  commit: string;
  commit_is_full: boolean;
}

export interface Run {
  schema_version: string;
  run_id: string;
  provenance: "ci" | "manual";
  finished_at: string | null;
  duration_seconds: number | null;
  kani: GitRef & { version: string | null };
  library: GitRef;
  toolchain: string | null;
  target: string;
  flags: { bounded_arguments: boolean };
  command: string | null;
  host: { os: string; arch: string; cpus: number | null; memory_gb: number | null } | null;
  workflow_url: string | null;
  adapter: string;
  source_files: { role: string; name: string; sha256: string }[];
  comparability_key: string;
}

export interface Category {
  id: string;
  label: string;
  kani_variant: string;
  axis: "coverage" | "reliability";
  expected_behavior: boolean;
  umbrella: { repo: string; number: number; url: string } | null;
  match_prefixes: string[];
}

export interface Categories {
  schema_version: string;
  categories: Category[];
}

export interface Summary {
  schema_version: string;
  run_id: string;
  totals: { candidates: number; generated: number; skipped: number };
  by_category: { id: string; count: number }[];
  by_crate: { crate: string; generated: number; skipped: number }[];
  not_observable: Record<string, string>;
}

export interface FunctionIndex {
  schema_version: string;
  run_id: string;
  crates: { crate: string; path: string; generated: number; skipped: number }[];
}

export interface FunctionRecord {
  name: string;
  status: "generated" | "skipped";
  category?: string;
  detail?: string;
  args?: { name: string; type: string }[];
}

export interface CrateShard {
  schema_version: string;
  run_id: string;
  crate: string;
  functions: FunctionRecord[];
}

export interface ValidationCheck {
  id: string;
  severity: "error" | "warning";
  status: "pass" | "fail" | "skipped";
  message: string;
  expected?: unknown;
  actual?: unknown;
}

export interface Validation {
  schema_version: string;
  run_id: string;
  status: "pass" | "fail";
  counts: { pass: number; fail: number; skipped: number };
  checks: ValidationCheck[];
}

/** Everything the dashboard needs up front. Function shards are loaded on demand. */
export interface Dataset {
  baseUrl: string;
  manifest: Manifest;
  run: Run;
  summary: Summary;
  categories: Categories;
  index: FunctionIndex;
  validation: Validation;
  integrity: "verified" | "unavailable";
}
