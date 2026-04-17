# Skill: 自动化平台操作助手 (Automation Platform Controller)

## Description
本 Skill 用于连接内部自动化平台（API 地址：https://uauto2.testplus.cn），实现任务监控、故障设备重试、以及根据项目名称快速拉起测试流水线的功能。

## Capabilities
- 实时查询自动化任务的状态（Pending, Running, Failed, Success）。
- 针对失败任务，能够识别特定失败设备并执行重新运行（Re-run）指令。
- 支持语义化触发测试任务，通过项目名称和测试类型自动匹配 Pipeline ID。

## Prerequisites
- 需要拥有自动化平台的 API Token。
- OpenClaw 环境需能访问平台后端接口。

## Instructions
1. **处理任务重试：**
   - 当收到 URL 或 TaskID 时，首先调用 `GET /task/detail` 获取设备列表。
   - 筛选出状态为 `error` 或 `failed` 的设备。
   - 调用 `POST /task/retry` 接口，传入具体的设备 ID。
   - 重试后，持续监控状态直至变为 `running` 并告知用户。

2. **触发新任务：**
   - 当用户提到“执行 [项目名] 的 [测试类型]”时：
     - 调用 `GET /pipelines/search?name={project_name}`。
     - 如果找到唯一的 Pipeline，直接调用 `POST /pipelines/{id}/run`。
     - 如果有多个（如：稳定性、兼容性），询问用户具体执行哪一个。

3. **异常处理：**
   - 若平台返回 500 错误，告知用户：“平台接口响应异常，请检查网络或平台服务状态。”
   - 若重试 3 次依然失败，停止操作并提取错误日志摘要。

## Tool Definitions (Python/API)
### get_task_info
- **Input**: `task_url` (string) 或 `task_id` (string)
- **Output**: JSON 格式的任务摘要，包含设备状态列表。

### manage_device_retry
- **Input**: `task_id`, `device_ids` (list)
- **Description**: 对指定设备触发重试操作。

### trigger_pipeline
- **Input**: `pipeline_id`, `params` (dict)
- **Description**: 启动指定的流水线。

## User Conversation Examples
- "帮我看看这个任务 https://uauto2.testplus.cn/project/starsandisland/taskDetail?taskId=142612 里的失败设备，帮我重跑一下。"
- "帮我跑一下 JX3 项目的稳定性测试。"
- "星砂 使用最新版本 执行 PC稳定性 任务"
- "触发人：AI-AUTO-RUN"

## 自动触发新任务规则

### 获取包体规则
当需要自动触发测试任务时，按以下规则选择安装包：
1. **版本选择**：默认选择**编译时间最新**的版本；如果用户指定版本号，则选择指定版本号
2. **编译类型**：默认选择 `release` 类型
3. **平台选择**：根据任务平台筛选包，PC -> `PC/` 路径，Xbox -> `XBOX/` 或 `xboxx/` 路径

### 执行流程
1. 调用 `GET /api/package/list` 获取项目所有包
2. 根据上述规则筛选出符合要求的包
3. 调用 `GET /api/pipeline/detail/{pipelineId}` 获取流水线详情
4. 更新流水线的 `appVersion` 字段，填入新选择的包信息（`packageId` + `downloadUrl`）
5. 调用 `POST /api/build/execute` 执行流水线

### 默认配置示例
| 项目 | 项目ID | 任务类型 | pipelineId |
|------|--------|----------|------------|
| 星砂物语 | `starsandisland` | PC 稳定性 | `946` |
| 星砂物语 | `starsandisland` | xbox 稳定性 | `953` |
| 机甲 | `mecha` | PC DX11稳定性 | `333` |
| 机甲 | `mecha` | PC DX12稳定性 | `429` |