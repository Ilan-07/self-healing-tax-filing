import type { SubmissionResult } from "../types/tax";

const money = (value?: string) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(Number(value ?? 0));

const num = (value?: string) => Number(value ?? 0);

const CHECK_LABELS: Record<string, string> = {
  taxpayer_name: "Taxpayer name",
  taxpayer_ssn: "Taxpayer SSN",
  income: "Income present",
  withholding_bounds: "Withholding bounds",
  w2_social_security_invariant: "SS withholding check",
  w2_medicare_invariant: "Medicare withholding check",
  calculation_replay: "Independent recompute",
  source_grounding: "Source grounding",
  params_verified: "Verified tax parameters",
  completeness: "Completeness",
};

export function ResultPanel({ result }: { result: SubmissionResult }) {
  const calc = result.calculation;
  const v = result.verification;
  const isRefund = num(calc?.refund) >= num(calc?.tax_due);
  const checks = v?.checks ?? [];
  const failedChecks = checks.filter((c) => !c.passed);
  const needsReview =
    result.status === "manual_review" || result.status === "failed";

  const breakdown: [string, string | undefined, boolean][] = calc
    ? [
        ["Total income", calc.total_income ?? calc.gross_income, false],
        ["Adjustments", calc.adjustments, false],
        ["Adjusted gross income", calc.adjusted_gross_income, true],
        ["Deductions", calc.deductions, false],
        ["QBI deduction", calc.qbi_deduction, false],
        ["Taxable income", calc.taxable_income, true],
        ["Tax before credits", calc.income_tax_before_credits, false],
        ["Credits", calc.nonrefundable_credits, false],
        ["Other taxes", calc.other_taxes, false],
        ["Total tax", calc.federal_tax, true],
        ["Total payments", calc.total_payments, false],
      ]
    : [];

  return (
    <section className="results">
      <div className="result-heading">
        <div>
          <span className={`status status-${result.status}`}>
            {result.status.replace("_", " ")}
          </span>
          <h2>Submission intelligence</h2>
          <p className="sub-id">{result.submission_id}</p>
        </div>
        {v && (
          <div className="confidence-card">
            <div className="confidence-num">
              {Math.round(v.confidence_score * 100)}
              <span>%</span>
            </div>
            <span className="confidence-label">confidence</span>
            <div className="verdict-chips">
              <span className={v.correctness_ok ? "chip ok" : "chip bad"}>
                correctness {v.correctness_ok ? "✓" : "✗"}
              </span>
              <span className={v.completeness_ok ? "chip ok" : "chip bad"}>
                completeness {v.completeness_ok ? "✓" : "✗"}
              </span>
            </div>
          </div>
        )}
      </div>

      {result.error && (
        <div className="alert" role="alert">
          {result.error}
        </div>
      )}

      {needsReview && (
        <div className="review-box" role="status">
          <strong>
            {result.status === "manual_review"
              ? "Routed to manual review"
              : "Processing didn’t complete"}
          </strong>
          <p>
            {result.status === "manual_review"
              ? "Automated checks couldn’t fully verify this return. Review the flagged checks below, correct the source documents, and resubmit."
              : "The pipeline stopped before finishing. Check the message above, then resubmit your documents."}
          </p>
          {failedChecks.length > 0 && (
            <ul>
              {failedChecks.map((c) => (
                <li key={c.name}>
                  {CHECK_LABELS[c.name] ?? c.name}
                  {c.message ? ` — ${c.message}` : ""}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {calc && (
        <div className="metric-grid">
          <article className="metric">
            <span>Taxpayer</span>
            <strong>{result.extracted_data?.employee_name || "Needs review"}</strong>
            <small>Tax year {result.extracted_data?.tax_year}</small>
          </article>
          <article className="metric">
            <span>Gross income</span>
            <strong>{money(calc.total_income ?? calc.gross_income)}</strong>
            <small>AGI {money(calc.adjusted_gross_income)}</small>
          </article>
          <article className="metric">
            <span>Taxable income</span>
            <strong>{money(calc.taxable_income)}</strong>
            <small>{calc.tax_table_used ? "IRS Tax Table" : "Tax Computation Worksheet"}</small>
          </article>
          <article className="metric">
            <span>Federal tax</span>
            <strong>{money(calc.federal_tax)}</strong>
            <small>
              {num(calc.child_tax_credit) > 0 ? `CTC ${money(calc.child_tax_credit)}` : "After credits"}
            </small>
          </article>
          <article className={`metric accent ${isRefund ? "" : "due"}`}>
            <span>{isRefund ? "Federal refund" : "Balance due"}</span>
            <strong>{money(isRefund ? calc.refund : calc.tax_due)}</strong>
            <small>
              {num(calc.state_refund) > 0
                ? `State refund ${money(calc.state_refund)}`
                : num(calc.state_balance_due) > 0
                  ? `State due ${money(calc.state_balance_due)}`
                  : result.receipt?.reference_number ?? "Pending verification"}
            </small>
          </article>
        </div>
      )}

      <div className="panel-row">
        {calc && (
          <div className="panel">
            <h3>Tax breakdown</h3>
            <dl className="breakdown">
              {breakdown.map(([label, value, total]) => (
                <div key={label} className={total ? "bd-row total" : "bd-row"}>
                  <dt>{label}</dt>
                  <dd>{money(value)}</dd>
                </div>
              ))}
              <div className="bd-row result">
                <dt>{isRefund ? "Refund" : "Balance due"}</dt>
                <dd>{money(isRefund ? calc.refund : calc.tax_due)}</dd>
              </div>
            </dl>
          </div>
        )}

        {v && (
          <div className="panel">
            <h3>Verification</h3>
            <ul className="checks">
              {checks.map((c) => (
                <li key={c.name} className={c.passed ? "ok" : "bad"}>
                  <span className="tick">{c.passed ? "✓" : "✗"}</span>
                  <div>
                    <strong>{CHECK_LABELS[c.name] ?? c.name}</strong>
                    {!c.passed && <small>{c.message}</small>}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

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
          Download professional report (PDF)
        </a>
      )}
    </section>
  );
}
