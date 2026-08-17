import { useEffect, useState, type ChangeEvent } from "react";
import { type DashboardPayload, type Diagnosis, type Report } from "./reportData";
import "./styles.css";

type Scenario = "regression" | "fixed";
type View = "overview" | "tasks" | "diagnosis";

const metrics = [
  ["Task success", "success_rate"],
  ["Tool selection", "tool_selection_accuracy"],
  ["Tool arguments", "tool_argument_accuracy"],
  ["Answer coverage", "answer_coverage"],
  ["Critical tasks", "critical_task_success_rate"],
] as const;

function formatPercent(value: number): string {
  return new Intl.NumberFormat("en-US", { style: "percent", maximumFractionDigits: 1 }).format(value);
}

function getDiagnosis(taskId: string, diagnoses: Diagnosis[]): Diagnosis | undefined {
  return diagnoses.find((diagnosis) => diagnosis.task_id === taskId);
}

export function App() {
  const [scenario, setScenario] = useState<Scenario>("regression");
  const [demoPayloads, setDemoPayloads] = useState<Partial<Record<Scenario, DashboardPayload>>>({});
  const [demoError, setDemoError] = useState<string | null>(null);
  const [importedPayload, setImportedPayload] = useState<DashboardPayload | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState("refund_001");
  const [activeView, setActiveView] = useState<View>("overview");
  useEffect(() => {
    Promise.all([
      fetch("/demo/baseline-to-regression.json").then((response) => response.json() as Promise<DashboardPayload>),
      fetch("/demo/baseline-to-fixed.json").then((response) => response.json() as Promise<DashboardPayload>),
    ]).then(([regression, fixed]) => setDemoPayloads({ regression, fixed }))
      .catch(() => setDemoError("Unable to load the bundled Dashboard artifacts."));
  }, []);

  const payload = importedPayload ?? demoPayloads[scenario];
  const report = payload?.report;
  const diagnoses = payload?.diagnoses ?? [];
  const status = payload?.gate.status;
  if (!report || !status) {
    return <main className="app-shell"><p className="empty-state">{demoError ?? "Loading release diagnostics..."}</p></main>;
  }
  const selectedTask = report.regressions.find((task) => task.task_id === selectedTaskId);
  const selectedDiagnosis = selectedTask ? getDiagnosis(selectedTask.task_id, diagnoses) : undefined;
  const summary = status === "PASS" ? "All release thresholds passed. The candidate is ready for promotion." : report.regressions.length + " task regressions detected, including " + report.regressions.filter((task) => task.is_critical).length + " critical task.";

  function selectScenario(nextScenario: Scenario) {
    setScenario(nextScenario);
    setImportedPayload(null);
    setImportError(null);
    setSelectedTaskId(nextScenario === "regression" ? "refund_001" : "");
    setActiveView("overview");
  }

  function importReport(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    file.text().then((text) => {
      const payload = JSON.parse(text) as DashboardPayload;
      if (!payload.report || !payload.diagnoses || !payload.gate) {
        throw new Error("Missing report, diagnoses, or gate.");
      }
      setImportedPayload(payload);
      setImportError(null);
      setSelectedTaskId(payload.report.regressions[0]?.task_id ?? "");
      setActiveView("overview");
    }).catch(() => setImportError("This file is not a valid TrajectIQ Dashboard artifact."));
  }

  return <main className="app-shell">
    <header className="topbar">
      <div className="brand"><div className="brand-mark">TQ</div><div><h1>TrajectIQ</h1><p>Release diagnostics for multi-tool Agents</p></div></div>
      <div className="scenario-toggle">
        <button className={scenario === "regression" ? "selected" : ""} onClick={() => selectScenario("regression")}>Regression run</button>
        <button className={scenario === "fixed" ? "selected" : ""} onClick={() => selectScenario("fixed")}>Fixed run</button>
      </div>
      <label className="import-control">Import JSON<input type="file" accept="application/json" onChange={importReport} /></label>
    </header>
    {importError && <p className="import-error">{importError}</p>}
    <section className="release-banner">
      <div><p className="eyebrow">Release decision</p><h2>{status === "PASS" ? "Candidate cleared for release" : status === "WARNING" ? "Candidate needs release review" : "Candidate blocked before release"}</h2><p>{summary}</p></div>
      <div className={status === "PASS" ? "status status-pass" : status === "WARNING" ? "status status-warning" : "status status-block"}>{status}</div>
    </section>
    <nav className="tabs">
      <button className={activeView === "overview" ? "active" : ""} onClick={() => setActiveView("overview")}>Overview</button>
      <button className={activeView === "tasks" ? "active" : ""} onClick={() => setActiveView("tasks")}>Regression tasks</button>
      <button className={activeView === "diagnosis" ? "active" : ""} onClick={() => setActiveView("diagnosis")}>First-error diagnosis</button>
    </nav>
    {activeView === "overview" && <section className="content-grid">
      <div className="section-heading"><div><p className="eyebrow">Version comparison</p><h2>{report.baseline.version} to {report.candidate.version}</h2></div><span className="dataset">Dataset: {report.dataset}</span></div>
      <div className="metrics-grid">{metrics.map(([label, key]) => { const baseline = report.baseline[key]; const candidate = report.candidate[key]; const delta = candidate - baseline; return <article className="metric" key={key}><p>{label}</p><strong>{formatPercent(candidate)}</strong><span className={delta < 0 ? "delta negative" : "delta positive"}>{(delta >= 0 ? "+" : "") + formatPercent(delta)} vs baseline</span></article>; })}</div>
      <article className="finding-panel"><div><p className="eyebrow">Gate findings</p><h3>{status === "PASS" ? "No release blockers" : "Why this run is blocked"}</h3></div>{status === "PASS" ? <p>All task and critical-task checks match the baseline.</p> : <ul><li>Task success fell from 100.0% to 66.7%</li><li>Tool selection accuracy fell below the 95.0% threshold</li><li>One critical refund task regressed</li></ul>}</article>
    </section>}
    {activeView === "tasks" && <section className="content-grid"><div className="section-heading"><div><p className="eyebrow">Task-level regressions</p><h2>{report.regressions.length} affected tasks</h2></div></div>{report.regressions.length === 0 ? <div className="empty-state">No task regressions detected for this candidate.</div> : <div className="task-list">{report.regressions.map((task) => <button className={selectedTaskId === task.task_id ? "task-row selected" : "task-row"} key={task.task_id} onClick={() => { setSelectedTaskId(task.task_id); setActiveView("diagnosis"); }}><span className={task.is_critical ? "priority critical" : "priority"}>{task.is_critical ? "Critical" : "Standard"}</span><strong>{task.task_id}</strong><span>Expected: {task.expected_tools.join(" -> ")}</span><span>Actual: {task.actual_tools.join(" -> ")}</span></button>)}</div>}</section>}
    {activeView === "diagnosis" && <section className="content-grid"><div className="section-heading"><div><p className="eyebrow">First divergent span</p><h2>{selectedDiagnosis ? selectedDiagnosis.task_id : "No diagnosis required"}</h2></div></div>{selectedDiagnosis ? <div className="diagnosis-layout"><article className="trajectory baseline-trajectory"><p className="eyebrow">Baseline trajectory</p><div className="trace-step">1 <span>planner</span></div><div className="trace-step correct">2 <span>{selectedDiagnosis.baseline_span}</span></div><div className="trace-step">3 <span>final_answer</span></div></article><article className="diagnosis-card"><p className="eyebrow">Detected cause</p><h3>{selectedDiagnosis.category.replaceAll("_", " ")}</h3><p>{selectedDiagnosis.reason}</p><dl><div><dt>First error step</dt><dd>{selectedDiagnosis.step}</dd></div><div><dt>Confidence</dt><dd>{formatPercent(selectedDiagnosis.confidence)}</dd></div><div><dt>Release impact</dt><dd>{selectedDiagnosis.is_critical ? "Blocks release" : "Needs review"}</dd></div></dl></article><article className="trajectory candidate-trajectory"><p className="eyebrow">Candidate trajectory</p><div className="trace-step">1 <span>planner</span></div><div className="trace-step error">2 <span>{selectedDiagnosis.candidate_span}</span></div><div className="trace-step">3 <span>final_answer</span></div></article></div> : <div className="empty-state">The selected candidate has no task regression to diagnose.</div>}</section>}
  </main>;
}
