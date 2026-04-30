# coding=utf-8
import argparse
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape

import requests


API_URL = "http://10.11.10.112:8686/api/statistic"

PROJECT_APPKEYS = {
    "jxsj4": "jxsj4",
    "JXSJ4": "jxsj4",
    "剑世4": "jxsj4",
    "starsandisland": "starsandisland",
    "星砂": "starsandisland",
    "星砂岛": "starsandisland",
}

LEVEL_ALIASES = {
    "Exception": "Exception",
    "exception": "Exception",
    "异常": "Exception",
    "Error": "Error",
    "error": "Error",
    "错误": "Error",
}


def resolve_appkey(project):
    return PROJECT_APPKEYS.get(project, project)


def resolve_levels(levels):
    if not levels:
        return ["Exception", "Error"]

    if isinstance(levels, str):
        levels = re.split(r"[,，\s]+", levels.strip())

    result = []
    for level in levels:
        if level:
            result.append(LEVEL_ALIASES.get(level, level))
    return result or ["Exception", "Error"]


def resolve_time_range(time_range, today=None):
    today = today or datetime.today()
    if not time_range or time_range in ("今天", "today"):
        return today.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    if time_range in ("昨天", "yesterday"):
        yesterday = today - timedelta(days=1)
        return yesterday.strftime("%Y-%m-%d"), yesterday.strftime("%Y-%m-%d")
    if time_range in ("最近一周", "近一周", "最近7天", "近7天", "last7days"):
        return (today - timedelta(days=7)).strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

    parts = re.split(r"[,，~至\s]+", time_range.strip())
    parts = [part for part in parts if part]
    if len(parts) >= 2:
        return parts[0], parts[1]
    return time_range, time_range


def get_log_list(
    project="jxsj4",
    fromtime=None,
    totime=None,
    time_range=None,
    levels=None,
    log_string="",
    offset=0,
    size=30000,
    limit=30000,
    timeout=120,
):
    if fromtime is None or totime is None:
        fromtime, totime = resolve_time_range(time_range)

    payload = {
        "appkey": resolve_appkey(project),
        "from": offset,
        "size": size,
        "limit": limit,
        "fromtime": fromtime,
        "totime": totime,
        "merge_type": 0,
        "compare_with_project_version": "gte",
        "skip": 0,
        "levels": resolve_levels(levels),
        "log_string": log_string or "",
    }

    response = requests.post(API_URL, json=payload, timeout=timeout)
    response.raise_for_status()
    result = response.json()
    if result.get("ret") not in (None, 0):
        raise RuntimeError("query failed: {}".format(result))
    payload["_project_name"] = project
    return payload, result.get("data", [])


