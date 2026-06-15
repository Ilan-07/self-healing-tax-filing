const agents = [
  ["01", "Reading", "OCR + vision"],
  ["02", "Tax Processing", "Rule engine"],
  ["03", "Verification", "Confidence"],
  ["04", "Remediation", "Self-healing"],
  ["05", "Documentation", "PDF report"],
];

export function AgentPipeline({ active }: { active?: string }) {
  const activeIndex = {
    parsing: 0,
    calculating: 1,
    verifying: 2,
    remediating: 3,
    completed: 4,
  }[active ?? ""] ?? -1;

  return (
    <section className="pipeline" aria-label="Agent workflow">
      {agents.map(([number, title, subtitle], index) => (
        <div
          className={`agent-card ${index <= activeIndex ? "active" : ""}`}
          key={title}
        >
          <span className="agent-number">{number}</span>
          <div>
            <strong>{title}</strong>
            <small>{subtitle}</small>
          </div>
        </div>
      ))}
    </section>
  );
}
