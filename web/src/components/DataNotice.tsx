import type { Run } from "../data/contract";
import { formatRunDate, runLabel } from "../data/derive";

/** Always-visible statement of what the data is, and what is not live yet. */
export function DataNotice({ run }: { run: Run }) {
  return (
    <div className="banner" role="note" aria-label="About this data">
      <span className="banner-icon" aria-hidden="true">ⓘ</span>
      <div>
        <p>
          <strong>{runLabel(run)}.</strong>{" "}
          {run.provenance === "manual"
            ? `Current dashboard data comes from the controlled ${formatRunDate(run.finished_at)} AutoHarness baseline, not a live Kani run.`
            : "Data from an automated measurement run."}
        </p>
        <p>
          The frontend and data pipeline are dynamic: replacing the generated JSON updates the dashboard without
          changing UI code. Automated Kani measurement and live GitHub issue synchronization are planned but are not
          implemented in this version.
        </p>
      </div>
    </div>
  );
}
