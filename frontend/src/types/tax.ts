export type WorkflowStatus =
  | "uploaded"
  | "parsing"
  | "calculating"
  | "verifying"
  | "remediating"
  | "completed"
  | "manual_review"
  | "failed";

export interface AuditEntry {
  agent: string;
  action: string;
  reason: string;
  timestamp: string;
  details: Record<string, unknown>;
}

export interface SubmissionResult {
  submission_id: string;
  status: WorkflowStatus;
  original_filename: string;
  extracted_data?: {
    employee_name: string;
    employer_name: string;
    filing_status: string;
    tax_year: number;
    wages: string;
    federal_tax_withheld: string;
    state_tax_withheld: string;
  };
  calculation?: {
    gross_income: string;
    total_income?: string;
    adjustments?: string;
    adjusted_gross_income?: string;
    deductions: string;
    qbi_deduction?: string;
    taxable_income: string;
    income_tax_before_credits?: string;
    nonrefundable_credits?: string;
    other_taxes?: string;
    federal_tax: string;
    state_tax: string;
    child_tax_credit?: string;
    earned_income_credit?: string;
    self_employment_tax?: string;
    total_payments?: string;
    tax_table_used?: boolean;
    params_verified?: boolean;
    refund: string;
    tax_due: string;
    state_refund?: string;
    state_balance_due?: string;
  };
  verification?: {
    valid: boolean;
    confidence_score: number;
    correctness_ok?: boolean;
    completeness_ok?: boolean;
    errors: string[];
    hallucination_flags: string[];
    checks?: { name: string; passed: boolean; message: string }[];
  };
  audit_trail: AuditEntry[];
  receipt?: {
    reference_number: string;
    filing_status: string;
  };
  report_url?: string;
  error?: string;
}
