# Phoenix 与 TrajectIQ 面试学习手册

这份文档用于准备 TrajectIQ 项目的技术面试。目标不是背 API，而是能够清楚回答四个问题：

1. Phoenix 和 OpenTelemetry 分别解决什么问题？
2. TrajectIQ 如何判断 Agent 版本发生了回归？
3. 它如何从 Trace 定位第一个错误？
4. 为什么这套方案适合接入 CI，而不是只做离线分析？

---

## 一、先记住项目主线

TrajectIQ 解决的是：**Agent 更新之后，如何自动发现质量下降、定位原因，并阻止风险版本发布。**

完整链路是：

```text
用户任务
  -> Agent 规划与工具调用
  -> OpenTelemetry / OpenInference Trace
  -> TrajectIQ 轨迹适配器
  -> 基线与候选版本对比
  -> 任务回归识别
  -> 首错归因
  -> YAML 发布门禁
  -> CI / PR 反馈 / Dashboard
```

面试时可以先用一句话概括：

> TrajectIQ 是一个面向多工具 Agent 的发布质量平台，它通过 Trace 驱动的版本回归评测和首错归因，在 CI 中自动阻断 Agent 工具调用退化。

---

## 二、OpenTelemetry 是什么

### 2.1 解决的问题

如果 Agent 只返回最终答案，我们只能知道“答错了”，不知道：

- 它有没有调用工具？
- 调用了哪个工具？
- 工具参数是否正确？
- 哪一步开始偏离预期？
- 工具失败还是模型规划错误？

OpenTelemetry，简称 OTel，是一套与具体厂商无关的可观测性标准。它定义了如何产生、传输和导出 Trace、Metric、Log。TrajectIQ 主要使用 Trace。

### 2.2 Trace、Span、Attribute

- **Trace**：一次完整请求的执行链路。
- **Span**：Trace 中的一个操作步骤，例如 Agent、LLM、工具调用。
- **Attribute**：Span 上的结构化字段，例如工具名、输入、输出和错误。

一个 Agent Trace 可以理解为一棵树：

```text
agent_run
├── planner
├── llm_turn
├── query_order
├── search_policy
└── final_answer
```

Span 通常包含：

```json
{
  "trace_id": "trace-001",
  "span_id": "span-003",
  "parent_id": "span-001",
  "name": "query_order",
  "start_time": 100,
  "end_time": 120,
  "status_code": "OK",
  "attributes": {
    "openinference.span.kind": "TOOL",
    "tool.name": "query_order",
    "input.value": "{\"order_id\":\"A1001\"}"
  }
}
```

### 2.3 为什么不用普通日志

普通日志主要是文本，难以可靠地表达父子关系、跨服务 Trace ID 和结构化输入输出。Trace 的优势是：

- 能按一次请求聚合完整执行链路；
- 能保留步骤顺序和父子关系；
- 能在 Phoenix 中按工具、错误、项目和时间筛选；
- 能被下游评测器和回归分析程序读取。

面试回答：

> 日志适合记录事件，Trace 适合还原一次请求的执行过程。Agent 的问题通常发生在中间步骤，所以必须保留工具调用和模型决策链路，而不是只保存最终答案。

---

## 三、Phoenix 是什么

Phoenix 是 Arize 提供的 AI/LLM 可观测性平台。它建立在 OpenTelemetry 和 OpenInference 之上，主要提供：

- Trace 接收与存储；
- Agent、LLM、Tool、Retriever 等 Span 的可视化；
- 输入、输出、Token、错误和延迟查看；
- 数据集、实验和评测能力；
- 本地运行与 Phoenix Cloud 部署方式。

在这个项目里，Phoenix 不是 TrajectIQ 的全部，而是**观测基础设施**。TrajectIQ 在它之上增加了：

- 版本之间的回归比较；
- 基线通过、候选失败的任务识别；
- 首个错误工具调用定位；
- YAML 质量门禁；
- CI 和 Dashboard 发布反馈。

面试时要明确边界：

> Phoenix 负责采集、存储和探索 Trace；TrajectIQ 负责面向发布流程的版本比较、回归判断、归因和门禁。

---

## 四、OpenInference 语义约定

OpenInference 是面向 AI 应用的 Span 语义约定。它在 OTel 的通用 Span 上定义 AI 场景需要的字段。

### 4.1 常见 Span Kind