def print_summary(payload, data, max_rows):
    total_count = sum(int(item.get("count", 0)) for item in data)
    levels = " / ".join(payload.get("levels", []))
    time_range = "{} 至 {}".format(payload.get("fromtime", ""), payload.get("totime", ""))

    print("### 查询概要")
    print()
    print("```")
    print("项目：{}".format(payload.get("appkey", "")))
    print("时间范围：{}".format(time_range))
    print("查询时间：{}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    print("错误类型：{}".format(levels))
    print("```")
    print()
    print("### 查询结果表格")
    print()
    print("| 编号 | 日志类型 | 日志详情 | 数量 |")
    print("|:---:|:-------:|---------|:----:|")

    for index, item in enumerate(data[:max_rows], 1):
        detail = format_log_detail(item.get("vector", ""))
        print(
            "| {index} | {level} | {detail} | {count} |".format(
                index=index,
                level=escape_table_text(item.get("level", "")),
                detail=detail,
                count=item.get("count", 0),
            )
        )

    print("| **合计** | | | **{}** |".format(total_count))


def escape_table_text(value):
    return str(value).replace("|", "\\|")


def format_log_detail(vector, max_length=200):
    detail = " ".join(str(vector).replace("\r", "").replace("\n", " ").split())
    if len(detail) > max_length:
        detail = detail[:max_length] + "..."
    return escape_table_text(detail)


def format_excel_detail(vector):
    return " ".join(str(vector).replace("\r", "").replace("\n", " ").split())


def make_excel_path(payload):
    levels = "-".join(payload.get("levels", [])) or "all"
    filename = "log_list_{appkey}_{fromtime}_{totime}_{levels}_{time}.xlsx".format(
        appkey=payload.get("appkey", "project"),
        fromtime=payload.get("fromtime", ""),
        totime=payload.get("totime", ""),
        levels=levels,
        time=datetime.now().strftime("%Y%m%d_%H%M%S"),
    )
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    return output_dir / filename


def excel_col_name(index):
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def excel_cell_xml(row_index, col_index, value):
    ref = "{}{}".format(excel_col_name(col_index), row_index)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return '<c r="{ref}"><v>{value}</v></c>'.format(ref=ref, value=value)
    text = escape(str(value), {'"': "&quot;"})
    return '<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>'.format(ref=ref, text=text)


def worksheet_xml(rows):
    xml_rows = []
    for row_index, row in enumerate(rows, 1):
        cells = [excel_cell_xml(row_index, col_index, value) for col_index, value in enumerate(row, 1)]
        xml_rows.append('<row r="{row_index}">{cells}</row>'.format(row_index=row_index, cells="".join(cells)))

    dimension = "A1:D{}".format(max(len(rows), 1))
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="{dimension}"/>
  <cols>
    <col min="1" max="1" width="10" customWidth="1"/>
    <col min="2" max="2" width="14" customWidth="1"/>
    <col min="3" max="3" width="120" customWidth="1"/>
    <col min="4" max="4" width="12" customWidth="1"/>
  </cols>
  <sheetData>{rows}</sheetData>
</worksheet>""".format(dimension=dimension, rows="".join(xml_rows))


def build_excel_rows(payload, data):
    levels = " / ".join(payload.get("levels", []))
    time_range = "{} 至 {}".format(payload.get("fromtime", ""), payload.get("totime", ""))
    total_count = sum(int(item.get("count", 0)) for item in data)
    rows = [
        ["项目", payload.get("appkey", ""), "", ""],
        ["时间范围", time_range, "", ""],
        ["查询时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "", ""],
        ["错误类型", levels, "", ""],
        ["", "", "", ""],
        ["编号", "日志类型", "日志详情", "数量"],
    ]

    for index, item in enumerate(data, 1):
        rows.append(
            [
                index,
                item.get("level", ""),
                format_excel_detail(item.get("vector", "")),
                int(item.get("count", 0)),
            ]
        )
    rows.append(["合计", "", "", total_count])
    return rows


def save_excel(payload, data, output_path=None):
    output_path = Path(output_path) if output_path else make_excel_path(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = build_excel_rows(payload, data)

    files = {
        "[Content_Types].xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
        "_rels/.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        "xl/workbook.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="log_list" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>""",
        "xl/_rels/workbook.xml.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
        "xl/worksheets/sheet1.xml": worksheet_xml(rows),
    }

    with ZipFile(output_path, "w", ZIP_DEFLATED) as xlsx:
        for file_name, content in files.items():
            xlsx.writestr(file_name, content)

    return output_path


def html_text(value):
    return escape(str(value), {'"': "&quot;", "'": "&#39;"})


def make_log_href(payload, item):
    logmd5 = item.get("logmd5")
    if not logmd5:
        return ""

    return (
        "https://logs.console.testplus.cn/project/{}/logs/logDetails?"
        "logmd5={}&fromtime={}T00:00:00+08:00&totime={}T23:59:59+08:00&"
    ).format(
        payload.get("appkey", ""),
        logmd5,
        payload.get("fromtime", ""),
        payload.get("totime", ""),
    )


def make_log_link(payload, item):
    href = make_log_href(payload, item)
    if not href:
        return "-"
    return '<a href="{}" target="_blank" rel="noopener">查看</a>'.format(html_text(href))


def ordered_log_levels(data):
    existing = []
    for item in data:
        level = item.get("level", "")
        if level and level not in existing:
            existing.append(level)

    ordered = [level for level in ("Exception", "Error", "Warn") if level in existing]
    ordered.extend(level for level in existing if level not in ordered)
    return ordered


def sanitize_filename_part(value):
    return re.sub(r'[\\/:*?"<>|]+', "_", str(value)).strip() or "project"


def make_html_path(payload, output_dir=None):
    project_name = payload.get("_project_name") or payload.get("appkey", "project")
    if payload.get("fromtime") == payload.get("totime"):
        date_text = payload.get("fromtime", "")
    else:
        date_text = "{}_{}".format(payload.get("fromtime", ""), payload.get("totime", ""))
    filename = "{}_{}-{}.html".format(
        sanitize_filename_part(project_name),
        sanitize_filename_part(date_text),
        datetime.now().strftime("%H-%M-%S"),
    )
    output_dir = Path(output_dir) if output_dir else Path("outputs")
    return output_dir / filename


