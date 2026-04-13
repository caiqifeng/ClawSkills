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

  触发词：星砂 今日稳定性执行详情, 星砂 稳定性执行情况, 剑世4 稳定性执行情况

allowed-tools: Bash, Read, Write, Exec
---

## 聊天触发与自动化执行

当用户在聊天中输入以下短语之一时，执行对应脚本并以指定模板生成输出文档：

### 触发短语 1：星砂 今日稳定性执行详情
- 匹配短语：`星砂 今日稳定性执行详情`
- 执行脚本：`python scripts/WPS_StabilitySummary.py --template start_result_model_v2.md --output start_result_model_v2_output.md`
- 使用模板：`start_result_model_v2.md`

### 触发短语 2：星砂 稳定性执行情况
- 匹配短语：`星砂 稳定性执行情况`
- 执行脚本：`python scripts/WPS_StabilitySummary.py --template references/START_TEMPLATE.md --output start_template_output.md`
- 使用模板：`references/START_TEMPLATE.md`

### 触发短语 3：剑世4 稳定性执行情况
- 匹配短语：`剑世4 稳定性执行情况`
- 执行脚本：`python scripts/WPS_StabilitySummaryJXSJ4.py --template references/JXSJ4_TEMPLATE.md --output jxsj4_template_output.md`
- 使用模板：`references/JXSJ4_TEMPLATE.md`

说明：
- 请确保 Python 环境已配置并安装脚本依赖。
- 如果需要不同日期，可在命令中加入 `--date YYYY-MM-DD` 或将 `--date 今日` 改为自然语言解析由脚本处理。

实现建议给 AI Agent 的发现点：
- 在 `description` 中包含触发词（已添加），以便 agent 能检索到该技能。
- 为确保确定性，agent 在检测到完全匹配短语时应调用对应的命令并返回生成的输出文件内容给用户。

## Agent 工作流程

当检测到触发短语时，根据以下映射执行相应脚本：

| 触发短语 | 执行命令 | 输出文件 |
|----------|----------|----------|
| `星砂 今日稳定性执行详情` | `python scripts/WPS_StabilitySummary.py --template start_result_model_v2.md --output start_result_model_v2_output.md` | `start_result_model_v2_output.md` |
| `星砂 稳定性执行情况` | `python scripts/WPS_StabilitySummary.py --template references/START_TEMPLATE.md --output start_template_output.md` | `start_template_output.md` |
| `剑世4 稳定性执行情况` | `python scripts/WPS_StabilitySummaryJXSJ4.py --template references/JXSJ4_TEMPLATE.md --output jxsj4_template_output.md` | `jxsj4_template_output.md` |

执行步骤：

1. **运行脚本**：在工作区根目录执行对应命令
2. **读取输出**：读取生成的输出文件内容
3. **返回结果**：将文件内容作为响应返回给用户

如果脚本执行失败或文件未生成，返回错误信息并建议检查 Python 环境和依赖。

# 星砂岛日常稳定性汇总技能

自动获取星砂岛四个平台的日常稳定性测试结果，生成结构化Markdown报告，便于更新到在线文档。

## 快速开始

### 环境要求

本技能依赖 `auto-platform-query` 技能的环境配置：
- 已安装 Python 依赖：`pip install -r requirements.txt`
- 已配置环境变量：`AUTOMATION_BASE_URL`, `AUTOMATION_PROJECT_ID`, `AUTOMATION_USER_ID`
- `auto-platform-query` 目录位于工作空间

### 执行命令

```bash
# 生成当天（默认）的汇总报告
cd "C:\root\.openclaw\workspace\star-autorun-result"
python scripts/star_autorun_v2.py

# 生成指定日期的汇总报告
python scripts/star_autorun_v2.py --date 2026-04-02

# 生成JSON格式数据（供AI分析）
python scripts/star_autorun_v2.py --format json

# 仅生成指定平台的报告
python scripts/star_autorun_v2.py --platform pc

# 保存报告到文件（便于更新到在线文档）
python scripts/star_autorun_v2.py --output daily_report.md
```

## 工作流程

### 1. 数据获取流程

