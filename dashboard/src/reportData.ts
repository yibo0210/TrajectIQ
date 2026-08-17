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
    success_rate: number;
    tool_selection_accuracy: number;
    tool_argument_accuracy: number;
    answer_coverage: number;
    critical_task_success_rate: number;
  };
  candidate: {
    version: string;
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

export const REGRESSION_REPORT: Report = {
  dataset: "customer_support_v1",
  baseline: {
    version: "baseline",
    success_rate: 1,
    tool_selection_accuracy: 1,
    tool_argument_accuracy: 1,
    answer_coverage: 1,
    critical_task_success_rate: 1,
  },
  candidate: {
    version: "regression",
    success_rate: 2 / 3,
    tool_selection_accuracy: 2 / 3,
    tool_argument_accuracy: 2 / 3,
    answer_coverage: 2 / 3,
    critical_task_success_rate: 1 / 2,
  },
  regressions: [
    {
      task_id: "refund_001",
      is_critical: true,
      expected_tools: ["query_order", "search_policy"],
      actual_tools: ["estimate_delivery"],
    },
    {
      task_id: "refund_002",
      is_critical: false,
      expected_tools: ["query_order"],
      actual_tools: ["estimate_delivery"],
    },
  ],
};

export const FIXED_REPORT: Report = {
  ...REGRESSION_REPORT,
  candidate: {
    version: "fixed",
    success_rate: 1,
    tool_selection_accuracy: 1,
    tool_argument_accuracy: 1,
    answer_coverage: 1,
    critical_task_success_rate: 1,
  },
  regressions: [],
};

export const REGRESSION_DIAGNOSES: Diagnosis[] = [
  {
    task_id: "refund_001",
    category: "tool_selection_error",
    step: 2,
    baseline_span: "query_order",
    candidate_span: "estimate_delivery",
    reason: "Candidate selected a different tool at the first divergent step.",
    confidence: 1,
    is_critical: true,
  },
  {
    task_id: "refund_002",
    category: "tool_selection_error",
    step: 2,
    baseline_span: "query_order",
    candidate_span: "estimate_delivery",
    reason: "Candidate selected a different tool at the first divergent step.",
    confidence: 1,
    is_critical: false,
  },
];
