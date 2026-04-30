---
name: kglogger-query
description: Use when the user wants to query log system details — queries like "星砂 今天日志详情", "剑世4 昨天 Exception 日志", "查看 XX 项目近7天日志". Triggers include requests for log details, error queries, exception lookups by project name, time range (today/yesterday/last7days/last30days), and error type (Exception/Error/Warn).
---

# KGLogger 日志查询系统

## Description

用于查询日志系统的日志详情。支持按**项目名**、**时间范围**和**错误类型**进行查询，调用 `scripts/KGLoggerQuery.py` 中的 `get_log_data()` 接口。

### 时间范围映射

| 用户关键词 | fromtime | totime |
|-----------|----------|--------|
| 今天 | `{今天 00:00}` | `{今天 23:59}` |
| 昨天 | `{昨天 00:00}` | `{昨天 23:59}` |
| 近7天 | `{7天前 00:00}` | `{今天 23:59}` |
| 近30天 | `{30天前 00:00}` | `{今天 23:59}` |

### 错误类型映射

| 用户关键词 | log_string |
|-----------|-----------|
| Exception | `Exception` |
| Error | `Error` |
| Warn | `Warn` |

### 项目-AppKey 映射

> **说明**：首次使用前需确认或补充项目映射关系。默认映射如下：

| 项目名 | appkey |
|-------|--------|
| 星砂 / 星砂岛物语 | `starsandisland` |
| 剑世4 / JXSJ4 | `jxsj4` |
| {{PROJECT_NAME_3}} | {{APPKEY_3}} |

## Constraints

1. **禁止任何开场白、客套话或与查询结果无关的说明文字**
2. **必须严格按照 Output Template 输出结果**，不得修改格式或添加额外内容
3. **禁止自由发挥**：所有数据必须来自 `get_log_data()` 的真实返回结果
4. 如果用户未指定时间范围，**默认查询"今天"**
5. 如果用户未指定错误类型，**查询全部三种类型**（Exception / Error / Warn 各一次）
6. 当查询结果为空时，输出 `本次查询无匹配日志`，不要自作聪明编造数据
7. 如果用户提到的项目不在映射表中，告知用户并提供可配置的映射说明
8. **严禁编造数据** — 若接口调用失败，如实报告错误信息

## Instructions

### Step 1: 解析用户意图

从用户输入中提取三个要素：**项目名**、**时间范围**、**错误类型**。

**项目名提取**：匹配用户提到的项目名称，对照「项目-AppKey 映射」表获取 `appkey`。支持模糊匹配和别名。

**时间范围计算**：根据用户关键词计算具体的 `fromtime`、`totime`（格式：`YYYY-MM-DD`）。

**错误类型提取**：根据用户关键词确定 `log_string`。若未指定，标记为"全量查询"。

### Step 2: 调用接口查询

使用 `scripts/KGLoggerQuery.py` 的 `get_log_data()` 函数。

**单类型查询**：

```python
from scripts.KGLoggerQuery import get_log_data

data = get_log_data(
    appkey="{{appkey}}",
    log_string="{{log_string}}",
    fromtime="{{fromtime}}",
    totime="{{totime}}"
)
```

**全量查询**（未指定错误类型时）：分别以 `Exception`、`Error`、`Warn` 为 `log_string` 调用三次，合并结果后按日志类型分表输出。

**响应数据结构**：
```json
[
    {"vector": "日志详情文本...", "count": 123},
    {"vector": "另一条日志详情...", "count": 45}
]
```

### Step 3: 格式化输出

按照 Output Template 渲染 HTML 结果。

当结果中同时包含多种日志类型时，必须按日志类型分开输出多个表格，顺序固定为：

1. `Exception`
2. `Error`
3. `Warn`

如果某个日志类型没有结果，则不输出该类型表格。

每一行必须包含“日志超链接”列，链接到日志控制台详情页面。链接必须使用接口返回的 `logmd5` 拼接，格式如下：

```html
<a href="https://logs.console.testplus.cn/project/{{APPKEY}}/logs/logDetails?logmd5={{LOG_MD5}}&fromtime={{FROMTIME}}T00:00:00+08:00&totime={{TOTIME}}T23:59:59+08:00&" target="_blank">查看</a>
```

如果接口返回中没有 `logmd5` 字段，则输出空链接文本 `-`。

### Step 4: 数量汇总

在表格底部汇总总数量。

## Output Template

输出必须是完整 HTML 文档，文件名后缀必须使用 `.html`，保存后可直接在浏览器打开。

HTML 结果文件名格式必须为：

