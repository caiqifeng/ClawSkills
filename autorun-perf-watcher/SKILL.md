---
name: autorun-perf-watcher
version: 1.0.0
description: |
  监控自动化任务的性能运行情况，统计当天流水线执行状态、失败设备、性能异常等。
  支持对比近一周的性能基线（FPS TP90、内存峰值、Jank），自动检测性能回归问题。

  使用场景:
  - 当天流水线执行情况监控
  - 性能数据对比分析（当天 vs 近一周基线）
  - 异常设备汇总
  - 性能回归检测

  核心功能:
  1. 统计当天流水线成功/失败案例
  2. 汇总失败设备列表
  3. 提取性能数据（FPS TP90、内存峰值、Jank）
  4. 对比近一周性能基线，检测异常

  触发词：星砂 性能监控，星砂 流水线执行情况，星砂 性能异常检测

allowed-tools: Bash, Read, Write, Exec
---

# Skill: 自动化任务性能监控 (Automation Performance Watcher)

## Description
本 Skill 用于监控自动化平台上特定流水线的性能运行情况，包括执行状态统计、失败设备汇总、性能数据趋势分析和异常检测。

## Capabilities
- 实时查询流水线的执行状态（Success, Failed, Running）
- 统计每个流水线的成功率和失败率
- 汇总失败设备列表，按失败原因分类
- 获取近一周的性能数据（FPS、内存、Jank）
- 自动检测性能异常和回归问题
- 生成可视化的性能趋势报告

## Prerequisites
- 需要拥有自动化平台的 API Token
- OpenClaw 环境需能访问平台后端接口（https://uauto2.testplus.cn）
- Python 环境已配置并安装必要依赖

## 项目配置

### 星砂岛物语 (starsandisland)
- **项目 ID**: `starsandisland`
- **监控流水线 ID**: `932, 1103, 1084, 1090`
- **流水线说明**:
  - `932`: PC 性能测试
  - `1103`: Xbox 性能测试
  - `1084`: PS5 性能测试
  - `1090`: NS2 性能测试

## Instructions

### 1. 查询流水线执行情况
当用户请求查看流水线执行情况时：
1. 调用 `GET /api/build/list?pipelineId={id}&pageSize=50` 获取最近的执行记录
2. 统计成功（SUCCESS）和失败（FAILED）的任务数量
3. 计算成功率：`成功率 = 成功数 / 总数 × 100%`
4. 按流水线分组展示统计结果

### 2. 汇总失败设备
当需要分析失败设备时：
1. 筛选出状态为 FAILED 的任务
2. 调用 `GET /api/task/detail/{taskId}` 获取每个失败任务的设备列表
3. 提取状态为 `error` 或 `failed` 的设备信息
4. 按失败原因分类汇总（崩溃、超时、环境异常等）
5. 生成失败设备清单，包含设备 ID、失败原因、失败时间

### 3. 获取性能数据
当需要查询性能数据时：
1. 调用 `GET /api/performance/query` 获取近 7 天的性能数据
2. 参数设置：
   - `pipelineIds`: `932,1103,1084,1090`
   - `startDate`: 当前日期 - 7 天
   - `endDate`: 当前日期
   - `metrics`: `fps,memory,jank`
3. 按日期和流水线分组整理数据
4. 计算每个指标的平均值、最大值、最小值

### 4. 性能异常检测
当需要检测性能异常时：
1. 获取近 7 天的性能数据作为基线
2. 对比最新一次执行的性能数据
3. 异常判断规则：
   - **FPS 异常**: 平均 FPS 下降 > 10% 或低于 30 FPS
   - **内存异常**: 内存使用增长 > 20% 或超过 4GB
   - **Jank 异常**: Jank 次数增加 > 30% 或超过 100 次/分钟
4. 生成异常报告，标注异常类型和严重程度

## Tool Definitions (Python/API)

### get_pipeline_stats
- **Input**: `pipeline_ids` (list), `days` (int, default=7)
- **Output**: JSON 格式的流水线统计信息
- **Description**: 获取指定流水线在指定天数内的执行统计

### get_failed_devices
- **Input**: `pipeline_ids` (list), `start_date` (string), `end_date` (string)
- **Output**: 失败设备列表，包含设备 ID、失败原因、任务链接
- **Description**: 汇总指定时间范围内的失败设备信息

### get_performance_data
- **Input**: `pipeline_ids` (list), `metrics` (list), `days` (int)
- **Output**: 性能数据时间序列，包含 FPS、内存、Jank 等指标
- **Description**: 获取指定流水线的性能数据

### detect_performance_anomaly
- **Input**: `pipeline_id` (string), `baseline_days` (int, default=7)
- **Output**: 异常检测结果，包含异常类型、严重程度、对比数据
- **Description**: 检测性能异常和回归问题