| Span Kind | 含义 | TrajectIQ 中的用途 |
| --- | --- | --- |
| `AGENT` | 自主规划或多步 Agent 执行 | 表示一次 Agent 运行 |
| `LLM` | 模型调用 | 记录模型输入输出 |
| `TOOL` | 外部函数或 API 调用 | 识别工具序列和参数 |
| `CHAIN` | 应用编排步骤 | 表示工作流节点 |
| `RETRIEVER` | 检索步骤 | 未来可用于 RAG 质量分析 |
| `EVALUATOR` | 评测步骤 | 表示评测器本身 |

### 4.2 TrajectIQ 依赖的关键字段

```text
openinference.span.kind = TOOL
tool.name = query_order
input.value = {"order_id": "A1001"}
output.value = {"status": "delivered"}
error.type = tool_error
trajectiq.task_id = refund_001
```

其中：

- `openinference.span.kind` 用来判断 Span 是否为工具调用；
- `tool.name` 用来恢复工具名；
- `input.value` 用来检查工具参数；
- `output.value` 用于诊断工具结果和最终回答；
- `error.type` 或 OTel 错误状态用于识别执行错误；
- `trajectiq.task_id` 将 Trace 关联到评测任务。

### 4.3 为什么属性是扁平字符串

Phoenix/OTel 导出经常把复杂对象序列化成字符串，例如：

```json
{"input.value": "{\"order_id\": \"A1001\"}"}
```

TrajectIQ 的适配器会尝试 JSON 解析字符串，使它恢复为 Python 字典，再和评测集里的期望参数比较。

---

## 五、TrajectIQ 的核心数据模型

### 5.1 Task：评测任务

每条任务描述“用户输入是什么，以及正确行为应该是什么”：

```json
{
  "task_id": "refund_001",
  "category": "refund_timeline",
  "tags": ["refund", "critical"],
  "input": "When will my refund arrive?",
  "expected_tools": ["query_order", "search_policy"],
  "expected_arguments": {"query_order": {"order_id": "A1001"}},
  "expected_answer_contains": ["3-5"],
  "critical": true
}
```

当前数据集有 36 条任务，覆盖：

- 退款时间和退款状态；
- 订单状态；
- 物流预计到达；
- 退货政策；
- 人工升级。

### 5.2 AgentVersion：被比较的版本

```python
AgentVersion(
    name="baseline",
    prompt_revision="prompt-v1",
    tool_policy="baseline",
)
```

项目内置三个版本：

- `baseline`：预期行为；
- `regression`：故意将退款请求错误路由到物流工具；
- `fixed`：修复后的行为。

这是一种确定性 Fixture，目的是稳定复现质量问题，而不是模拟真实模型随机性。

### 5.3 标准化轨迹

无论轨迹来自内置 Agent、OpenAI 示例还是 Phoenix 导出，都会转成：

```json
{
  "task_id": "refund_001",
  "answer": "...",
  "spans": [
    {"kind": "planner", "name": "planner"},
    {"kind": "tool", "name": "query_order", "input": {"order_id": "A1001"}},
    {"kind": "final", "name": "final_answer"}
  ]
}
```

这是一个重要的架构边界：**适配器负责格式差异，评测器只处理统一轨迹。**

---

## 六、回归评测如何工作

### 6.1 单任务评测

`evaluate_task()` 会检查三类条件：

```text
工具序列正确
AND 工具参数正确
AND 回答包含期望信息
=> 任务成功
```

对应代码在 `src/trajectiq/regression.py`。

工具序列使用精确匹配：

```python
actual_tools == task.expected_tools
```

例如：

```text
期望：query_order -> search_policy
实际：estimate_delivery
结果：工具选择错误
```

### 6.2 版本比较

`compare_results()` 会：

1. 分别评估 baseline 和 candidate；
2. 按 `task_id` 对齐两边结果；
3. 只把“baseline 成功、candidate 失败”的任务定义为回归；
4. 计算类别切片统计；
5. 生成 JSON 或 Markdown 报告。

### 6.3 为什么不是“候选失败就算回归”

因为测试集中可能本来就有失败任务。

```text
baseline 失败，candidate 失败：历史问题，不是新回归
baseline 成功，candidate 失败：新版本引入回归
baseline 成功，candidate 成功：没有回归
baseline 失败，candidate 成功：修复或提升，不算回归
```

这就是项目中最重要的判定原则之一。

### 6.4 当前指标