```text
{{PROJECT_NAME}}_{{YYYY-MM-DD}}-{{HH}}-{{MM}}-{{SS}}.html
```

示例：

```text
星砂_2026-04-30-15-50-30.html
```

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{{PROJECT_NAME}} 日志详情 {{DATE}}</title>
  <style>
    body { margin: 24px; font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif; color: #202124; }
    h1 { margin: 0 0 16px; font-size: 22px; }
    h2 { margin: 28px 0 10px; font-size: 18px; }
    .summary { margin-bottom: 18px; line-height: 1.8; font-size: 14px; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 13px; }
    th, td { border: 1px solid #d0d7de; padding: 8px 10px; vertical-align: top; }
    th { background: #f6f8fa; text-align: center; }
    .level { width: 120px; text-align: center; }
    .link { width: 96px; text-align: center; }
    .count { width: 96px; text-align: right; font-variant-numeric: tabular-nums; }
    .detail pre { margin: 0; white-space: pre-wrap; word-break: break-word; font-family: Consolas, "Microsoft YaHei", monospace; }
    .actions { margin: 8px 0 18px; }
    .export-button { padding: 6px 12px; border: 1px solid #d0d7de; background: #f6f8fa; cursor: pointer; }
    tfoot td { background: #f6f8fa; font-weight: 700; }
  </style>
</head>
<body>
  <h1>{{PROJECT_NAME}} 日志详情</h1>
  <div class="summary">
    <div><strong>项目：</strong>{{PROJECT_NAME}}</div>
    <div><strong>AppKey：</strong>{{APPKEY}}</div>
    <div><strong>时间范围：</strong>{{TIME_RANGE_DESC}}</div>
    <div><strong>查询时间：</strong>{{QUERY_TIME}}</div>
    <div><strong>错误类型：</strong>{{ERROR_TYPES}}</div>
    <div><strong>合计数量：</strong>{{TOTAL_COUNT}}</div>
  </div>
  <div class="actions">
    <button class="export-button" type="button" onclick="exportExcel()">导出Excel文档</button>
  </div>

  <h2>Exception</h2>
  <table>
    <thead>
      <tr>
        <th class="count">数量</th>
        <th class="level">日志类型</th>
        <th>日志详情</th>
        <th class="link">日志超链接</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td class="count">{{COUNT}}</td>
        <td class="level">Exception</td>
        <td class="detail"><pre>{{LOG_DETAIL}}</pre></td>
        <td class="link">{{LOG_LINK}}</td>
      </tr>
    </tbody>
    <tfoot>
      <tr>
        <td class="count">{{EXCEPTION_TOTAL_COUNT}}</td>
        <td></td>
        <td>合计</td>
        <td></td>
      </tr>
    </tfoot>
  </table>

  <h2>Error</h2>
  <table>
    <thead>
      <tr>
        <th class="count">数量</th>
        <th class="level">日志类型</th>
        <th>日志详情</th>
        <th class="link">日志超链接</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td class="count">{{COUNT}}</td>
        <td class="level">Error</td>
        <td class="detail"><pre>{{LOG_DETAIL}}</pre></td>
        <td class="link">{{LOG_LINK}}</td>
      </tr>
    </tbody>
    <tfoot>
      <tr>
        <td class="count">{{ERROR_TOTAL_COUNT}}</td>
        <td></td>
        <td>合计</td>
        <td></td>
      </tr>
    </tfoot>
  </table>
  <script>
    function exportExcel() {
      // 导出当前页面中的 Exception / Error 表格为一个 Excel 文件，Sheet 名分别为 Exception 和 Error。
    }
  </script>
</body>
</html>
```

> **字段说明**：
> - **数量**：`count` 字段值
> - **日志类型**：`Exception` / `Error` / `Warn`（全量查询时每行标注对应类型）
> - **日志详情**：`vector` 字段内容，HTML 中使用 `<pre>` 保留换行和堆栈格式
> - **日志超链接**：使用 `logmd5` 拼接日志详情页 URL，文字固定为 `查看`
> - **合计**：当前日志类型表格内所有行数量之和
> - **导出Excel文档**：按钮显示在“合计数量”下方，导出的 Excel 必须包含两个 Sheet：`Exception` 和 `Error`

### 空结果

```
项目：{{PROJECT_NAME}}
时间范围：{{TIME_RANGE_DESC}}
查询时间：{{QUERY_TIME}}
错误类型：{{ERROR_TYPE}}

本次查询无匹配日志
```

### 错误响应

```
查询失败：{{ERROR_MESSAGE}}
```
