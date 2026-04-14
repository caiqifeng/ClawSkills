---
name: autorun-result
description: |
  读取项目每日稳定性测试结果,按天汇总PC、XBox、PS5、NS2四个平台的运行情况。
  按平台、版本、任务进行层级统计,输出格式化的Markdown报告,便于更新到在线文档。

  使用场景:
  - 每日自动化测试结果汇总
  - 多平台稳定性监控日报
  - 在线文档每日更新

  核心功能:
  1. 按日期统计(默认当天)
  2. 按平台和版本分组
  3. 设备执行时长统计(>4小时)
  4. 异常设备检测(崩溃、提前退出)
  5. 生成可直接复制到在线文档的Markdown格式

  触发词:星砂 今日稳定性执行详情, 星砂 稳定性执行情况, 剑世4 今日稳定性执行情况, 剑世4 稳定性执行情况, 输出 剑世4 今日稳定性执行情况, 星砂 2026.04.14稳定性执行情况, 剑世4 2026.04.14稳定性执行情况

allowed-tools: Bash, Read, Write, Exec
---

## 聊天触发与自动化执行

当用户在聊天中输入以下短语之一时,执行对应脚本并以指定模板生成输出文档:

| 触发短语 | 执行脚本 | 使用模板 | 输出文件 |
|----------|----------|----------|----------|
| `星砂 今日稳定性执行详情` | `python scripts/WPS_StabilitySummary.py` | `assets/START_TEMPLATE.md` | `start_result_model_v2_output.md` |
| `星砂 稳定性执行情况` | `python scripts/WPS_StabilitySummary.py` | `assets/START_TEMPLATE.md` | `start_template_output.md` |
| `剑世4 今日稳定性执行情况` | `python scripts/WPS_StabilitySummaryJXSJ4.py` | `assets/JXSJ4_TEMPLATE.md` | `jxsj4_report_final.md` |
| `剑世4 稳定性执行情况` | `python scripts/WPS_StabilitySummaryJXSJ4.py` | `assets/JXSJ4_TEMPLATE.md` | `jxsj4_report_final.md` |

说明:
- 请确保 Python 环境已配置并安装脚本依赖。
- 如果需要不同日期,可在命令中加入 `--date YYYY-MM-DD` 或将 `--date 今日` 改为自然语言解析由脚本处理。

实现建议给 AI Agent 的发现点:
- 在 `description` 中包含触发词(已添加),以便 agent 能检索到该技能。
- 为确保确定性,agent 在检测到完全匹配短语时应调用对应的命令并返回生成的输出文件内容给用户。

## 报告模板
注意：报告必须手动输出，不可用脚本生成

- 生成报告前，必须先 read assets对应的报告模板，并且要按对应项目模板，再按它输出；
- **剑世4格式要求（2026.04.14更新）**：
  - 平台标题加粗：`**一、PC共{M}台设备，其中{N}台执行超过4小时。**`、`**二、android共{M}台设备，其中{N}台执行超过4小时。**`、`**三、ios共{M}台设备，其中{N}台执行超过4小时。**`
  - 设备数加粗：`共**N**台设备`、`其中**M**台执行超过4小时`
  - 任务行数字加粗：`共**N**台设备，其中**M**台设备执行超过4小时`
  - 异常数加粗：`发现**X**台异常`
  - 严格按照 `assets/JXSJ4_TEMPLATE.md` 中的最新模板格式执行

- **星砂岛格式要求（2026.04.14更新）**：
  - 平台标题格式：`## 一、PC（共**{N}台**设备，其中**{M}台**执行超过4小时）`
  - 版本行格式：`- （版本：v{version_number}）`
  - 任务行数字加粗：`共**{task_device_count}台**设备，其中**{task_over_4h_count}台**设备执行超过4小时`
  - 异常信息：`{abnormal_info}`（未发现异常 或 以下{X}台出现异常）
  - 平台顺序固定：PC → Xbox → PS5 → NS2
  - 严格按照 `assets/START_TEMPLATE.md` 中的最新模板格式执行

## Agent 工作流程

当检测到触发短语时,根据上方触发短语映射执行对应脚本:

执行步骤:

1. **运行脚本**:在工作区根目录执行对应命令
2. **读取输出**:读取生成的输出文件内容
3. **返回结果**:将文件内容作为响应返回给用户

如果脚本执行失败或文件未生成,返回错误信息并建议检查 Python 环境和依赖。

