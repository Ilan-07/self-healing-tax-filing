import type { SubmissionResult } from "../types/tax";

export async function submitDocument(file: File): Promise<SubmissionResult> {
  const body = new FormData();
  body.append("document", file);
  const response = await fetch("/api/v1/submissions", {
    method: "POST",
    body,
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "The submission could not be processed.");
  }
  return response.json();
}

export async function getSubmission(
  submissionId: string,
): Promise<SubmissionResult> {
  const response = await fetch(`/api/v1/submissions/${submissionId}`);
  if (!response.ok) {
    throw new Error("The saved submission could not be loaded.");
  }
  return response.json();
}
