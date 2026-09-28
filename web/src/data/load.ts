// Loads and checks a dataset. This is the only module that fetches.
//
// Refuses (throws DatasetError) when:
//   - manifest.json cannot be fetched or parsed,
//   - the schema major version is not supported,
//   - manifest.status is not "pass"  (the generator's own verdict),
//   - a file listed in the manifest is missing, or its sha256 does not match,
//   - run_id differs between files (mixed datasets),
//   - summary totals do not add up.
// A refused dataset is never rendered as metrics.

import type {
  Categories,
  CrateShard,
  Dataset,
  FunctionIndex,
  Manifest,
  Run,
  Summary,
  Validation,
} from "./contract";
import { SUPPORTED_SCHEMA_MAJOR } from "./contract";

export type DatasetErrorKind =
  | "unreachable"
  | "malformed"
  | "unsupported-schema"
  | "validation-failed"
  | "integrity"
  | "inconsistent";

export class DatasetError extends Error {
  constructor(
    public kind: DatasetErrorKind,
    message: string,
    /** Failed checks from validation.json, when the dataset was refused for that reason. */
    public failedChecks: { id: string; message: string }[] = [],
  ) {
    super(message);
    this.name = "DatasetError";
  }
}

/** Where the data lives: ?data=<url> overrides; default is "data/" next to index.html. */
export function resolveDataBase(location: Pick<Location, "href" | "search">): string {
  const override = new URLSearchParams(location.search).get("data");
  const base = new URL(override ?? "data/", location.href).toString();
  return base.endsWith("/") ? base : `${base}/`;
}

async function fetchBytes(url: string): Promise<ArrayBuffer> {
  let res: Response;
  try {
    res = await fetch(url, { cache: "no-cache" });
  } catch (e) {
    throw new DatasetError("unreachable", `Could not fetch ${url}: ${(e as Error).message}`);
  }
  if (!res.ok) throw new DatasetError("unreachable", `Could not fetch ${url}: HTTP ${res.status}`);
  return res.arrayBuffer();
}

function parseJson<T>(bytes: ArrayBuffer, name: string): T {
  try {
    return JSON.parse(new TextDecoder("utf-8").decode(bytes)) as T;
  } catch {
    throw new DatasetError("malformed", `${name} is not valid JSON`);
  }
}

async function sha256Hex(bytes: ArrayBuffer): Promise<string | null> {
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) return null; // insecure context (plain http, non-localhost)
  const digest = await subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

function requireSchema(version: unknown, name: string) {
  if (typeof version !== "string" || !/^\d+\.\d+\.\d+$/.test(version)) {
    throw new DatasetError("malformed", `${name} has no valid schema_version`);
  }
  const major = Number(version.split(".")[0]);
  if (major !== SUPPORTED_SCHEMA_MAJOR) {
    throw new DatasetError(
      "unsupported-schema",
      `${name} uses schema ${version}; this dashboard supports ${SUPPORTED_SCHEMA_MAJOR}.x`,
    );
  }
}

/** Fetch one file listed in the manifest, verifying its hash when the browser allows it. */
async function fetchListed<T>(
  base: string,
  manifest: Manifest,
  path: string,
  integrity: { available: boolean },
): Promise<T> {
  const entry = manifest.files.find((f) => f.path === path);
  if (!entry) throw new DatasetError("inconsistent", `manifest.json does not list ${path}`);
  const bytes = await fetchBytes(new URL(path, base).toString());
  const digest = await sha256Hex(bytes);
  if (digest === null) integrity.available = false;
  else if (digest !== entry.sha256) {
    throw new DatasetError("integrity", `${path} does not match the sha256 recorded in manifest.json`);
  }
  const doc = parseJson<T & { schema_version?: string; run_id?: string }>(bytes, path);
  requireSchema(doc.schema_version, path);
  if (doc.run_id !== undefined && doc.run_id !== manifest.run_id) {
    throw new DatasetError("inconsistent", `${path} belongs to run ${doc.run_id}, manifest is ${manifest.run_id}`);
  }
  return doc;
}

export async function loadDataset(base: string): Promise<Dataset> {
  const manifest = parseJson<Manifest>(await fetchBytes(new URL("manifest.json", base).toString()), "manifest.json");
  if (!manifest || typeof manifest !== "object" || !Array.isArray(manifest.files)) {
    throw new DatasetError("malformed", "manifest.json is missing required fields");
  }
  requireSchema(manifest.schema_version, "manifest.json");

  const integrity = { available: true };

  if (manifest.status !== "pass") {
    // Show why, if validation.json is readable, but never render the metrics.
    let failed: { id: string; message: string }[] = [];
    try {
      const v = await fetchListed<Validation>(base, manifest, "validation.json", integrity);
      failed = v.checks.filter((c) => c.status === "fail").map(({ id, message }) => ({ id, message }));
    } catch {
      /* the refusal below is what matters */
    }
    throw new DatasetError(
      "validation-failed",
      `This dataset did not pass validation (manifest status: ${JSON.stringify(manifest.status)}). ` +
        "Its numbers are not shown.",
      failed,
    );
  }

  const [run, summary, categories, index, validation] = await Promise.all([
    fetchListed<Run>(base, manifest, "run.json", integrity),
    fetchListed<Summary>(base, manifest, "summary.json", integrity),
    fetchListed<Categories>(base, manifest, "categories.json", integrity),
    fetchListed<FunctionIndex>(base, manifest, "functions/index.json", integrity),
    fetchListed<Validation>(base, manifest, "validation.json", integrity),
  ]);

  if (validation.status !== "pass") {
    throw new DatasetError("validation-failed", "validation.json reports a failure although the manifest says pass");
  }
  const t = summary.totals;
  if (t.generated + t.skipped !== t.candidates) {
    throw new DatasetError("inconsistent", "summary totals do not add up (generated + skipped ≠ candidates)");
  }
  const catSum = summary.by_category.reduce((n, c) => n + c.count, 0);
  if (catSum !== t.skipped) {
    throw new DatasetError("inconsistent", "category counts do not add up to the skipped total");
  }

  return {
    baseUrl: base,
    manifest,
    run,
    summary,
    categories,
    index,
    validation,
    integrity: integrity.available ? "verified" : "unavailable",
  };
}

const shardCache = new Map<string, Promise<CrateShard>>();

/** Lazily load one crate's function file (cached per dataset + crate). */
export function loadCrate(dataset: Dataset, crate: string): Promise<CrateShard> {
  const entry = dataset.index.crates.find((c) => c.crate === crate);
  if (!entry) return Promise.reject(new DatasetError("inconsistent", `Unknown crate ${crate}`));
  const key = `${dataset.baseUrl}|${dataset.manifest.run_id}|${crate}`;
  let p = shardCache.get(key);
  if (!p) {
    p = fetchListed<CrateShard>(dataset.baseUrl, dataset.manifest, entry.path, { available: true });
    p.catch(() => shardCache.delete(key)); // allow retry after a failure
    shardCache.set(key, p);
  }
  return p;
}

export function clearShardCache() {
  shardCache.clear();
}
