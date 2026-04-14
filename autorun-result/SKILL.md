---
name: autorun-result
description: |
  读取项目每日稳定性测试结果，按天汇总PC、XBox、PS5、NS2四个平台的运行情况。
  按平台、版本、任务进行层级统计，输出格式化的Markdown报告，便于更新到在线文档。
  
  使用场景：
  - 每日自动化测试结果汇总
  - 多平台稳定性监控日报
  - 在线文档每日更新

  核心功能：
  1. 按日期统计（默认当天）
  2. 按平台和版本分组
  3. 设备执行时长统计（>4小时）
  4. 异常设备检测（崩溃、提前退出）
  5. 生成可直接复制到在线文档的Markdown格式

  触发词：星砂 今日稳定性执行详情, 星砂 稳定性执行情况, 剑世4 今日稳定性执行情况, 剑世4 稳定性执行情况，星砂 2026.04.14稳定性执行情况, 剑世4 2026.04.14稳定性执行情况

allowed-tools: Bash, Read, Write, Exec
---

## 聊天触发与自动化执行

当用户在聊天中输入以下短语之一时，执行对应脚本并以指定模板生成输出文档：

| 触发短语 | 执行脚本 | 使用模板 | 输出文件 |
|----------|----------|----------|----------|
| `星砂 今日稳定性执行详情` | `python scripts/WPS_StabilitySummary.py` | `references/START_TEMPLATE.md` | `start_result_model_v2_output.md` |
| `星砂 稳定性执行情况` | `python scripts/WPS_StabilitySummary.py` | `references/START_TEMPLATE.md` | `start_template_output.md` |
| `剑世4 今日稳定性执行情况` | `python scripts/WPS_StabilitySummaryJXSJ4.py` | `references/JXSJ4_TEMPLATE.md` | `jxsj4_template_output.md` |
| `剑世4 稳定性执行情况` | `python scripts/WPS_StabilitySummaryJXSJ4.py` | `references/JXSJ4_TEMPLATE.md` | `jxsj4_template_output.md` |

说明：
- 请确保 Python 环境已配置并安装脚本依赖。
- 如果需要不同日期，可在命令中加入 `--date YYYY-MM-DD` 或将 `--date 今日` 改为自然语言解析由脚本处理。

实现建议给 AI Agent 的发现点：
- 在 `description` 中包含触发词（已添加），以便 agent 能检索到该技能。
- 为确保确定性，agent 在检测到完全匹配短语时应调用对应的命令并返回生成的输出文件内容给用户。

## Agent 工作流程

当检测到触发短语时，根据上方触发短语映射执行对应脚本：

执行步骤：

1. **运行脚本**：在工作区根目录执行对应命令
2. **读取输出**：读取生成的输出文件内容
3. **返回结果**：将文件内容作为响应返回给用户

如果脚本执行失败或文件未生成，返回错误信息并建议检查 Python 环境和依赖。

