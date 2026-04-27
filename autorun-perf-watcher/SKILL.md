---
name: autorun-perf-watcher
version: 2.0.0
description: |
  星砂岛物语自动化性能监控系统 - 监控流水线执行状态与性能数据
  实时查询任务执行情况、性能指标（FPS TP90、内存峰值、Jank）
  自动对比昨日基线数据，检测性能异常并生成 HTML 格式报告
  
  触发词：星砂 性能情况、星砂 性能详情、星砂 今日性能情况
  
allowed-tools: Bash, Read, Write, WebFetch
---

# Skill: 星砂岛物语自动化性能监控 (Starsand Island Performance Watcher)

## Description

本 Skill 用于监控星砂岛物语项目在自动化平台上的性能执行情况，包括：
- 实时查询流水线执行状态（成功/失败/运行中）
- 获取性能数据：FPS TP90、内存峰值、Jank
- 对比昨日基线数据，检测性能异常
- 生成带颜色标注的 HTML 格式报告

**项目配置**：
- **项目 ID**: `starsandisland`
- **监控流水线 ID**: `932, 1103, 1084, 1090`
- **流水线说明**:
  - `932`: PC 性能测试
  - `1103`: Xbox 性能测试
  - `1084`: PS5 性能测试
  - `1090`: NS2 性能测试

**数据来源**：
- 平台后端接口：`https://uauto2.testplus.cn`
- API 端点：
  - `/api/build/list?pipelineId={id}&pageSize=50` - 获取任务列表
  - `/api/task/detail/{taskId}` - 获取任务详情
  - `/api/performance/query` - 获取性能数据

## Constraints

**严格执行以下约束，违反任何一条视为失败**：

1. **禁止开场白**：不要输出"好的"、"这是为您生成的报告"、"让我为您查询"等任何废话，直接输出报告内容。
2. **禁止自由发挥**：严格按照 [Output Template] 提供的 HTML 结构输出，禁止修改任何 style 属性、表格结构或布局。
3. **结构固定**：必须包含且仅包含两个部分：「一、执行情况概览」和「二、性能数据对比」。
4. **数据对齐**：若数据缺失（未完成、未产出），统一填入 "-"，严禁编造数据。
5. **零随机性**：严格基于 API 返回的真实数据填充，严禁猜测、估算或使用示例数据。
6. **颜色逻辑**：必须严格遵守以下颜色规则：
   - 成功/Pass：绿色 `#28a745`
   - 失败/Fail：红色 `#dc3545`
   - FPS TP90 >= 60：绿色，< 60：红色
   - 内存峰值 <= 2048MB：绿色，> 2048MB：红色
   - Jank <= 10：绿色，> 10：红色
   - 性能衰退（当前值 < 基线值 * 0.9）：红色
7. **基线对比**：必须获取昨日（T-1）的性能数据作为基线，计算变化百分比。
8. **HTML 输出**：最终输出必须是纯 HTML 代码，不要用 Markdown 代码块包裹。

## Instructions

### 步骤 1：查询今日任务执行情况

对于每个流水线 ID（932, 1103, 1084, 1090），执行以下操作：

1. 调用 API：`GET /api/build/list?pipelineId={id}&pageSize=50&date={today}`
2. 统计以下数据：
   - 任务总数（Total Tasks）
   - 成功任务数（Success）
   - 失败任务数（Failed）
   - 运行中任务数（Running）
   - 案例总数（Total Cases）
   - 案例成功数（Cases Success）
   - 案例失败数（Cases Failed）
   - 设备总数（Total Devices）
   - 设备成功数（Devices Success）
   - 设备失败数（Devices Failed）
   - 最新任务 ID 和链接

3. 获取任务状态：
   - `SUCCESS` - 成功
   - `FAILED` - 失败
   - `RUNNING` - 运行中
   - `PENDING` - 等待中

### 步骤 2：获取性能数据

对于每个已完成的任务：

1. 调用 API：`GET /api/task/detail/{taskId}`
2. 提取性能指标：
   - **FPS TP90**：帧率 90 分位数
   - **内存峰值**：最大内存使用量（MB）
   - **Jank**：卡顿次数（次/10分钟）

3. 数据处理规则：
   - 若任务未完成：填入 "-"
   - 若性能数据未产出：填入 "-"
   - 若数据为 0 或 null：填入 "-"
   - 保留小数点后 1 位

### 步骤 3：获取昨日基线数据

1. 调用 API：`GET /api/build/list?pipelineId={id}&pageSize=50&date={yesterday}`
2. 获取昨日同一流水线的性能数据作为基线
3. 计算变化百分比：`((当前值 - 基线值) / 基线值) * 100`
4. 判断性能衰退：
   - FPS TP90 下降 > 10%：标红
   - 内存峰值增长 > 20%：标红
   - Jank 增长 > 50%：标红

### 步骤 4：生成 HTML 报告

严格按照 [Output Template] 填充数据，应用颜色逻辑。

