import { useEffect, useState, type ChangeEvent } from "react";
import { type DashboardPayload, type Diagnosis } from "./reportData";
import "./styles.css";

type Scenario = "regression" | "fixed";
type View = "overview" | "tasks" | "diagnosis";

const metrics = [
  ["任务成功率", "success_rate", "percent"],
  ["工具选择准确率", "tool_selection_accuracy", "percent"],
  ["工具参数准确率", "tool_argument_accuracy", "percent"],
  ["回答覆盖率", "answer_coverage", "percent"],
  ["关键任务成功率", "critical_task_success_rate", "percent"],
  ["平均延迟", "average_latency_ms", "ms"],
  ["平均 Token", "average_total_tokens", "tokens"],
  ["平均成本", "average_cost_usd", "usd"],
] as const;

const categoryLabels: Record<string, string> = {
  tool_selection_error: "工具选择错误",
  tool_argument_error: "工具参数错误",
  tool_execution_error: "工具执行错误",
  generation_error: "回答生成错误",
};

function formatPercent(value: number): string {
  return new Intl.NumberFormat("zh-CN", { style: "percent", maximumFractionDigits: 1 }).format(value);
}

function formatMetric(value: number, kind: "percent" | "ms" | "tokens" | "usd"): string {
  if (kind === "percent") return formatPercent(value);
  if (kind === "usd") return `$${value.toFixed(5)}`;
  if (kind === "ms") return `${value.toFixed(1)} ms`;
  return `${value.toFixed(1)}`;
}

function getDiagnosis(taskId: string, diagnoses: Diagnosis[]): Diagnosis | undefined {
  return diagnoses.find((diagnosis) => diagnosis.task_id === taskId);
}

