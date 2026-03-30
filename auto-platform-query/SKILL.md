---
name: auto-platform-query
description: |
  Query automation testing platform for pipelines, tasks, devices, and cases.
  Get task details with performance metrics (FPS, JANK, memory), perform performance comparison, and analyze performance trends.
  CRITICAL: When analyzing tasks, MUST retrieve data for ALL statuses (RUNNING/QUEUE/CANCEL/FAILED/SUCCESS).

  Use when Claude needs to:
  - Query platform data (pipelines, tasks, devices, cases)
  - Get task details with performance metrics - include ALL task statuses
  - Compare performance across builds - include ALL tasks regardless of status
  - Analyze performance trend over a time range using get_pipeline_performance_trend

  Prerequisites: Configure AUTOMATION_PROJECT_ID and AUTOMATION_USER_ID
allowed-tools: Bash, Read, Write
---

# 自动化测试平台查询工具

自动化测试平台数据查询工具 - 查询流水线、任务详情和性能数据。

## 🔥 核心原则

**获取任务详情或进行性能对比时，不管任务和用例的状态如何，都必须获取和展示所有相关数据！**

**任务状态**: RUNNING, QUEUE, CANCEL, FAILED, SUCCESS
**用例状态**: SUCCESS, FAILED, QUEUE, RUNNING, CANCEL

**禁止**: ❌ 按任务/用例状态过滤数据（例如只显示 SUCCESS）
**必须**: ✅ 包含所有任务/用例状态，即使是 FAILED/CANCEL 数据

---

## 快速开始

### 环境配置

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量（在 .env 或系统环境中）
AUTOMATION_BASE_URL=https://automation-api.testplus.cn
AUTOMATION_PROJECT_ID=your_project_id
AUTOMATION_USER_ID=your_user_id
```

## 工作流决策指南

**重要**: 根据用户请求类型，必须加载对应的 reference 文档执行详细工作流。

### 决策树

```
用户请求类型判断：
├─ "任务详情" / "获取任务" / "查询任务" / "任务执行情况"
│  └─ 加载 references/TASK_DETAIL.md
│
├─ "稳定性测试" / 用例名称包含"稳定性"
│  └─ 加载 references/STABILITY_TEST_DETAIL.md
│
├─ "性能对比" / "对比性能" / "比较多次执行" / "性能变化"
│  └─ 加载 references/PERFORMANCE_COMPARISON.md
│
├─ "性能趋势" / "趋势分析" / "最近N天" / "时间段性能"
│  └─ 加载 references/PERFORMANCE_TREND.md
│
└─ "发现任务" / "查找流水线" / 不知道任务ID
   └─ 使用下方任务发现功能