## User Conversation Examples
- "帮我看看星砂的流水线执行情况"
- "星砂 性能监控"
- "星砂 近一周性能情况"
- "星砂 流水线 932、1103、1084、1090 的成功率是多少？"
- "汇总一下星砂最近失败的设备"
- "星砂 性能异常检测"
- "检查星砂是否有性能回归"

## 聊天触发与自动化执行

当用户在聊天中输入以下短语之一时，执行对应的监控脚本：

| 触发短语 | 执行命令 | 输出文件 |
|----------|----------|----------|
| `星砂 性能监控` | `python scripts/perf_watcher.py --project starsandisland --pipelines "932,1103,1084,1090" --output perf_report.md` | `perf_report.md` |
| `星砂 流水线执行情况` | `python scripts/perf_watcher.py --project starsandisland --pipelines "932,1103,1084,1090" --mode stats --output pipeline_stats.md` | `pipeline_stats.md` |
| `星砂 性能异常检测` | `python scripts/perf_watcher.py --project starsandisland --pipelines "932,1103,1084,1090" --mode anomaly --output anomaly_report.md` | `anomaly_report.md` |
| `星砂 近一周性能情况` | `python scripts/perf_watcher.py --project starsandisland --pipelines "932,1103,1084,1090" --days 7 --output weekly_perf.md` | `weekly_perf.md` |

### 命令参数说明
- `--project`: 项目 ID (starsandisland)
- `--pipelines`: 流水线 ID 列表，用逗号分隔
- `--mode`: 执行模式
  - `stats`: 统计执行情况（默认）
  - `anomaly`: 性能异常检测
  - `full`: 完整报告（包含统计 + 性能 + 异常）
- `--days`: 查询天数，默认 7 天
- `--output`: 输出文件名
- `--date`: (可选) 指定结束日期，格式 YYYY-MM-DD，默认为当天

## 报告模板

### 流水线执行情况报告

```markdown
# 星砂岛物语 - 流水线执行情况报告

**统计时间**: {target_date}

## 一、执行概览

| 流水线 ID | 流水线名称 | Case 总数 | Case 成功 | Case 失败 | 设备总数 | 设备成功 | 设备失败 | 最新任务 |
|-----------|-----------|----------|----------|----------|---------|---------|---------|----------|
| 932 | PC 性能测试 | **12** | **11** | **1** | **120** | **118** | **2** | [查看](链接) |
| 1084 | PS5 性能测试 | **11** | **2** | **9** | **44** | **31** | **13** | [查看](链接) |
| 1090 | NS2 性能测试 | **33** | **1** | **32** | **66** | **10** | **56** | [查看](链接) |
| 1103 | Xbox 性能测试 | **11** | **7** | **4** | **33** | **23** | **10** | [查看](链接) |

**总计**:
- 任务层级：共 **6** 次，成功 **0** 次，失败 **1** 次，运行中 **4** 次
- Case层级：共 **67** 个，成功 **21** 个，失败 **46** 个
- 设备层级：共 **263** 台，成功 **182** 台，失败 **81** 台

## 二、性能数据对比

### PC 性能测试 (932)

| 测试场景 | FPS TP90/基线 | 内存峰值（MB）/基线 | Jank（/10min）/基线 |
|----------|---------------|---------------------|--------------------|
| 主城跑图(TDR) | 81.0 / 92.7 (↓12.7%) ⚠️ | 9124.8 / 9062.5 (↑0.7%)  | 3.9 / 6.7 (↓42.1%)  |
| 新手流程-制造师师初见剧情(TDR) | 106.5 / 92.7 (↑14.9%)  | 8728.4 / 9062.5 (↓3.7%)  | 18.1 / 6.7 (↑172.7%) ⚠️ |

### 性能异常检测

⚠️ **检测到 3 个性能异常**：

- **设备名称** - 新手流程-制造师师初见剧情(TDR)
  - Jank 增加 172.7% (当前: 18.1, 基线: 6.7)
  - [查看 Perfeye](链接)

✅ **其他平台性能正常**
```

## Agent 工作流程

当检测到触发短语时，根据触发短语映射表执行对应的监控脚本：

执行步骤：

1. **识别触发词**: 匹配用户输入与触发短语表
2. **运行脚本**: 在工作区根目录执行对应命令
3. **读取输出**: 读取生成的输出文件内容
4. **格式化输出**: 将报告内容以 Markdown 格式返回给用户（不使用代码块）
5. **异常处理**: 如果脚本执行失败，返回错误信息并建议检查环境

### 注意事项
- 报告必须直接以 Markdown 格式输出，不能使用 ``` 代码块包裹
- 保留所有超链接的可点击性
- 数字和关键指标需要加粗显示
- 性能趋势使用箭头符号（↑ ↓ →）表示变化方向
- 异常检测结果需要明确标注严重程度