```
1. 确定查询日期（默认当天）
2. 按平台获取当天开始的所有任务
   - PC: 流水线ID 946
   - XBox: 流水线ID 953
   - PS5: 流水线ID 954
   - NS2: 流水线ID 1056

3. 对每个任务：
   a. 提取版本信息（从packageUrl）
   b. 获取任务详情（设备执行情况）
   c. 统计设备数和执行时长
   d. 检测异常设备（崩溃、执行不足）

4. 按平台→版本→任务进行数据分组
5. 生成Markdown格式报告
```

### 2. 统计规则

**日期筛选**：
- 默认：当天日期（系统时间）
- 支持：指定任意日期（YYYY-MM-DD格式）
- 筛选：任务开始时间（startTime）在指定日期

**版本提取**：
- 从 `model.baseInfo.packageUrl` 提取
- 格式：`SimSandbox_v{version}_release_il2cpp_no_login_pre_zh-cn.zip`
- 版本：提取 `v1.0.0.8137.197081` 格式

**设备统计**：
- 总设备数：任务分配的设备总数
- 在线设备：deviceStatus = 1 的设备
- 执行超4小时设备：执行时长 ≥ 4小时（14400秒）
- 异常设备：执行不足4小时且有崩溃记录

**执行时长计算**：
- 执行时长 = 设备结束时间 - 设备开始时间
- 需要完整的开始和结束时间
- 仅统计在线设备
- 超时阈值：4小时（14400秒）

## 输出格式

### Markdown报告格式（默认）

```markdown
# 2026.04.02《星砂岛物语》稳定性汇总

## 一、PC（共40台设备，其中33台执行超过4小时）
1. （版本：v1.0.0.8137.197081）
  - 1.[197081分支更新包稳定性](https://uauto2.testplus.cn/project/starsandisland/taskDetail?taskId=140173)
    任务执行汇总：共19台设备，其中16台设备执行超过4小时，未发现异常

1. （版本：v1.0.0.8140.197085）
  - 1.[日常稳定性 release（PC）（分支）-#135](https://uauto2.testplus.cn/project/starsandisland/taskDetail?taskId=140100)
    任务执行汇总：共21台设备，其中17台设备执行超过4小时，未发现异常

## 二、Xbox（共6台设备，其中2台执行超过4小时）
1. （版本：v1.0.0.8129.197039）
  - 1.[分支-日常稳定性 release（XBox）-#98](https://uauto2.testplus.cn/project/starsandisland/taskDetail?taskId=140105)
    任务执行汇总：共6台设备，其中2台设备执行超过4小时，以下1台出现异常
    - xbox_XSS_160.126_海外（10.11.160.126）执行了3小时44分28秒，在UI遍历出现宕机 [Crasheye](https://crasheye2.testplus.cn/project/starsandisland/vk/u3zy0p16/error?viewNoDumpFile=false&searchs=dump_name%7Ci%7C10.11.160.126_StarsandIsland.exe.824.dmp&startTime=2026-04-02&endTime=2026-05-02) | [Perfeye](https://perfeye.testplus.cn/case/69cda13627a1f09a0aa66953/report?appKey=starsandisland)

## 三、PS5（共2台设备，其中0台执行超过4小时）
1. （版本：v1.0.0.8130.197039）
  - 1.[分支-日常稳定性（PS5）-#88](https://uauto2.testplus.cn/project/starsandisland/taskDetail?taskId=140106)
    任务执行汇总：共2台设备，其中0台设备执行超过4小时，未发现异常

## 四、Switch（共2台设备，其中0台执行超过4小时）
1. （版本：v1.0.0.8128.197039）
  - 1.[分支-日常稳定性 release（NS2）-#24](https://uauto2.testplus.cn/project/starsandisland/taskDetail?taskId=140104)
    任务执行汇总：共2台设备，其中0台设备执行超过4小时，未发现异常
```

### JSON格式（AI Agent分析用）

