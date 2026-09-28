import { beforeEach, describe, expect, it } from "vitest";
import { clearShardCache, DatasetError, loadCrate, loadDataset, resolveDataBase } from "../data/load";
import { BASE, fixtureJson, serveFixture } from "./serve";

beforeEach(() => clearShardCache());

async function refusal(p: Promise<unknown>): Promise<DatasetError> {
  try {
    await p;
  } catch (e) {
    expect(e).toBeInstanceOf(DatasetError);
    return e as DatasetError;
  }
  throw new Error("expected the dataset to be refused");
}

describe("resolveDataBase", () => {
  it("defaults to data/ next to index.html, under any base path", () => {
    expect(resolveDataBase({ href: "https://x.github.io/repo/#/coverage", search: "" })).toBe("https://x.github.io/repo/data/");
    expect(resolveDataBase({ href: "https://x.github.io/a/b/index.html", search: "" })).toBe("https://x.github.io/a/b/data/");
  });
  it("accepts a ?data= override", () => {
    expect(resolveDataBase({ href: "https://x.io/app/", search: "?data=https://y.io/d" })).toBe("https://y.io/d/");
  });
});

describe("loadDataset", () => {
  it("loads and checks a valid dataset", async () => {
    serveFixture();
    const ds = await loadDataset(BASE);
    expect(ds.summary.totals).toEqual({ candidates: 14, generated: 4, skipped: 10 });
    expect(ds.categories.categories).toHaveLength(5);
    expect(ds.integrity).toBe("verified");
  });

  it("refuses a dataset whose manifest status is not pass, and reports the failed checks", async () => {
    serveFixture({
      "manifest.json": (t) => t.replace('"status": "pass"', '"status": "fail"'),
      "validation.json": (t) => t, // hash still matches, so failed checks can be read
    });
    const e = await refusal(loadDataset(BASE));
    expect(e.kind).toBe("validation-failed");
  });

  it("refuses an unreachable manifest", async () => {
    serveFixture({ "manifest.json": { status: 404 } });
    expect((await refusal(loadDataset(BASE))).kind).toBe("unreachable");
  });

  it("refuses a manifest that is not JSON", async () => {
    serveFixture({ "manifest.json": "<html>oops</html>" });
    expect((await refusal(loadDataset(BASE))).kind).toBe("malformed");
  });

  it("refuses an unsupported schema major version", async () => {
    serveFixture({ "manifest.json": (t) => t.replace('"schema_version": "1.0.0"', '"schema_version": "2.0.0"') });
    expect((await refusal(loadDataset(BASE))).kind).toBe("unsupported-schema");
  });

  it("refuses a file whose sha256 does not match the manifest", async () => {
    serveFixture({ "summary.json": (t) => t.replace('"generated": 4', '"generated": 5') });
    expect((await refusal(loadDataset(BASE))).kind).toBe("integrity");
  });

  it("loads crate files lazily and caches them", async () => {
    const requested = serveFixture();
    const ds = await loadDataset(BASE);
    expect(requested.some((p) => p.startsWith("functions/") && p !== "functions/index.json")).toBe(false);
    const core = await loadCrate(ds, "core");
    await loadCrate(ds, "core");
    expect(core.functions).toHaveLength(fixtureJson("functions/core.json").functions.length);
    expect(requested.filter((p) => p === "functions/core.json")).toHaveLength(1);
  });
});
