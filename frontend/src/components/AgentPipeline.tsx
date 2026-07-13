const agents = [
  ["01", "Reading", "OCR + vision"],
  ["02", "Tax Processing", "Rule engine"],
  ["03", "Verification", "Confidence"],
  ["04", "Remediation", "Self-healing"],
  ["05", "Documentation", "PDF report"],
];

// The backend persists a single "processing" status until the run is terminal,
// so we deliberately show an HONEST indeterminate bar rather than pretending to
// track a per-stage cursor (which would imply progress the API never reports,
// e.g. lighting up Remediation on every run when it only fires on failure).
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

  return (
    <section
      className="pipeline-wrap"
      aria-label="Agent workflow"
      aria-live="polite"
    >
      <div
        className={`pipeline${running ? " running" : ""}${halted ? " halted" : ""}`}
      >
        {agents.map(([number, title, subtitle]) => (
          <div className={`agent-card ${done ? "active" : ""}`} key={title}>
            <span className="agent-number">{number}</span>
            <div>
              <strong>{title}</strong>
              <small>{subtitle}</small>
            </div>
          </div>
        ))}
      </div>
      {running && (
        <div className="pipeline-status" role="status">
          <div className="pipeline-bar" aria-hidden="true" />
          <small>Agents working — extracting, computing, and verifying…</small>
        </div>
      )}
    </section>
  );
}