```json
{
  "type": "star_autorun_daily",
  "date": "2026-04-02",
  "generated_at": "2026-04-02 17:30:00",
  "platforms": {
    "pc": {
      "platform": "PC",
      "pipeline_id": 946,
      "total_devices": 40,
      "devices_over_4h": 33,
      "versions": {
        "v1.0.0.8137.197081": [
          {
            "task_id": 140173,
            "task_name": "197081分支更新包稳定性",
            "status": "FAILED",
            "start_time": "2026-04-02T17:28:29",
            "end_time": null,
            "total_devices": 19,
            "devices_over_4h": 16,
            "abnormal_devices": [],
            "task_url": "https://uauto2.testplus.cn/project/starsandisland/taskDetail?taskId=140173"
          }
        ]
      }
    }
  },
  "summary": {
    "total_platforms": 4,
    "platforms_with_data": 4,
    "overall_devices": 50,
    "overall_devices_over_4h": 35
  }
}
```

## AI Agent分析要点

### 数据分析维度
1. **按日期分析**：当天测试覆盖情况
2. **按平台分析**：各平台测试资源和执行情况
3. **按版本分析**：不同版本的稳定性表现
4. **异常检测**：崩溃、执行不足、设备异常

### 报告生成要求
1. **标题格式**：`YYYY.MM.DD《星砂岛物语》稳定性汇总`
2. **平台顺序**：PC → Xbox → PS5 → Switch
3. **版本分组**：同一版本的任务归为一组
4. **任务列表**：每个任务独立一行，带超链接
5. **异常详情**：异常设备单独列出，包含崩溃链接

### 在线文档更新
1. **格式兼容**：生成可直接复制到飞书/钉钉文档的Markdown
2. **每日更新**：建议通过定时任务自动生成
3. **历史追溯**：支持按日期查询历史数据

## 实现说明

### 核心功能模块
1. **日期筛选**：支持指定日期，默认当天
2. **版本提取**：从packageUrl解析出版本号
3. **设备统计**：按任务统计设备执行情况
4. **异常检测**：识别崩溃和执行不足的设备
5. **报告生成**：按指定格式生成Markdown报告

### 性能优化
- 并行获取多个任务详情（如需）
- 缓存已获取的任务数据
- 支持增量更新

### 错误处理
- 无当天任务：提示无数据
- API错误：记录并跳过，继续其他平台
- 数据解析错误：使用默认值，记录警告

## 更新日志
- 2026-04-02: 初始版本创建，支持四个平台的日常运行情况汇总
- 2026-04-02: 升级为按日统计，支持版本分组和异常检测

## 输出模板与固定提示词（保证稳定输出）

为保证每次调用返回一致且可解析的结果，建议使用以下稳定模板与固定提示词。可将下面的提示词作为日常触发短语，或在自动化脚本中以 `--prompt` 参数传入。

### 稳定化策略（要点）
- 明确输出格式：同时提供“可读Markdown模板”和“严格JSON模板”。
- 要求“仅输出数据、不得额外说明或上下文”。
- 为AI/技能提供严格的字段顺序与必需字段。
- 在脚本中增加 `--template v1 --strict` 开关，保证机器可重复解析。

### 推荐：Markdown 模板（`日报模板 V1`）

输出必须严格遵守下列结构和顺序（字段不可省略，空值请用 `-` 表示）：

```markdown
# {date}《星砂岛物语》稳定性汇总

## 一、PC（共{pc.total_devices}台设备，其中{pc.devices_over_4h}台执行超过4小时）
{for each version in pc.versions}
1. （版本：{version}）
  - {for each task in version.tasks}
    - [{task.task_name}]({task.task_url}) 任务执行汇总：共{task.total_devices}台设备，其中{task.devices_over_4h}台设备执行超过4小时，{if task.abnormal_devices_count>0}以下{task.abnormal_devices_count}台出现异常
      {for each abnormal in task.abnormal_devices}
      - {abnormal.device_name}({abnormal.ip}) 执行{abnormal.duration}，异常：{abnormal.reason} {abnormal.links}
      {end}
    {end}
{end}

## 二、Xbox（...）
## 三、PS5（...）
## 四、Switch（...）

---

**总体汇总**：平台覆盖 {summary.platforms_with_data} / {summary.total_platforms}，设备总计 {summary.overall_devices}，执行超过4小时 {summary.overall_devices_over_4h}
```

