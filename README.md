# TrajectIQ

TrajectIQ 是一个面向多工具 Agent 的发布质量诊断平台。项目以 Phoenix 和 OpenTelemetry 提供可观测性基础，在此之上实现版本回归评测、首错定位与 CI 发布门禁。

## 项目状态

`v0.7` 已完成：确定性 Agent 运行时、Phoenix Trace 导出、36 条评测集、回归诊断、YAML 门禁、GitHub Actions 和独立 Dashboard。

## 项目结构

```text
agentguard/
├── src/agentguard/       # Agent 运行时、评测与发布门禁
├── tests/                # 独立测试
├── dashboard/            # React 发布诊断界面
├── ARCHITECTURE.md        # 组件关系与数据流
├── ROADMAP.md             # 版本计划与验收标准
└── release-gate.yaml     # 发布质量阈值
```

## 核心能力

- 以 `baseline`、`regression`、`fixed` 三个版本复现 Agent 行为差异。
- 在 36 条客服任务上评估退款、订单查询、物流、退货政策和人工升级。
- 对基线通过、候选失败的任务识别回归，并定位第一处工具调用分歧。
- 将任务成功率、工具选择、参数正确性、回答覆盖率和关键任务质量写入发布门禁。
- 生成 Dashboard JSON，一页展示发布结论、任务退化和执行轨迹。

其中 `regression` 版本会故意将退款请求错误路由至 `estimate_delivery`。它稳定产生 10 条退款回归，其中 3 条是关键任务；`fixed` 版本可通过默认门禁。

## 本地运行

在项目根目录安装依赖并运行版本：

```bash
python -m pip install -e .[dev]
trajectiq --version baseline
trajectiq --version regression
```

生成回归报告与首错诊断：

```bash
trajectiq-regression --baseline baseline --candidate regression
trajectiq-diagnose --baseline baseline --candidate regression
```

执行发布门禁：

```bash
trajectiq-gate --baseline baseline --candidate fixed
trajectiq-gate --baseline baseline --candidate regression
```

第一个命令输出 `PASS`，第二个命令输出 `BLOCK` 且以状态码 `1` 退出，可直接接入 CI。

## Dashboard

Dashboard 默认加载仓库中由评测命令生成的真实报告，而非手写样例：

```bash
cd dashboard
pnpm install
pnpm dev
```

页面可切换回归版本与修复版本，也支持导入自定义 JSON：

```bash
trajectiq-dashboard-data --baseline baseline --candidate regression --output dashboard-report.json
```

## Phoenix Trace 导出

启动 Phoenix 后执行：

```bash
trajectiq --version baseline --trace --endpoint http://localhost:6006
```

每个任务会生成 `agent_run` 根 Span，以及 `planner`、工具调用和 `final_answer` 子 Span，可在 Phoenix 中查看完整执行链路。

## 项目边界

Phoenix 负责 Trace 存储、界面、数据集和评测基础设施；TrajectIQ 独立实现版本快照、回归比较、首错归因和发布门禁，因此可以作为完整的 Agent 质量工程个人项目运行与演示。