| 指标 | 含义 |
| --- | --- |
| Task success rate | 完整满足工具、参数和答案断言的任务比例 |
| Tool selection accuracy | 工具序列完全匹配的比例 |
| Tool argument accuracy | 工具序列正确且参数正确的比例 |
| Answer coverage | 最终答案包含全部关键断言的比例 |
| Critical task success rate | 关键任务成功比例 |
| Average steps | 平均工具调用数量 |

---

## 七、首错归因如何工作

回归检测告诉我们“哪些任务坏了”，首错归因告诉我们“最早在哪里坏了”。

### 7.1 对齐算法

对 baseline 和 candidate 的工具 Span 按顺序逐步比较：

```text
step 1: baseline=query_order, candidate=query_order
step 2: baseline=search_policy, candidate=estimate_delivery
=> 第 2 步是首个工具选择错误
```

### 7.2 错误分类

- `tool_selection_error`：选择了不同工具、少调用或多调用工具；
- `tool_argument_error`：同一个工具的参数不同；
- `tool_execution_error`：工具返回错误；
- `generation_error`：工具轨迹一致，但最终回答不满足断言。

### 7.3 为什么定位“第一处”错误

后续错误可能都是前一个错误的连锁结果。比如：

```text
错误规划 -> 错误工具 -> 错误工具结果 -> 错误回答
```

修复最早的错误点，通常比逐个修复后续症状更有效。

---

## 八、发布门禁与 CI

`release-gate.yaml` 中配置质量阈值：

```yaml
thresholds:
  minimum_success_rate: 0.90
  maximum_success_rate_drop: 0.03
  minimum_tool_selection_accuracy: 0.95
  maximum_critical_task_regressions: 0
  maximum_task_regressions: 0
```

门禁状态：

- `PASS`：没有违反规则；
- `WARNING`：有非阻断问题；
- `BLOCK`：违反阻断规则，命令以非零状态码退出。

CI 做四件事：

1. 安装项目；
2. 运行自动化测试；
3. 执行发布门禁；
4. 上传 Markdown Artifact、写入 Actions Summary，并更新 Pull Request 质量评论。

### 为什么真实模型不直接进入 CI

这是一个工程取舍：

- 真实 API 需要密钥；
- 每次 CI 会产生费用；
- 模型输出可能随机；
- 外部网络会造成不稳定；
- 回归测试需要可重复。

所以 CI 使用确定性 Fixture，而真实 OpenAI 兼容 Agent 作为人工演示和集成验证入口。

---

## 九、OpenAI 兼容 Agent 示例

`trajectiq-openai-demo` 使用 Chat Completions 的工具调用协议：

```text
用户任务
  -> messages + tools 发送给模型
  -> 模型返回 tool_calls
  -> TrajectIQ 执行本地工具
  -> tool 结果回传模型
  -> 模型生成最终回答
```

它会产生：

- `AGENT` 根 Span；
- `LLM` 模型调用 Span；
- `TOOL` 工具调用 Span。

默认只运行单个任务，`--all` 才运行完整数据集。API Key 从 `OPENAI_API_KEY` 读取，不进入报告和仓库。

---

## 十、Phoenix 与 TrajectIQ 的代码地图

| 文件 | 需要理解的内容 |
| --- | --- |
| `src/trajectiq/agent.py` | 确定性 Agent、工具路由、Span 生成 |
| `src/trajectiq/openai_compatible.py` | 真实模型工具调用、LLM/Tool Trace |
| `src/trajectiq/telemetry.py` | OTLP HTTP 导出到 Phoenix |
| `src/trajectiq/openinference.py` | Phoenix/OTel 原始 Span 适配 |
| `src/trajectiq/trace_io.py` | 外部轨迹输入和回归 CLI |
| `src/trajectiq/dataset.py` | JSONL 数据集加载和校验 |
| `src/trajectiq/regression.py` | 指标、版本比较、类别切片 |
| `src/trajectiq/attribution.py` | 首错定位与错误分类 |
| `src/trajectiq/gate.py` | YAML 质量门禁与 Markdown 输出 |
| `src/trajectiq/dashboard_data.py` | Dashboard 统一 JSON |
| `.github/workflows/release-gate.yml` | 测试、门禁、Artifact、PR 反馈 |
| `dashboard/src/App.tsx` | Dashboard 数据状态与交互 |

---

## 十一、面试高频问题与回答

