# TrajectIQ
TrajectIQ is a Phoenix extension project for diagnosing e-commerce support Agent regressions and enforcing release-quality gates. Phoenix remains the observability foundation; TrajectIQ adds version comparison, first-error localization, failure clustering, and CI release gates.

## Current status

`v0.6` is complete. It includes Agent execution, Phoenix trace export, regression diagnostics, YAML release gates, CI, and a standalone Dashboard.

## Project layout

```text
agentguard/
├── src/agentguard/       # Agent runtime and OTLP instrumentation
├── tests/                # Isolated project tests
├── dashboard/            # Standalone React release-diagnostics interface
├── ARCHITECTURE.md        # Component ownership and data flow
├── README.md             # Setup and scope
├── ROADMAP.md            # Version plan and acceptance criteria
└── pyproject.toml        # Standalone package metadata
```

## Run locally

From this directory, install the isolated project dependencies and run a version:

```bash
python -m pip install -e .[dev]
trajectiq --version baseline
trajectiq --version regression
```

`baseline` and `fixed` use the intended refund flow: `query_order` then `search_policy`. `regression` deliberately calls `estimate_delivery` for refund tasks, creating a stable regression fixture for later versions.

Compare two versions and list task-level regressions:

```bash
trajectiq-regression --baseline baseline --candidate regression
trajectiq-regression --format json --output reports/regression.json
```

The report compares task success, tool selection, tool arguments, answer coverage, and critical-task success. A regression is a task that passes in the baseline and fails in the candidate.

Diagnose the first divergent step for every task-level regression:

```bash
trajectiq-diagnose --baseline baseline --candidate regression
trajectiq-diagnose --format json --output reports/diagnosis.json
```

The deterministic diagnosis distinguishes tool selection, tool argument, tool execution, and generation errors. Each result includes the first divergent step, baseline and candidate span names, a reason, and confidence.

## Enforce a release gate

The checked-in [release-gate.yaml](release-gate.yaml) controls the minimum quality level and regression budget:

```bash
trajectiq-gate --baseline baseline --candidate fixed
trajectiq-gate --baseline baseline --candidate regression
```

The first command reports PASS. The second reports BLOCK and exits with code 1, which makes it suitable for CI. A GitHub Actions example is included in [.github/workflows/release-gate.yml](.github/workflows/release-gate.yml).

## Dashboard

The standalone Dashboard visualizes the release decision, quality deltas, affected tasks, and the first divergent tool step. It is intentionally kept separate from Phoenix's frontend so this repository remains independently runnable.

```bash
cd dashboard
pnpm install
pnpm dev
```

Open the local URL shown by Vite. The scenario selector switches between the blocked regression run and the passing fixed run.

To create an artifact from the CLI and import it into the Dashboard:

    trajectiq-dashboard-data --baseline baseline --candidate regression --output dashboard-report.json

Choose Import JSON in the Dashboard and select dashboard-report.json. Two reproducible example artifacts are checked into dashboard/public/demo.

## Demo flow

1. Run the release gate against regression and show that it blocks the candidate.
2. Generate dashboard-report.json and import it into the Dashboard.
3. Open the regression task list and select refund_001.
4. Show that the first divergent span selected estimate_delivery instead of query_order.
5. Switch to fixed and show the passing release decision.

## Export traces to Phoenix

Start Phoenix separately, then run:

```bash
trajectiq --version baseline --trace --endpoint http://localhost:6006
```

The default export target is `http://localhost:6006/v1/traces`. Every task produces an `agent_run` root span with `planner`, tool, and `final_answer` child spans.

## Contribution boundary

TrajectIQ is based on Phoenix integration concepts and OpenTelemetry. Phoenix provides the trace storage, UI, datasets, experiments, and evaluator infrastructure. TrajectIQ's version snapshots, regression comparison, first-error localization, failure attribution, and release gates are independent extension work.
