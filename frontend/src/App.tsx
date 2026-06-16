import { FormEvent, useEffect, useState } from "react";
import { getSubmission, submitDocument } from "./api/submissions";
import { AgentPipeline } from "./components/AgentPipeline";
import { ResultPanel } from "./components/ResultPanel";
import type { SubmissionResult } from "./types/tax";

const TERMINAL = new Set(["completed", "manual_review", "failed"]);

async function pollUntilDone(
  submissionId: string,
  onUpdate: (r: SubmissionResult) => void,
  attempts = 60,
): Promise<SubmissionResult> {
  let latest: SubmissionResult | undefined;
  for (let i = 0; i < attempts; i += 1) {
    latest = await getSubmission(submissionId);
    onUpdate(latest);
    if (TERMINAL.has(latest.status)) return latest;
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
  return latest as SubmissionResult;
}

export default function App() {
  const [files, setFiles] = useState<File[]>([]);
  const [result, setResult] = useState<SubmissionResult>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    const submissionId = new URLSearchParams(window.location.search).get(
      "submission",
    );
    if (!submissionId) return;
    setBusy(true);
    pollUntilDone(submissionId, setResult)
      .then(setResult)
      .catch((caught) =>
        setError(caught instanceof Error ? caught.message : "Load failed"),
      )
      .finally(() => setBusy(false));
  }, []);

  function resetRun() {
    setFiles([]);
    setResult(undefined);
    setError("");
    setDragging(false);
    window.history.replaceState({}, "", window.location.pathname);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!files.length) return;
    setBusy(true);
    setError("");
    setResult(undefined);
    try {
      const queued = await submitDocument(files);
      setResult(queued);
      window.history.replaceState({}, "", `?submission=${queued.submission_id}`);
      setResult(await pollUntilDone(queued.submission_id, setResult));
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
        <div className="nav-right">
          {(result || busy) && (
            <button
              type="button"
              className="start-over"
              onClick={resetRun}
              disabled={busy}
            >
              {busy ? "Running…" : "Start over"}
            </button>
          )}
          <div className="local-badge">Local-first · auditable by design</div>
        </div>
      </nav>

      <header className="hero">
        <div className="eyebrow">Self-healing filing intelligence</div>
        <h1>Tax documents in.<br />Verified answers out.</h1>
        <p>
          Five agents extract, calculate, challenge, repair, and document every
          decision — on a deterministic 2025 tax engine with a grounded,
          verifiable audit trail.
        </p>
      </header>

      <AgentPipeline status={busy ? "processing" : result?.status} />

      <section className="workspace">
        <form className="upload-card" onSubmit={handleSubmit}>
          <div className="upload-icon">↑</div>
          <h2>Start a filing run</h2>
          <p>Upload your W-2 plus any 1099s, SSA-1099, K-1, or 1098 — together.</p>
          <label
            className={`file-field${dragging ? " dragging" : ""}`}
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              const dropped = Array.from(event.dataTransfer.files ?? []);
              if (dropped.length) setFiles(dropped);
            }}
          >
            <input
              type="file"
              multiple
              accept=".pdf,.png,.jpg,.jpeg"
              onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
            />
            <span>
              {dragging
                ? "Drop to upload"
                : files.length === 0
                  ? "Drop files here, or choose PDF / images"
                  : files.length === 1
                    ? files[0].name
                    : `${files.length} files selected`}
            </span>
          </label>
          {files.length > 1 && (
            <ul className="file-list">
              {files.map((f) => (
                <li key={f.name}>{f.name}</li>
              ))}
            </ul>
          )}
          <button
            className={busy ? "working" : ""}
            disabled={!files.length || busy}
            aria-busy={busy}
          >
            {busy ? "Agents are working…" : "Process securely"}
          </button>
          <small>PDF · PNG · JPG · multiple documents merged into one return</small>
          {error && (
            <div className="alert" role="alert">
              {error}
            </div>
          )}
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
        <span>Deterministic 1040 engine · grounded extraction</span>
      </footer>
    </main>
  );
}