### 推荐：JSON 模板（机器解析，`JSON_SCHEMA_V1`）

必须输出单个JSON对象，字段和类型如下（示例化说明）：

```json
{
  "type": "star_autorun_daily",
  "date": "YYYY-MM-DD",
  "generated_at": "ISO8601 timestamp",
  "platforms": {
    "pc": {
      "platform": "PC",
      "pipeline_id": 946,
      "total_devices": 0,
      "devices_over_4h": 0,
      "versions": {
        "v1.0.0.xxx": [
          {
            "task_id": 0,
            "task_name": "string",
            "task_url": "string",
            "total_devices": 0,
            "devices_over_4h": 0,
            "abnormal_devices": [
              {
                "device_name": "string",
                "ip": "string",
                "duration_seconds": 0,
                "reason": "crash|early_exit|other",
                "evidence_links": ["url"]
              }
            ]
          }
        ]
      }
    }
  },
  "summary": {
    "total_platforms": 4,
    "platforms_with_data": 4,
    "overall_devices": 0,
    "overall_devices_over_4h": 0
  }
}
```

### 固定提示词（直接说一句即可触发稳定输出）

请复制下面任一固定短语作为你的触发词：

- 严格Markdown（人可读，便于文档粘贴）：

  请严格按“日报模板 V1”输出{date}的稳定性汇总，格式为Markdown，仅返回模板内容，不要任何解释或多余文本。

- 严格JSON（机器解析）：

  请严格按“JSON_SCHEMA_V1”输出{date}的稳定性汇总，返回单个JSON对象，仅返回JSON，不要任何解释或多余文本。

（说明：把 `{date}` 替换为 `今日` 或 `YYYY-MM-DD` 即可。）

### 在脚本中集成建议

- 新增CLI参数 `--template v1`（v1=上文模板）和 `--strict`（只输出模板内容）。
- 当 `--strict` 为真时，脚本应直接输出JSON或Markdown并以exit 0结束，不要打印调试信息。
- 在CI/定时任务中使用：

```bash
python scripts/star_autorun_v2.py --date 2026-04-02 --template v1 --strict --format markdown
python scripts/star_autorun_v2.py --date 2026-04-02 --template v1 --strict --format json
```

如果你愿意，我可以：
1. 将上面章节追加到当前 `SKILL.md`（已完成）。
2. 为 `scripts/star_autorun_v2.py` 添加 `--template`/`--strict` 支持并实现输出格式化器（需要我继续修改代码）。

### 示例模板 V1（精简版——你提供的示例）

下面是你希望得到的精简版 Markdown 输出示例，复制此样式作为 `日报模板 V1（精简）`：

```
2026.04.03《星砂岛物语》稳定性汇总
一、PC（共22台设备，其中20台执行超过4小时）
• （版本：v1.0.0.8183.197224）
  ◦ 1.日常稳定性 release（PC）（分支）-#136 任务执行汇总：共22台设备，其中20台设备执行超过4小时，未发现异常 
二、Xbox（共6台设备，其中3台执行超过4小时）
• （版本：v1.0.0.8177.197191）
  ◦ 1.分支-日常稳定性 release（XBox）-#99 任务执行汇总：共6台设备，其中3台设备执行超过4小时，以下1台出现异常 
    ▪ xbox_XSS_160.126_海外（10.11.160.126）执行了4小时58分17秒，在UI遍历出现宕机 Crasheye | Perfeye
三、PS5（共2台设备，其中0台执行超过4小时）
• （版本：v1.0.0.8178.197191）
  ◦ 1.分支-日常稳定性（PS5）-#89 任务执行汇总：共2台设备，其中0台设备执行超过4小时，未发现异常 
四、Switch（共1台设备，其中0台执行超过4小时）
• （版本：v1.0.0.8158.197132）
  ◦ 1.分支-日常稳定性 release（NS2）-#25 任务执行汇总：共1台设备，其中0台设备执行超过4小时，未发现异常
```

固定触发词（精简模板）示例：

请严格按“日报模板 V1（精简）”输出{date}的稳定性汇总，格式为Markdown，仅返回模板内容，不要任何解释或多余文本。