### Q1：为什么选择 Phoenix，而不是自己写 Trace 存储？

**回答：**

Phoenix 已经解决了 OTel Trace 接收、存储、查询和可视化，自己重写这些基础设施会分散项目重点。我的工作重点是 Phoenix 之上的 Agent 质量工程：版本比较、首错归因和发布门禁。

### Q2：OpenTelemetry 和 OpenInference 有什么关系？

**回答：**

OpenTelemetry 是通用的可观测性传输和数据模型；OpenInference 是针对 AI 应用的语义约定，例如 AGENT、LLM、TOOL Span 以及 `tool.name`、`input.value` 等字段。TrajectIQ 使用 OTel 传输 Trace，用 OpenInference 解释 AI Span。

### Q3：为什么工具序列要精确匹配？

**回答：**

工具选择和参数是强约束业务行为，精确匹配能给出可解释、可重复的 CI 判断。开放式回答不能只依赖关键词，生产环境可以增加 LLM-as-a-Judge 或人工标注，但必须保留确定性规则作为基础护栏。

### Q4：如果 baseline 自己就失败怎么办？

**回答：**

它不会被定义为新回归。项目只把 baseline 成功、candidate 失败的任务算作回归；历史失败应单独作为基线质量问题管理。

### Q5：为什么要保存标准化轨迹？

**回答：**

不同 Agent 框架的 Trace 格式不同。将 Phoenix 导出、OpenAI 示例和内置 Agent 统一成 `task_id + answer + spans` 后，适配器和评测器解耦，新增框架只需要实现输入适配。

### Q6：如何避免 CI 因模型随机性变红？

**回答：**

CI 使用确定性 Agent Fixture 和版本化 JSONL 数据集，不直接调用真实模型。真实模型用于集成演示和脱离 CI 的评测；如果生产化，可以固定模型版本、温度、数据集快照，并用多次运行统计置信区间。

### Q7：项目目前的局限是什么？

**回答：**

目前门禁聚焦任务成功率、工具选择、关键任务和回归数量，尚未完整纳入延迟、Token、成本、统计显著性和历史运行存储。下一步可以通过 Span 时间戳、Token 属性和成本模型补齐这些生产指标。

---

## 十二、建议学习顺序

### 第 1 阶段：先能讲清链路

1. 阅读 `ARCHITECTURE.md`。
2. 运行 `trajectiq-regression --baseline baseline --candidate regression`。
3. 阅读 `regression.py`，理解任务评测和回归定义。
4. 阅读 `attribution.py`，手动跟一遍 `refund_001`。

### 第 2 阶段：理解 Phoenix 与 Trace

1. 区分 Trace、Span、Attribute。
2. 记住 AGENT、LLM、TOOL 三类 Span。
3. 阅读 `telemetry.py`，理解 OTLP endpoint 和 exporter。
4. 阅读 `openinference.py`，理解原始 Span 如何恢复为工具步骤。

### 第 3 阶段：理解工程取舍

1. 为什么 CI 不调用真实 API。
2. 为什么数据集使用 JSONL 版本化。
3. 为什么适配器与评测器分离。
4. 为什么关键任务单独设门禁。

### 第 4 阶段：准备演示

1. Dashboard 展示 `BLOCK`。
2. 点击 `refund_001` 展示首错工具。
3. 展示 `release-gate.yaml` 和 CI 报告。
4. 展示 OpenInference 导入命令。
5. 有 API Key 时再展示 `trajectiq-openai-demo`。

---

## 十三、练习题

1. 把 `refund_001` 的候选工具从 `estimate_delivery` 改成 `query_order`，预测门禁结果。
2. 新增一条 JSONL 任务，并说明它的 expected tools 和 critical 标记。
3. 构造一个参数错误，确认归因类别变成 `tool_argument_error`。
4. 构造工具执行错误，确认归因类别变成 `tool_execution_error`。
5. 删除工具但保持最终回答正确，观察任务为什么仍然失败。
6. 给 Trace 增加 `status_code=ERROR`，观察 OpenInference 适配器如何保留错误。
7. 解释为什么 `baseline` 和 `candidate` 必须使用同一批任务。
8. 设计一个 `maximum_latency_ms` 门禁，并说明它应该读取哪个 Span 字段。

完成这些练习后，你应该能独立解释项目的架构、指标、Trace 语义、失败分类、CI 取舍和生产化方向，而不是只会复述 README。