function formatViolation(rule: string): string {
  const messages: Record<string, string> = {
    minimum_success_rate: "候选版本的任务成功率低于最低阈值。",
    maximum_success_rate_drop: "候选版本的任务成功率下降超过允许范围。",
    minimum_tool_selection_accuracy: "候选版本的工具选择准确率低于最低阈值。",
    maximum_critical_task_regressions: "候选版本的关键任务退化数量超过允许范围。",
    maximum_task_regressions: "候选版本的任务退化数量超过预警阈值。",
    maximum_average_latency_ms: "候选版本的平均延迟超过阈值。",
    maximum_average_total_tokens: "候选版本的平均 Token 用量超过阈值。",
    maximum_average_cost_usd: "候选版本的平均估算成本超过阈值。",
  };
  return messages[rule] ?? "候选版本未满足发布质量规则。";
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
      .catch(() => setDemoError("无法加载内置的评测报告。"));
  }, []);

  const payload = importedPayload ?? demoPayloads[scenario];
  const report = payload?.report;
  const diagnoses = payload?.diagnoses ?? [];
  const status = payload?.gate.status;
  if (!report || !status) {
    return <main className="app-shell"><p className="empty-state">{demoError ?? "正在加载发布诊断结果..."}</p></main>;
  }
  const selectedTask = report.regressions.find((task) => task.task_id === selectedTaskId);
  const selectedDiagnosis = selectedTask ? getDiagnosis(selectedTask.task_id, diagnoses) : undefined;
  const candidateVersion = report.candidate.version;
  const summary = status === "PASS" ? "所有发布阈值均已满足，当前版本可以进入发布流程。" : `发现 ${report.regressions.length} 条任务退化，其中 ${report.regressions.filter((task) => task.is_critical).length} 条为关键任务。`;

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
        throw new Error("缺少报告、诊断或门禁数据。");
      }
      setImportedPayload(payload);
      setImportError(null);
      setSelectedTaskId(payload.report.regressions[0]?.task_id ?? "");
      setActiveView("overview");
    }).catch(() => setImportError("该文件不是有效的 TrajectIQ Dashboard 报告。"));
  }

  function exportReport() {
    const content = JSON.stringify(payload, null, 2);
    const url = URL.createObjectURL(new Blob([content], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `trajectiq-${candidateVersion}-report.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return <main className="app-shell">
    <header className="topbar">
      <div className="brand"><div className="brand-mark"><span>T</span><span>Q</span></div><div><h1>TrajectIQ</h1><p>多工具 Agent 发布诊断平台</p></div></div>
      <span className="environment">EVALUATION / CUSTOMER SUPPORT</span>
      <div className="scenario-toggle">
        <button className={scenario === "regression" ? "selected" : ""} onClick={() => selectScenario("regression")}>回归版本</button>
        <button className={scenario === "fixed" ? "selected" : ""} onClick={() => selectScenario("fixed")}>修复版本</button>
      </div>
      <label className="import-control">导入 JSON<input type="file" accept="application/json" onChange={importReport} /></label>
      <button className="export-control" onClick={exportReport}>导出报告</button>
    </header>
    {importError && <p className="import-error">{importError}</p>}
    <section className="release-banner">
      <div className="release-copy"><p className="eyebrow">发布决策 / Release decision</p><h2>{status === "PASS" ? "候选版本可发布" : status === "WARNING" ? "候选版本需要人工复核" : "候选版本已被发布门禁拦截"}</h2><p>{summary}</p></div>
      <div className="release-meta"><span>质量门禁</span><div className={status === "PASS" ? "status status-pass" : status === "WARNING" ? "status status-warning" : "status status-block"}>{status}</div><small>{payload.gate.violations.length} 条规则命中</small></div>
    </section>
    <section className="run-context" aria-label="本次评测上下文">
      <span><b>评测来源</b>{importedPayload ? "导入报告" : "内置可复现样例"}</span>
      <span><b>门禁配置</b>release-gate.yaml</span>
      <span><b>任务规模</b>{report.baseline.task_count} cases</span>
      <span><b>诊断覆盖</b>{diagnoses.length} first-error findings</span>
    </section>
    <nav className="tabs">
      <button className={activeView === "overview" ? "active" : ""} onClick={() => setActiveView("overview")}>质量概览</button>
      <button className={activeView === "tasks" ? "active" : ""} onClick={() => setActiveView("tasks")}>退化任务</button>
      <button className={activeView === "diagnosis" ? "active" : ""} onClick={() => setActiveView("diagnosis")}>首错诊断</button>
    </nav>
    {activeView === "overview" && <section className="content-grid">
      <div className="section-heading"><div><p className="eyebrow">版本对比 / Version diff</p><h2>{report.baseline.version} <span>→</span> {report.candidate.version}</h2></div><span className="dataset">数据集：{report.dataset} · {report.baseline.task_count} 条任务</span></div>
      <div className="metrics-grid">{metrics.map(([label, key, kind]) => { const baseline = report.baseline[key]; const candidate = report.candidate[key]; const delta = candidate - baseline; const meterWidth = kind === "percent" ? candidate * 100 : Math.min(100, candidate > 0 ? 70 : 0); const deltaIsBad = kind === "percent" ? delta < 0 : delta > 0; return <article className="metric" key={key}><div className="metric-top"><p>{label}</p><span className={deltaIsBad ? "delta negative" : "delta positive"}>{(delta >= 0 ? "+" : "") + formatMetric(delta, kind)}</span></div><strong>{formatMetric(candidate, kind)}</strong><div className="metric-meter" aria-label={`${label} ${formatMetric(candidate, kind)}`}><span style={{ width: `${meterWidth}%` }} /></div><small>基线 {formatMetric(baseline, kind)}</small></article>; })}</div>
      <article className="finding-panel"><div><p className="eyebrow">门禁结论</p><h3>{status === "PASS" ? "未发现发布阻塞项" : "当前版本的阻塞原因"}</h3></div>{status === "PASS" ? <p>任务质量与关键任务检查均达到发布要求。</p> : <ul>{payload.gate.violations.map((violation) => <li key={violation.rule}>{formatViolation(violation.rule)}</li>)}</ul>}</article>
    </section>}
    {activeView === "tasks" && <section className="content-grid"><div className="section-heading"><div><p className="eyebrow">任务级退化</p><h2>{report.regressions.length} 条受影响任务</h2></div></div>{report.regressions.length === 0 ? <div className="empty-state">当前候选版本未发现任务退化。</div> : <div className="task-list">{report.regressions.map((task) => <button className={selectedTaskId === task.task_id ? "task-row selected" : "task-row"} key={task.task_id} onClick={() => { setSelectedTaskId(task.task_id); setActiveView("diagnosis"); }}><span className={task.is_critical ? "priority critical" : "priority"}>{task.is_critical ? "关键任务" : "常规任务"}</span><strong>{task.task_id}</strong><span>预期：{task.expected_tools.join(" -> ")}</span><span>实际：{task.actual_tools.join(" -> ")}</span></button>)}</div>}</section>}
    {activeView === "diagnosis" && <section className="content-grid"><div className="section-heading"><div><p className="eyebrow">首个分歧步骤</p><h2>{selectedDiagnosis ? selectedDiagnosis.task_id : "无需诊断"}</h2></div></div>{selectedDiagnosis ? <div className="diagnosis-layout"><article className="trajectory baseline-trajectory"><p className="eyebrow">基线执行轨迹</p><div className="trace-step">1 <span>planner</span></div><div className="trace-step correct">2 <span>{selectedDiagnosis.baseline_span}</span></div><div className="trace-step">3 <span>final_answer</span></div></article><article className="diagnosis-card"><p className="eyebrow">识别原因</p><h3>{categoryLabels[selectedDiagnosis.category] ?? selectedDiagnosis.category}</h3><p>候选版本在第一个分歧步骤选择了与基线不同的工具。</p><dl><div><dt>首错步骤</dt><dd>{selectedDiagnosis.step}</dd></div><div><dt>置信度</dt><dd>{formatPercent(selectedDiagnosis.confidence)}</dd></div><div><dt>发布影响</dt><dd>{selectedDiagnosis.is_critical ? "阻断发布" : "需要复核"}</dd></div></dl></article><article className="trajectory candidate-trajectory"><p className="eyebrow">候选版本执行轨迹</p><div className="trace-step">1 <span>planner</span></div><div className="trace-step error">2 <span>{selectedDiagnosis.candidate_span}</span></div><div className="trace-step">3 <span>final_answer</span></div></article></div> : <div className="empty-state">当前候选版本没有需要诊断的任务退化。</div>}</section>}
  </main>;
}
