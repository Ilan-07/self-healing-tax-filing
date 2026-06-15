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
    deductions: string;
    taxable_income: string;
    federal_tax: string;
    state_tax: string;
    refund: string;
    tax_due: string;
  };
  verification?: {
    valid: boolean;
    confidence_score: number;
    errors: string[];
    hallucination_flags: string[];
  };
  audit_trail: AuditEntry[];
  receipt?: {
    reference_number: string;
    filing_status: string;
  };
  report_url?: string;
  error?: string;
}