```

---

## 核心工作流

### 0. 任务发现（统一入口）

**用途**: 在进行详细分析之前，先找到正确的任务或流水线

**何时使用**:
- 开始任何分析但不知道任务/流水线 ID
- 验证哪些任务匹配您的查询
- 从多个匹配任务中选择

**命令**:
```bash
# 根据任务名+时间范围发现任务
python scripts/cli.py tasks --build-name "TDR" --start-time "2026-02-01" --end-time "2026-02-14" --discover
```

**输出**: 精简的任务列表 + 智能推荐

### 1. 查询任务详情

**触发条件**: 用户请求包含 "任务详情"、"获取任务"、"查询任务"、"执行情况" 等关键词

**操作**: 加载 [references/TASK_DETAIL.md](references/TASK_DETAIL.md) 并执行其中的工作流

查询任务执行数据和性能指标。根据任务/用例名称自动路由到适当的工作流。

**稳定性测试专项**: 如果用例名称包含"稳定性"，加载 [references/STABILITY_TEST_DETAIL.md](references/STABILITY_TEST_DETAIL.md)

### 2. 性能对比

**触发条件**: 用户请求包含 "性能对比"、"对比性能"、"比较多次执行"、"性能变化" 等关键词

**操作**: 加载 [references/PERFORMANCE_COMPARISON.md](references/PERFORMANCE_COMPARISON.md) 并执行其中的工作流

对比多次构建的性能指标（FPS、JANK、内存）。支持基础对比和深度对比，自动筛查显著变化。

### 3. 性能趋势分析

**触发条件**: 用户请求包含 "性能趋势"、"趋势分析"、"最近N天"、"时间段" 等关键词，或请求获取流水线在时间范围内的性能变化

**操作**: 加载 [references/PERFORMANCE_TREND.md](references/PERFORMANCE_TREND.md) 并执行其中的工作流

分析时间范围内的性能趋势。生成包含回归检测、异常识别和优化建议的综合报告。

---

## 输出格式

所有 CLI 输出均为 **JSON 格式**（专为 AI Agent 分析设计）：

```json
{
  "type": "device_executions",
  "task": {
    "build_id": 128639,
    "build_name": "...",
    "status": "FAILED",
    "execute_time": 24359,
    "total_cases": 7
  },
  "summary": {
    "case_status_distribution": {"FAILED": 7},
    "device_stats": {
      "total_devices": 9,
      "success_devices": 6,
      "failed_devices": 9
    }
  },
  "cases": [...]
}
```

**完整字段说明**:
- 任务详情: 参见 references/TASK_DETAIL.md
- 性能对比: 参见 references/PERFORMANCE_COMPARISON.md
- 性能趋势: 参见 references/PERFORMANCE_TREND.md

---

### 路径格式（Windows/Git Bash）

**Windows 路径**在 Git Bash 中需要使用 Unix 格式：

| 错误 | 正确 |
|--------|----------|-------------|
| `C:\Users\...` | `/c/Users/...` |
| `cd "C:\Users\..."` | `cd "/c/Users/..."` |

---

## 浏览器自动化分析（当 CLI 不可用时）

当 CLI 工具因 SDK 缺失或命令不可用时，使用浏览器自动化获取数据：

### 稳定性测试页面数据提取

页面列结构：
1. 设备名称 | 2. 是否在线 | 3. 机型 | 4. IP | 5. 平台 | 6. 状态 | 7. 耗时 | 8. 开始时间 | 9. 完成时间 | 10. 报告链接 | **11. 性能概况 (FPS TP90 / 内存峰值 / Jank)**

```javascript
// 获取完整设备列表（性能列格式："- 9924.8 -" 表示 FPS=空 / 内存=9924.8MB / Jank=空）
const rows = document.querySelectorAll('table tbody tr');
const devices = [];
rows.forEach(r => {
  const cells = r.querySelectorAll('td');
  if (cells.length > 10) {
    const perfText = cells[10]?.innerText?.trim() || '';
    const perfParts = perfText.split(/\s+/);
    devices.push({
      name: cells[0]?.innerText?.trim(),
      online: cells[1]?.innerText?.trim(),
      model: cells[2]?.innerText?.trim(),
      ip: cells[3]?.innerText?.trim(),
      status: cells[5]?.innerText?.trim(),
      duration: cells[6]?.innerText?.trim(),
      startTime: cells[7]?.innerText?.trim(),
      endTime: cells[8]?.innerText?.trim(),
      fps: perfParts[0] === '-' ? null : perfParts[0],       // FPS TP90（可能为空）
      mem: perfParts[1] === '-' ? null : perfParts[1],       // 内存峰值(MB)
      jank: perfParts[2] === '-' ? null : perfParts[2]       // Jank(次/10min)（可能为空）
    });
  }
});
```

### 设备分类统计标准（核心规则）

**⚠️ 判断顺序（按优先级）：**

| 优先级 | 分类 | 判断条件 | 统计方式 |
|--------|------|---------|---------|
| 1 | ✅ 成功 | **只看状态列**：包含"成功"即为成功 | 计入通过率 |
| 2 | ❌ 失败（在线） | 状态列包含"失败" 且 在线列="在线" | 计入通过率 |
| 3 | 🔴 失败（离线） | 状态列包含"失败" 且 在线列="离线" | **不计入通过率** |
| 4 | 🔄 运行中 | 状态列包含"运行中" | 不计入完成统计 |

**关键**：成功只看状态列，与"在线列"无关！即使设备离线，只要状态列是"成功"就算成功。

**通过率计算公式**: `成功数 / (成功数 + 失败在线数)`

### 稳定性测试关键指标

1. **执行时长**: 成功设备应达到约6小时
2. **内存峰值**: PC 平台正常范围 6000-12000 MB
3. **FPS TP90 / Jank**: ⚠️ **可能为空**，仅当任务配置采集时才显示
4. **通过率基准**: ≥80% 为达标
5. **失败模式分析**:
   - 极早期失败（<30分钟）：启动/崩溃问题
   - 早期失败（1-2小时）：低配兼容性问题
   - 中途失败（3-5小时）：内存/稳定性问题

### 报告列显示规则

| 表格列名 | 数据来源 | 显示条件 |
|----------|---------|---------|
| **内存峰值(MB)** | perfParts[1] | **始终显示**（必填项） |
| FPS TP90 | perfParts[0] | 有数据时显示，为 `-` 时省略 |
| Jank(次/10min) | perfParts[2] | 有数据时显示，为 `-` 时省略 |

**⚠️ 重要：页面表头顺序为 `FPS TP90 | 内存峰值(MB) | Jank`，对应 perfParts 索引为 `[0] | [1] | [2]`**

---

## 常见问题

**问: 可以查询 RUNNING/CANCEL 状态的任务详情吗？**
答: **可以！** 获取任务详情时不考虑状态（RUNNING/QUEUE/CANCEL/FAILED/SUCCESS 都可以）。

**问: 为什么要读取 references 文档？**
答: References 包含完整的工作流、数据结构、性能标准和最佳实践。

**问: 性能报告是如何生成的？**
答: 由 AI Agent 分析 JSON 数据生成 - 不是由 Python 脚本生成。AI 提供灵活、智能的分析。

**问: 输出格式是什么？**
答: 仅 JSON（专为 AI Agent 设计）。AI Agent 解析 JSON 并生成 Markdown 报告。

**问: CLI 命令缺失怎么办？**
答: 使用浏览器自动化直接抓取页面数据，参考上方的"浏览器自动化分析"章节。
