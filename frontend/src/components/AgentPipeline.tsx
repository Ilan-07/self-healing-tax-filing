import { useEffect, useState } from "react";

const agents = [
  ["01", "Reading", "OCR + vision"],
  ["02", "Tax Processing", "Rule engine"],
  ["03", "Verification", "Confidence"],
  ["04", "Remediation", "Self-healing"],
  ["05", "Documentation", "PDF report"],
];

// The backend persists a single "processing" status until the run is terminal,
// so we show an indeterminate scanner (not a faked per-stage stepper).
const RUNNING = new Set([
  "processing",
  "parsing",
  "calculating",
  "verifying",
  "remediating",
]);

export function AgentPipeline({ status }: { status?: string }) {
  const running = !!status && RUNNING.has(status);
  const done = status === "completed";
  const halted = status === "manual_review" || status === "failed";
  const [cursor, setCursor] = useState(0);

  useEffect(() => {
    if (!running) return;
    const id = setInterval(
      () => setCursor((c) => (c + 1) % agents.length),
      1600,
    );
    return () => clearInterval(id);
  }, [running]);

  return (
    <section
      className={`pipeline${running ? " running" : ""}${halted ? " halted" : ""}`}
      aria-label="Agent workflow"
      aria-live="polite"
    >
      {agents.map(([number, title, subtitle], index) => {
        const cls = done
          ? "active"
          : running && index === cursor
            ? "scan"
            : "";
        return (
          <div className={`agent-card ${cls}`} key={title}>
            <span className="agent-number">{number}</span>
            <div>
              <strong>{title}</strong>
              <small>{cls === "scan" ? "working…" : subtitle}</small>
            </div>
          </div>
        );
      })}
    </section>
  );
}
