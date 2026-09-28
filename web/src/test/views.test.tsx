import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import App from "../App";
import { clearShardCache } from "../data/load";
import { BASE, fixtureJson, serveFixture } from "./serve";

const summary = fixtureJson("summary.json");
const categories = fixtureJson("categories.json").categories as { id: string; label: string; umbrella: { number: number; url: string } }[];

function go(hash: string) {
  window.history.replaceState(null, "", hash);
  window.dispatchEvent(new HashChangeEvent("hashchange"));
}

beforeEach(() => {
  clearShardCache();
  window.history.replaceState(null, "", "#/overview");
});

describe("Overview", () => {
  it("renders summary numbers from the data, and the baseline label", async () => {
    serveFixture();
    render(<App dataBase={BASE} />);
    const tile = await screen.findByTestId("tile-candidates");
    expect(tile).toHaveTextContent(String(summary.totals.candidates));
    expect(screen.getByTestId("tile-generated")).toHaveTextContent(String(summary.totals.generated));
    expect(screen.getByTestId("tile-skipped")).toHaveTextContent(String(summary.totals.skipped));
    // 4 / 14 = 28.6%, computed by the frontend
    expect(screen.getByTestId("tile-rate")).toHaveTextContent("28.6%");
    expect(screen.getByTestId("tile-validation")).toHaveTextContent("Passed");
    expect(screen.getAllByText(/Controlled baseline/).length).toBeGreaterThan(0);
    expect(screen.getByRole("note")).toHaveTextContent("not implemented in this version");
  });

  it("shows an error state instead of metrics when the manifest failed validation", async () => {
    serveFixture({ "manifest.json": (t) => t.replace('"status": "pass"', '"status": "fail"') });
    render(<App dataBase={BASE} />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("This dataset failed validation");
    expect(screen.queryByTestId("tile-candidates")).toBeNull();
    expect(screen.queryByText(String(summary.totals.candidates))).toBeNull();
  });

  it("shows an error state when the manifest cannot be loaded", async () => {
    serveFixture({ "manifest.json": { status: 500 } });
    render(<App dataBase={BASE} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("could not be loaded");
  });
});

describe("Coverage", () => {
  it("renders every category with count, share of skipped, and umbrella issue", async () => {
    serveFixture();
    go("#/coverage");
    render(<App dataBase={BASE} />);
    for (const c of categories) {
      const node = await screen.findByTestId(`node-${c.id}`);
      const count = summary.by_category.find((b: { id: string }) => b.id === c.id).count;
      expect(node).toHaveTextContent(c.label);
      expect(node).toHaveTextContent(String(count));
      expect(node).toHaveTextContent(`${((count / summary.totals.skipped) * 100).toFixed(1)}%`);
      expect(within(node).getByRole("link")).toHaveAttribute("href", c.umbrella.url);
    }
  });

  it("opens a detail panel with issue link and affected-functions link", async () => {
    serveFixture();
    go("#/coverage");
    render(<App dataBase={BASE} />);
    await userEvent.click(await screen.findByTestId("node-const_generic_unsupported"));
    const panel = await screen.findByTestId("detail-panel");
    expect(panel).toHaveTextContent("Non-usize const generic");
    expect(screen.getByTestId("detail-count")).toHaveTextContent("2");
    expect(screen.getByTestId("detail-share")).toHaveTextContent("20.0%"); // 2 of 10 skipped
    expect(screen.getByRole("link", { name: /View Kani issue #4889/ })).toHaveAttribute(
      "href", "https://github.com/model-checking/kani/issues/4889");
    expect(screen.getByRole("link", { name: /View 2 affected functions/ })).toHaveAttribute(
      "href", "#/functions?category=const_generic_unsupported&crate=all&status=skipped");
  });
});

describe("Functions", () => {
  it("lazily loads only the selected crate", async () => {
    const requested = serveFixture();
    go("#/functions?crate=std");
    render(<App dataBase={BASE} />);
    await waitFor(() => expect(screen.getByTestId("result-count")).toHaveTextContent("2 of 2 functions"));
    const shards = requested.filter((p) => /^functions\/(?!index)/.test(p));
    expect(shards).toEqual(["functions/std.json"]);
  });

  it("filters by status, category and text across all crates", async () => {
    serveFixture();
    go("#/functions?crate=all");
    render(<App dataBase={BASE} />);
    const count = () => screen.getByTestId("result-count");
    await waitFor(() => expect(count()).toHaveTextContent("14 of 14 functions"));

    await userEvent.selectOptions(screen.getByLabelText("Status"), "generated");
    await waitFor(() => expect(count()).toHaveTextContent("4 of 14"));

    await userEvent.selectOptions(screen.getByLabelText("Status"), "all");
    await userEvent.selectOptions(screen.getByLabelText("Skip category"), "requires_bounded_arguments");
    await waitFor(() => expect(count()).toHaveTextContent("2 of 14"));
    expect(screen.getByText("str::from_utf8")).toBeInTheDocument();
    const chips = screen.getAllByLabelText("Parsed arguments").map((el) => el.textContent);
    expect(chips).toContain("v: &[u8]"); // parsed argument chip from the contract's args field

    await userEvent.type(screen.getByLabelText("Search function or reason"), "CStr");
    await waitFor(() => expect(count()).toHaveTextContent("1 of 14"));
    expect(screen.getByText("ffi::CStr::to_str")).toBeInTheDocument();
  });
});
