# 外部轨迹接入

`trajectiq-trace-regression` 用于评测任意 Agent 运行时导出的执行轨迹。它不依赖某个框架；只需要将 Trace 转换为 TrajectIQ 的最小 JSON 结构。

```json
{
  "version": "candidate-2026-08-17",
  "runs": [
    {
      "task_id": "refund_001",
      "answer": "...",
      "spans": [
        {"step": 1, "kind": "planner", "name": "planner"},
        {"step": 2, "kind": "tool", "name": "query_order", "input": {"order_id": "A1001"}},
        {"step": 3, "kind": "final", "name": "final_answer"}
      ]
    }
  ]
}
```

`task_id`、`answer` 与 `spans` 是必填字段。工具 Span 的 `kind` 必须为 `tool`，`name` 为工具名；`input`、`output`、`error` 用于工具参数、执行结果与首错定位。

```bash
trajectiq-trace-regression \
  --baseline-traces exports/baseline.json \
  --candidate-traces exports/candidate.json \
  --format markdown
```

传入自己的 JSONL 评测集时，使用 `--dataset`。每行是一条任务，字段包括 `task_id`、`category`、`tags`、`input`、`expected_tools`、`expected_arguments`、`expected_answer_contains` 和可选的 `critical`。

## Phoenix/OpenInference 导出

原始 OpenTelemetry/Phoenix JSON 使用 `--input-format openinference`。适配器按照 OpenInference 语义约定读取：

- `trajectiq.task_id`：关联版本化评测任务。
- `openinference.span.kind=TOOL`：识别工具调用步骤。
- `tool.name`、`input.value`、`output.value`：恢复工具名、参数与结果。
- `error.type` 或 OTel `status_code=ERROR`：保留工具错误。

导出可以是顶层 `spans` 数组，也可以是包含 `spans` 的 `traces` 数组；attributes 同时支持 Phoenix 的 JSON 对象和 OTLP JSON 属性数组。

## 真实 Agent 示例

仓库内的 `trajectiq-openai-demo` 使用 OpenAI 兼容的 Chat Completions 工具调用协议，并将模型选择的工具写成 `TOOL` Span。它默认只运行一条任务：

```bash
trajectiq-openai-demo --task-id refund_001 --output exports/live.json
trajectiq-trace-regression --baseline-traces exports/baseline.json --candidate-traces exports/live.json
```

这是一个可选示例，不会在测试或 CI 中调用外部模型。
