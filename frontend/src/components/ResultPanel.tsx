import type { SubmissionResult } from "../types/tax";

const money = (value?: string) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(Number(value ?? 0));

export function ResultPanel({ result }: { result: SubmissionResult }) {
  const calculation = result.calculation;
  const verification = result.verification;
  return (
    <section className="results">
      <div className="result-heading">
        <div>
          <span className={`status status-${result.status}`}>
            {result.status.replace("_", " ")}
          </span>
          <h2>Submission intelligence</h2>
          <p>{result.submission_id}</p>
        </div>
        {verification && (
          <div className="confidence">
            <strong>{Math.round(verification.confidence_score * 100)}%</strong>
            <span>confidence</span>
          </div>
        )}
      </div>

      {result.error && <div className="alert">{result.error}</div>}

      {result.extracted_data && (
        <div className="data-grid">
          <article>
            <span>Taxpayer</span>
            <strong>{result.extracted_data.employee_name || "Needs review"}</strong>
            <small>{result.extracted_data.employer_name}</small>
          </article>
          <article>
            <span>Gross income</span>
            <strong>{money(calculation?.gross_income)}</strong>
            <small>Tax year {result.extracted_data.tax_year}</small>
          </article>
          <article>
            <span>Federal tax</span>
            <strong>{money(calculation?.federal_tax)}</strong>
            <small>Deterministic calculation</small>
          </article>
          <article className="accent">
            <span>{Number(calculation?.refund) > 0 ? "Refund" : "Tax due"}</span>
            <strong>
              {money(
                Number(calculation?.refund) > 0
                  ? calculation?.refund
                  : calculation?.tax_due,
              )}
            </strong>
            <small>{result.receipt?.reference_number ?? "Pending verification"}</small>
          </article>
        </div>
      )}

      {verification?.errors.length ? (
        <div className="review-box">
          <strong>Review signals</strong>
          {verification.errors.map((error) => (
            <p key={error}>{error}</p>
          ))}
        </div>
      ) : null}

      <div className="audit">
        <h3>Agent decision log</h3>
        {result.audit_trail.map((entry, index) => (
          <div className="audit-row" key={`${entry.timestamp}-${index}`}>
            <span>{String(index + 1).padStart(2, "0")}</span>
            <div>
              <strong>{entry.agent}</strong>
              <p>{entry.reason}</p>
            </div>
            <code>{entry.action}</code>
          </div>
        ))}
      </div>

      {result.report_url && (
        <a className="download" href={result.report_url}>
          Download verified PDF report
        </a>
      )}
    </section>
  );
}
