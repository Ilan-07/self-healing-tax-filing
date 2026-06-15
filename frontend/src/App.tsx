import { FormEvent, useEffect, useState } from "react";
import { getSubmission, submitDocument } from "./api/submissions";
import { AgentPipeline } from "./components/AgentPipeline";
import { ResultPanel } from "./components/ResultPanel";
import type { SubmissionResult } from "./types/tax";

export default function App() {
  const [file, setFile] = useState<File>();
  const [result, setResult] = useState<SubmissionResult>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const submissionId = new URLSearchParams(window.location.search).get(
      "submission",
    );
    if (!submissionId) return;
    setBusy(true);
    getSubmission(submissionId)
      .then(setResult)
      .catch((caught) =>
        setError(caught instanceof Error ? caught.message : "Load failed"),
      )
      .finally(() => setBusy(false));
  }, []);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setError("");
    setResult(undefined);
    try {
      const processed = await submitDocument(file);
      setResult(processed);
      window.history.replaceState(
        {},
        "",
        `?submission=${processed.submission_id}`,
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <nav>
        <div className="brand">
          <span>TF</span>
          <strong>TaxFlow Local</strong>
        </div>
        <div className="local-badge">Ollama only · private by design</div>
      </nav>

      <header className="hero">
        <div className="eyebrow">Self-healing filing intelligence</div>
        <h1>Tax documents in.<br />Verified answers out.</h1>
        <p>
          Five local agents extract, calculate, challenge, repair, and document
          every decision. Your taxpayer data never leaves your machine.
        </p>
      </header>

      <AgentPipeline active={busy ? "parsing" : result?.status} />

      <section className="workspace">
        <form className="upload-card" onSubmit={handleSubmit}>
          <div className="upload-icon">↑</div>
          <h2>Start a filing run</h2>
          <p>Upload a W-2 or supporting tax document.</p>
          <label className="file-field">
            <input
              type="file"
              accept=".pdf,.png,.jpg,.jpeg"
              onChange={(event) => setFile(event.target.files?.[0])}
            />
            <span>{file?.name ?? "Choose PDF or image"}</span>
          </label>
          <button disabled={!file || busy}>
            {busy ? "Agents are working…" : "Process securely"}
          </button>
          <small>PDF · PNG · JPG · OCR and vision enabled</small>
          {error && <div className="alert">{error}</div>}
        </form>

        <aside className="principles">
          <div>
            <span>01</span>
            <p><strong>Grounded extraction</strong>Every value carries source evidence.</p>
          </div>
          <div>
            <span>02</span>
            <p><strong>Rule-based math</strong>LLMs never author tax arithmetic.</p>
          </div>
          <div>
            <span>03</span>
            <p><strong>Bounded recovery</strong>Failed checks trigger an auditable loop.</p>
          </div>
        </aside>
      </section>

      {result && <ResultPanel result={result} />}

      <footer>
        <span>FastAPI · LangGraph · PostgreSQL · ChromaDB · React</span>
        <span>llama3.2-vision · qwen2.5-coder</span>
      </footer>
    </main>
  );
}
