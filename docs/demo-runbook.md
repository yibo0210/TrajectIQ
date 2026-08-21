# TrajectIQ 演示 Runbook

这份 Runbook 用于面试、项目答辩或录屏演示。完整流程约 2 到 3 分钟，不需要 API Key，也不会产生外部费用。

## 1. 展示正常版本

```bash
trajectiq-regression --baseline baseline --candidate fixed
trajectiq-gate --baseline baseline --candidate fixed
```

`fixed` 与 `baseline` 的任务行为一致，门禁最终状态为 `PASS`。

## 2. 制造并拦截回归

```bash
trajectiq-regression --baseline baseline --candidate regression
trajectiq-gate --baseline baseline --candidate regression
```

`regression` 版本会把退款请求错误路由到 `estimate_delivery`。系统识别出 10 条回归，其中 3 条为关键任务，门禁输出 `BLOCK` 并返回非零状态码。

## 3. 展示首错定位

```bash
trajectiq-diagnose --baseline baseline --candidate regression
```

重点说明：系统不仅报告成功率下降，还会对比两条轨迹，定位第一个工具选择分歧。

## 4. 打开 Dashboard

```bash
trajectiq-dashboard-data --baseline baseline --candidate regression --output dashboard/public/demo/baseline-to-regression.json
cd dashboard
pnpm install
pnpm dev
```

页面按“发布结论 → 质量指标 → 退化任务 → 首错诊断 → 修复版本 PASS”的顺序展示。质量概览中包含成功率、工具选择、平均延迟、Token 和成本。

## 5. 面试中的一句话总结

> TrajectIQ 把 Agent 的一次运行从黑盒回答变成可比较的执行轨迹，并在版本发布前自动检查任务质量、工具选择、延迟、Token 和成本；一旦发现回归，还能定位到第一个错误工具步骤。

## 演示边界

默认演示使用确定性 Fixture，保证每次结果一致。真实 OpenAI 兼容 Agent 需要配置 `OPENAI_API_KEY`，适合单独展示 Trace 接入，不建议在面试现场运行完整 36 条任务。

没有 API Key 时，可运行本地 OpenAI 兼容 Mock：

```bash
trajectiq-openai-demo --mock --task-id refund_001 --output exports/mock-agent.json
```

Mock 会返回固定的 `query_order -> search_policy` 工具调用，并使用与真实客户端相同的 HTTP Chat Completions 协议。它验证的是接口、工具循环和轨迹导出链路，不验证真实模型的决策质量。
