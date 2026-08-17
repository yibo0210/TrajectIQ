# TrajectIQ Roadmap

TrajectIQ is a Phoenix extension for e-commerce support Agent regression diagnostics and release gates. Phoenix supplies OpenTelemetry trace storage, datasets, experiments, and evaluator infrastructure. TrajectIQ focuses on version comparison, first-error localization, failure clustering, and CI gates.

## Version plan

### v0.1: Reproducible Agent baseline

- Deliver a deterministic e-commerce support Agent with fixed order, policy, and delivery data.
- Support `baseline`, `regression`, and `fixed` configuration versions.
- Produce structured trajectories containing planner, tool, and final nodes.
- Include six representative tasks and isolated tests.

Acceptance: `agentguard --version baseline` runs repeatedly with identical results. Each run records its tools, arguments, results, and errors.

### v0.2: Phoenix trace integration

- Add OpenTelemetry spans for the Agent root, planner, tools, and final response.
- Export traces to a local Phoenix instance using `PHOENIX_COLLECTOR_ENDPOINT` or `--endpoint`.
- Document Phoenix integration.

Acceptance: the Phoenix Trace view reconstructs every e-commerce support task as an execution tree.

### v0.3: Version regression engine (complete)

- Run the same dataset against baseline and candidate versions.
- Calculate task success, tool selection accuracy, tool argument accuracy, latency, and cost deltas.
- Identify tasks that passed for baseline and fail for the candidate.
- Emit JSON and Markdown reports.

Acceptance: the `regression` version consistently produces diagnosed task regressions.

### v0.4: First-error localization and attribution (complete)

- Align baseline and candidate trajectories to identify the first divergent tool selection, argument, or result.
- Classify planning, tool selection, argument, retrieval, execution, generation, and timeout failures.
- Aggregate failures into a diagnosis report.

Acceptance: every regression points to a concrete step and failure category.

### v0.5: Release gates and CI (complete)

- Support YAML thresholds for success rate, tool accuracy, critical-task regressions, P95 latency, and cost.
- Emit `PASS`, `WARNING`, or `BLOCK`; return a non-zero exit code for `BLOCK`.
- Include a GitHub Actions workflow example.

Acceptance: a degraded candidate blocks the pipeline and identifies remediation priority.

### v0.6: TrajectIQ dashboard (complete)

- Add a standalone version overview, regression task list, first-error diagnostics, and gate decision interface.
- Keep the dashboard in this repository rather than coupling it to Phoenix's React application.
- Use report-shaped deterministic demo data now; add report artifact import as the next increment.
