export type RegressionTask = {
  task_id: string;
  is_critical: boolean;
  actual_tools: string[];
  expected_tools: string[];
};

export type Report = {
  dataset: string;
  baseline: {
    version: string;
    task_count: number;
    success_rate: number;
    tool_selection_accuracy: number;
    tool_argument_accuracy: number;
    answer_coverage: number;
    critical_task_success_rate: number;
  };
  candidate: {
    version: string;
    task_count: number;
    success_rate: number;
    tool_selection_accuracy: number;
    tool_argument_accuracy: number;
    answer_coverage: number;
    critical_task_success_rate: number;
  };
  regressions: RegressionTask[];
};

export type Diagnosis = {
  task_id: string;
  category: string;
  step: number;
  baseline_span: string | null;
  candidate_span: string | null;
  reason: string;
  confidence: number;
  is_critical: boolean;
};

export type Gate = {
  status: "PASS" | "WARNING" | "BLOCK";
  violations: {
    rule: string;
    severity: string;
    actual: number;
    threshold: number;
    message: string;
  }[];
};

export type DashboardPayload = {
  report: Report;
  diagnoses: Diagnosis[];
  gate: Gate;
};