def resolve_html_path(payload, output_path=None):
    if not output_path:
        return make_html_path(payload)

    path = Path(output_path)
    if path.suffix:
        return path.with_suffix(".html")
    return make_html_path(payload, path)


def save_html(payload, data, output_path=None):
    output_path = resolve_html_path(payload, output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    levels = " / ".join(payload.get("levels", []))
    time_range = "{} 至 {}".format(payload.get("fromtime", ""), payload.get("totime", ""))
    query_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_count = sum(int(item.get("count", 0)) for item in data)

    sections = []
    for level in ordered_log_levels(data):
        level_items = [item for item in data if item.get("level") == level]
        level_total = sum(int(item.get("count", 0)) for item in level_items)
        rows = []
        for item in level_items:
            rows.append(
                """      <tr>
        <td class="count">{count}</td>
        <td class="level">{level}</td>
        <td class="detail"><pre>{detail}</pre></td>
        <td class="link">{link}</td>
      </tr>""".format(
                    count=int(item.get("count", 0)),
                    level=html_text(level),
                    detail=html_text(item.get("vector", "")),
                    link=make_log_link(payload, item),
                )
            )

        sections.append(
            """  <h2>{level}</h2>
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
{rows}
    </tbody>
    <tfoot>
      <tr>
        <td class="count">{level_total}</td>
        <td></td>
        <td>合计</td>
        <td></td>
      </tr>
    </tfoot>
  </table>""".format(
                level=html_text(level),
                rows="\n".join(rows),
                level_total=level_total,
            )
        )

    html = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{project} 日志详情 {date}</title>
  <style>
    body {{
      margin: 24px;
      color: #202124;
      font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
      background: #ffffff;
    }}
    h1 {{
      margin: 0 0 16px;
      font-size: 22px;
      font-weight: 700;
    }}
    .summary {{
      margin-bottom: 18px;
      line-height: 1.8;
      font-size: 14px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      font-size: 13px;
    }}
    th, td {{
      border: 1px solid #d0d7de;
      padding: 8px 10px;
      vertical-align: top;
    }}
    th {{
      background: #f6f8fa;
      text-align: center;
      font-weight: 700;
    }}
    .level {{
      width: 120px;
      text-align: center;
    }}
    .link {{
      width: 96px;
      text-align: center;
    }}
    .count {{
      width: 96px;
      text-align: right;
      font-variant-numeric: tabular-nums;
    }}
    .detail pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-family: Consolas, "Microsoft YaHei", monospace;
      line-height: 1.45;
    }}
    .actions {{
      margin: 8px 0 18px;
    }}
    .export-button {{
      padding: 6px 12px;
      border: 1px solid #d0d7de;
      background: #f6f8fa;
      color: #202124;
      cursor: pointer;
      font-size: 13px;
    }}
    .export-button:hover {{
      background: #eef2f6;
    }}
    tfoot td {{
      background: #f6f8fa;
      font-weight: 700;
    }}
  </style>
