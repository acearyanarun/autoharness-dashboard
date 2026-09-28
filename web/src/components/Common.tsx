import type { ReactNode } from "react";
import type { Category } from "../data/contract";

export function Swatch({ slot, color }: { slot?: number; color?: string }) {
  return <span className="swatch" aria-hidden="true" style={{ background: color ?? `var(--s${slot})` }} />;
}

export function Badge({ kind, children }: { kind: "pass" | "fail" | "neutral" | "soon"; children: ReactNode }) {
  return <span className={`badge badge-${kind}`}>{children}</span>;
}

export function StatusBadge({ status }: { status: "pass" | "fail" }) {
  return status === "pass" ? <Badge kind="pass">✓ Passed</Badge> : <Badge kind="fail">✕ Failed</Badge>;
}

export function IssueChip({ category }: { category: Category }) {
  if (!category.umbrella) return <span className="hint">no umbrella issue</span>;
  const { repo, number, url } = category.umbrella;
  const short = repo.split("/").pop();
  return (
    <a className="issue-chip" href={url} target="_blank" rel="noreferrer" title={`${repo}#${number} (opens GitHub)`}
       onClick={(e) => e.stopPropagation()}>
      <span className="repo">{short}</span>#{number}
    </a>
  );
}

export function Card({ title, subtitle, children, className = "", actions }: {
  title?: ReactNode; subtitle?: ReactNode; children: ReactNode; className?: string; actions?: ReactNode;
}) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <div className="card-head">
          <div>
            {title && <h2>{title}</h2>}
            {subtitle && <p>{subtitle}</p>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}