## Output Template

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>星砂岛物语 - 性能监控报告</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 28px;
            font-weight: 600;
        }
        .header .date {
            margin-top: 10px;
            font-size: 14px;
            opacity: 0.9;
        }
        .content {
            padding: 30px;
        }
        .section {
            margin-bottom: 40px;
        }
        .section-title {
            font-size: 20px;
            font-weight: 600;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        th {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px;
            text-align: center;
            font-weight: 600;
            font-size: 13px;
        }
        td {
            padding: 12px;
            text-align: center;
            border-bottom: 1px solid #e0e0e0;
            font-size: 13px;
        }
        tr:hover {
            background-color: #f8f9fa;
        }
        .status-success {
            color: #28a745;
            font-weight: 600;
        }
        .status-failed {
            color: #dc3545;
            font-weight: 600;
        }
        .status-running {
            color: #ffc107;
            font-weight: 600;
        }
        .perf-good {
            background-color: #d4edda;
            color: #155724;
            font-weight: 600;
        }
        .perf-bad {
            background-color: #f8d7da;
            color: #721c24;
            font-weight: 600;
        }
        .baseline {
            background-color: #e7f3ff;
            font-weight: 600;
        }
        .link {
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
        }
        .link:hover {
            text-decoration: underline;
        }
        .summary {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-top: 15px;
        }
        .summary-item {
            display: inline-block;
            margin-right: 30px;
            font-size: 14px;
        }
        .summary-item strong {
            color: #667eea;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎮 星砂岛物语 - 性能监控报告</h1>
            <div class="date">统计时间：{{report_date}}</div>
        </div>
        
        <div class="content">
            <!-- 第一部分：执行情况概览 -->
            <div class="section">
                <div class="section-title">一、执行情况概览</div>
                <table>
                    <thead>
                        <tr>
                            <th>流水线 ID</th>
                            <th>流水线名称</th>
                            <th>任务状态</th>
                            <th>案例总数</th>
                            <th>案例成功</th>
                            <th>案例失败</th>
                            <th>设备总数</th>
                            <th>设备成功</th>
                            <th>设备失败</th>
                            <th>最新任务</th>
                        </tr>
                    </thead>
                    <tbody>
                        {{#each pipelines}}
                        <tr>
                            <td><strong>{{pipeline_id}}</strong></td>
                            <td>{{pipeline_name}}</td>
                            <td class="{{status_class}}">{{task_status}}</td>
                            <td>{{total_cases}}</td>
                            <td class="status-success">{{cases_success}}</td>
                            <td class="status-failed">{{cases_failed}}</td>
                            <td>{{total_devices}}</td>
                            <td class="status-success">{{devices_success}}</td>
                            <td class="status-failed">{{devices_failed}}</td>
                            <td><a href="{{task_link}}" class="link" target="_blank">查看详情</a></td>
                        </tr>
                        {{/each}}
                    </tbody>
                </table>
                
                <div class="summary">
                    <div class="summary-item"><strong>任务总数：</strong>{{total_tasks}}</div>
                    <div class="summary-item"><strong>成功：</strong><span class="status-success">{{tasks_success}}</span></div>
                    <div class="summary-item"><strong>失败：</strong><span class="status-failed">{{tasks_failed}}</span></div>
                    <div class="summary-item"><strong>运行中：</strong><span class="status-running">{{tasks_running}}</span></div>
                </div>
            </div>
            
            <!-- 第二部分：性能数据对比 -->
            <div class="section">
                <div class="section-title">二、性能数据对比（今日 vs 昨日基线）</div>
                
                {{#each pipelines}}
                <h3 style="color: #667eea; margin-top: 30px;">{{pipeline_name}} ({{pipeline_id}})</h3>
                <table>
                    <thead>
                        <tr>
                            <th rowspan="2">测试场景</th>
                            <th colspan="2">FPS TP90</th>
                            <th colspan="2">内存峰值 (MB)</th>
                            <th colspan="2">Jank (次/10min)</th>
                            <th rowspan="2">Perfeye</th>
                        </tr>
                        <tr>
                            <th>当前值</th>
                            <th>变化</th>
                            <th>当前值</th>
                            <th>变化</th>
                            <th>当前值</th>
                            <th>变化</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr class="baseline">
                            <td><strong>昨日基线</strong></td>
                            <td>{{baseline_fps}}</td>
                            <td>-</td>
                            <td>{{baseline_memory}}</td>
                            <td>-</td>
                            <td>{{baseline_jank}}</td>
                            <td>-</td>
                            <td>-</td>
                        </tr>
                        {{#each test_cases}}
                        <tr>
                            <td>{{case_name}}</td>
                            <td class="{{fps_class}}">{{fps_value}}</td>
                            <td class="{{fps_change_class}}">{{fps_change}}</td>
                            <td class="{{memory_class}}">{{memory_value}}</td>
                            <td class="{{memory_change_class}}">{{memory_change}}</td>
                            <td class="{{jank_class}}">{{jank_value}}</td>
                            <td class="{{jank_change_class}}">{{jank_change}}</td>
                            <td><a href="{{perfeye_link}}" class="link" target="_blank">查看</a></td>
                        </tr>
                        {{/each}}
                    </tbody>
                </table>
                {{/each}}
            </div>
        </div>
    </div>
</body>
</html>
```

## 占位符说明

### 全局占位符
- `{{report_date}}` - 报告生成日期，格式：YYYY-MM-DD HH:mm:ss

### 执行情况概览占位符
- `{{pipeline_id}}` - 流水线 ID（932/1103/1084/1090）
- `{{pipeline_name}}` - 流水线名称（PC 性能测试/Xbox 性能测试/PS5 性能测试/NS2 性能测试）
- `{{task_status}}` - 任务状态（成功/失败/运行中）
- `{{status_class}}` - 状态样式类（status-success/status-failed/status-running）
- `{{total_cases}}` - 案例总数
- `{{cases_success}}` - 案例成功数
- `{{cases_failed}}` - 案例失败数
- `{{total_devices}}` - 设备总数
- `{{devices_success}}` - 设备成功数
- `{{devices_failed}}` - 设备失败数
- `{{task_link}}` - 任务详情链接
- `{{total_tasks}}` - 任务总数
- `{{tasks_success}}` - 成功任务数
- `{{tasks_failed}}` - 失败任务数
- `{{tasks_running}}` - 运行中任务数

### 性能数据对比占位符
- `{{baseline_fps}}` - 昨日基线 FPS TP90
- `{{baseline_memory}}` - 昨日基线内存峰值
- `{{baseline_jank}}` - 昨日基线 Jank
- `{{case_name}}` - 测试场景名称
- `{{fps_value}}` - 当前 FPS TP90 值
- `{{fps_change}}` - FPS 变化百分比（+X% / -X%）
- `{{fps_class}}` - FPS 样式类（perf-good/perf-bad）
- `{{fps_change_class}}` - FPS 变化样式类
- `{{memory_value}}` - 当前内存峰值
- `{{memory_change}}` - 内存变化百分比
- `{{memory_class}}` - 内存样式类
- `{{memory_change_class}}` - 内存变化样式类
- `{{jank_value}}` - 当前 Jank 值
- `{{jank_change}}` - Jank 变化百分比
- `{{jank_class}}` - Jank 样式类
- `{{jank_change_class}}` - Jank 变化样式类
- `{{perfeye_link}}` - Perfeye 详情链接

## 颜色逻辑规则

### 执行状态颜色
- 成功（SUCCESS）：`status-success` → 绿色 #28a745
- 失败（FAILED）：`status-failed` → 红色 #dc3545
- 运行中（RUNNING）：`status-running` → 黄色 #ffc107

### 性能指标颜色
- **FPS TP90**：
  - >= 60：`perf-good` → 绿色背景
  - < 60：`perf-bad` → 红色背景
  
- **内存峰值**：
  - <= 2048MB：`perf-good` → 绿色背景
  - > 2048MB：`perf-bad` → 红色背景
  
- **Jank**：
  - <= 10：`perf-good` → 绿色背景
  - > 10：`perf-bad` → 红色背景

### 变化趋势颜色
- FPS TP90 下降 > 10%：`perf-bad` → 红色背景
- 内存峰值增长 > 20%：`perf-bad` → 红色背景
- Jank 增长 > 50%：`perf-bad` → 红色背景
- 其他情况：`perf-good` → 绿色背景

## 触发词

用户输入以下任一短语时，立即执行本 Skill：

- `星砂 性能情况`
- `星砂 性能详情`
- `星砂 性能状况`
- `星砂 今日性能情况`
- `星砂 今日性能详情`
- `星砂 今日性能状况`

## 执行流程

1. **识别触发词** → 匹配用户输入
2. **查询今日数据** → 调用 API 获取今日任务执行情况和性能数据
3. **查询昨日基线** → 调用 API 获取昨日性能数据作为基线
4. **数据处理** → 计算变化百分比，应用颜色逻辑
5. **生成报告** → 填充 HTML 模板，输出纯 HTML 代码
6. **直接输出** → 不要任何开场白，直接输出 HTML 报告

## 错误处理

- API 调用失败：在对应位置填入 "-"，并在报告底部添加错误提示
- 数据缺失：统一填入 "-"
- 昨日基线不存在：在基线行填入 "-"，变化百分比填入 "N/A"

## 注意事项

1. **严格遵守 Constraints**：任何违反约束的行为都是不可接受的
2. **数据真实性**：严禁编造数据，所有数据必须来自 API
3. **HTML 纯净输出**：不要用 Markdown 代码块包裹 HTML
4. **颜色逻辑准确**：必须严格按照规则应用颜色
5. **链接可点击**：确保所有链接格式正确，可以直接点击跳转
