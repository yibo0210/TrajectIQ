# TrajectIQ Architecture

~~~mermaid
flowchart LR
  A[Customer-support tasks] --> B[Deterministic multi-tool Agent]
  B --> C[OpenTelemetry traces]
  C --> D[Phoenix]
  B --> E[Regression evaluator]
  E --> F[First-error attribution]
  E --> G[YAML release gate]
  F --> H[Dashboard data artifact]
  G --> H
  H --> I[TrajectIQ Dashboard]
  G --> J[GitHub Actions]
~~~

## Ownership

Phoenix owns trace ingestion, storage, exploration, datasets, experiments, and general evaluators. TrajectIQ owns the customer-support Agent fixture, version comparison, task-level regression detection, first-error attribution, release-gate policy, CI artifact generation, and the standalone dashboard.

## Data flow

1. The Agent executes the same task set under a baseline and a candidate configuration.
2. The evaluator compares task success, tool choice, tool parameters, and final-answer expectations.
3. The attribution module aligns both trajectories and finds the first divergent step.
4. The release gate evaluates quality thresholds from release-gate.yaml.
5. The TrajectIQ dashboard-data command writes one JSON artifact consumed by the Dashboard.