</head>
<body>
  <h1>{project} 日志详情</h1>
  <div class="summary">
    <div><strong>项目：</strong>{appkey}</div>
    <div><strong>时间范围：</strong>{time_range}</div>
    <div><strong>查询时间：</strong>{query_time}</div>
    <div><strong>错误类型：</strong>{levels}</div>
    <div><strong>合计数量：</strong>{total_count}</div>
  </div>
  <div class="actions">
    <button class="export-button" type="button" onclick="exportExcel()">导出Excel文档</button>
  </div>
{sections}
  <script>
    function xmlEscape(value) {{
      return String(value == null ? "" : value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&apos;");
    }}

    function findTable(levelName) {{
      var headings = document.querySelectorAll("h2");
      for (var i = 0; i < headings.length; i++) {{
        if (headings[i].textContent.trim() === levelName) {{
          return headings[i].nextElementSibling;
        }}
      }}
      return null;
    }}

    function tableRows(levelName) {{
      var rows = [["数量", "日志类型", "日志详情", "日志超链接"]];
      var table = findTable(levelName);
      if (!table) {{
        return rows;
      }}

      var bodyRows = table.querySelectorAll("tbody tr");
      for (var i = 0; i < bodyRows.length; i++) {{
        var cells = bodyRows[i].querySelectorAll("td");
        var link = cells[3].querySelector("a");
        rows.push([
          cells[0].textContent.trim(),
          cells[1].textContent.trim(),
          cells[2].innerText.trim(),
          link ? link.href : cells[3].textContent.trim()
        ]);
      }}

      var total = table.querySelector("tfoot .count");
      rows.push([total ? total.textContent.trim() : "", "", "合计", ""]);
      return rows;
    }}

    function worksheetXml(sheetName) {{
      var rows = tableRows(sheetName);
      var rowXml = rows.map(function(row) {{
        var cellXml = row.map(function(cell) {{
          return "<Cell><Data ss:Type=\\"String\\">" + xmlEscape(cell) + "</Data></Cell>";
        }}).join("");
        return "<Row>" + cellXml + "</Row>";
      }}).join("");
      return "<Worksheet ss:Name=\\"" + xmlEscape(sheetName) + "\\"><Table>" + rowXml + "</Table></Worksheet>";
    }}

    function exportExcel() {{
      var workbook =
        "<?xml version=\\"1.0\\" encoding=\\"UTF-8\\"?>" +
        "<?mso-application progid=\\"Excel.Sheet\\"?>" +
        "<Workbook xmlns=\\"urn:schemas-microsoft-com:office:spreadsheet\\" " +
        "xmlns:o=\\"urn:schemas-microsoft-com:office:office\\" " +
        "xmlns:x=\\"urn:schemas-microsoft-com:office:excel\\" " +
        "xmlns:ss=\\"urn:schemas-microsoft-com:office:spreadsheet\\">" +
        worksheetXml("Exception") +
        worksheetXml("Error") +
        "</Workbook>";

      var blob = new Blob([workbook], {{ type: "application/vnd.ms-excel;charset=utf-8;" }});
      var link = document.createElement("a");
      var safeTitle = document.title.replace(/[\\\\/:*?\\"<>|]+/g, "_");
      link.href = URL.createObjectURL(blob);
      link.download = safeTitle + ".xls";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(link.href);
    }}
  </script>
</body>
</html>
""".format(
        project=html_text(output_path.stem.rsplit("_", 1)[0]),
        date=html_text(payload.get("fromtime", "")),
        appkey=html_text(payload.get("appkey", "")),
        time_range=html_text(time_range),
        query_time=html_text(query_time),
        levels=html_text(levels),
        sections="\n\n".join(sections),
        total_count=total_count,
    )

    output_path.write_text(html, encoding="utf-8")
    return output_path


def parse_args():
    parser = argparse.ArgumentParser(description="Query TestPlus log statistic list.")
    parser.add_argument("--project", default="jxsj4", help="project name or appkey, e.g. jxsj4, 剑世4, 星砂")
    parser.add_argument("--fromtime", help="start date, e.g. 2026-04-28")
    parser.add_argument("--totime", help="end date, e.g. 2026-04-30")
    parser.add_argument("--time-range", help="今天 / 昨天 / 最近一周 / 2026-04-28 2026-04-30")
    parser.add_argument("--levels", default="", help="异常,错误 or Exception,Error")
    parser.add_argument("--log-string", default="", help="keyword in log vector")
    parser.add_argument("--size", type=int, default=30000, help="request size")
    parser.add_argument("--limit", type=int, default=30000, help="backend query limit")
    parser.add_argument("--timeout", type=int, default=120, help="request timeout seconds")
    parser.add_argument("--max-rows", type=int, default=20, help="summary rows to print")
    parser.add_argument("--excel-path", help="xlsx output path")
    parser.add_argument("--no-excel", action="store_true", help="do not save xlsx")
    parser.add_argument("--html-path", help="html output path or directory")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    payload, data = get_log_list(
        project=args.project,
        fromtime=args.fromtime,
        totime=args.totime,
        time_range=args.time_range,
        levels=args.levels,
        log_string=args.log_string,
        size=args.size,
        limit=args.limit,
        timeout=args.timeout,
    )
    print_summary(payload, data, args.max_rows)
    if not args.no_excel:
        excel_path = save_excel(payload, data, args.excel_path)
        print()
        print("Excel附件：{}".format(excel_path))
    if args.html_path:
        html_path = save_html(payload, data, args.html_path)
        print()
        print("HTML文件：{}".format(html_path))
