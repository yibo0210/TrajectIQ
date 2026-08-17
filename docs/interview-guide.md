# TrajectIQ 项目讲解

## 30 秒版本

TrajectIQ 是一个多工具 Agent 的发布质量平台。它把真实 Agent 的 OpenInference Trace 与版本化评测集关联，对比基线和候选版本的工具选择、参数和回答质量，定位第一处错误步骤，并在 CI 中阻断不满足质量阈值的版本。

## 两分钟演示顺序

1. 打开 Dashboard，展示 `baseline -> regression` 的 `BLOCK` 决策和十条退款退化。
2. 选择 `refund_001`，说明基线调用 `query_order`，候选版本却错误调用 `estimate_delivery`。
3. 展示 `release-gate.yaml`，说明关键任务退化会阻断发布。
4. 展示 GitHub Actions 的报告 Artifact 与 Pull Request 质量摘要。
5. 展示 `trajectiq-trace-regression --input-format openinference`，说明平台可以接入 Phoenix/OpenTelemetry 导出。
6. 最后展示 `trajectiq-openai-demo`：真实 OpenAI 兼容 Agent 的工具调用会被写为 AGENT、LLM、TOOL Span。

## 关键设计决策

- **基线通过、候选失败才算回归**：避免把历史已知失败误判成新版本问题。
- **确定性评测优先**：工具选择和参数错误适合精确断言，能保证 CI 可重复；开放式回答可在后续接入 LLM-as-a-Judge。
- **OpenInference 作为适配边界**：内部运行时、Phoenix 导出和外部 Agent 都统一为标准轨迹，评测逻辑无需绑定某个框架。
- **真实模型不进入 CI**：CI 使用确定性 Fixture，避免 API 成本、密钥泄露和外部服务波动；真实 Agent 示例用于人工演示和集成验证。

## 已知边界

- 当前发布门禁聚焦任务成功率、工具选择、关键任务与回归数量；延迟、Token 和成本门禁可作为后续生产化指标。
- OpenAI 示例实现 Chat Completions 工具调用协议；其他框架通过 OpenInference JSON 适配进入平台。
