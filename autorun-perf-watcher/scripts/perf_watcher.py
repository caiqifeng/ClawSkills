#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化任务性能监控脚本
监控流水线执行情况、失败设备、性能数据和异常检测
"""

import sys
import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import argparse
from collections import defaultdict
import statistics

# 解决 Windows 控制台中文乱码问题
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')


def get_pipeline_builds(pipeline_id: int, project_id: str, start_date: str, end_date: str) -> List[Dict]:
    """获取流水线的构建记录"""
    res_json = {
        "projectId": project_id,
        "order_by": "queueTime",
        "asc": False,
        "filters": {
            "pipelineId": pipeline_id,
            "startTime": start_date,
            "endTime": end_date,
        },
        "page": 1,
        "count": 100,
    }

    try:
        response = requests.post(
            f"https://automation-api.testplus.cn/api/tasks/list?projectId={project_id}",
            json=res_json,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 0 and "data" in data:
            builds = data["data"].get("list", [])
            return builds
        return []
    except Exception as e:
        print(f"获取流水线 {pipeline_id} 数据失败: {e}")
        return []


def get_task_detail(task_id: str, project_id: str) -> Dict:
    """获取任务详情"""
    try:
        response = requests.get(
            f"https://automation-api.testplus.cn/api/tasks/detail/{task_id}?projectId={project_id}",
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 0 and "data" in data:
            return data["data"]
        return {}
    except Exception as e:
        print(f"获取任务 {task_id} 详情失败: {e}")
        return {}


def calculate_pipeline_stats(builds: List[Dict], project_id: str) -> Dict:
    """计算流水线统计信息
    同时统计任务、Case、设备三个层级的成功失败
    """
    # 任务层级统计（原有统计）
    task_total = len(builds)
    task_success = sum(1 for b in builds if b.get("buildStatus") == "SUCCESS")
    task_failed = sum(1 for b in builds if b.get("buildStatus") == "FAILED")
    task_running = sum(1 for b in builds if b.get("buildStatus") == "RUNNING")

    # Case 和 设备 层级统计
    case_total = 0
    case_success = 0
    case_failed = 0
    device_total = 0
    device_success = 0
    device_failed = 0

    # 获取最新任务（按排队时间排序，最新的排在前面）
    latest_task_id = None
    if builds:
        # builds 已经按 queueTime 降序排序，第一个就是最新的
        latest_task_id = builds[0].get("buildId")

    for build in builds:
        task_id = build.get("buildId")
        task_detail = get_task_detail(task_id, project_id)
        if not task_detail:
            continue

        case_details = task_detail.get("caseDetails", [])
        for case_detail in case_details:
            # 统计所有已经出结果的 Case（不管任务是否还在运行）
            case_status = case_detail.get("status", "").lower()
            if not case_status:  # Case 还没开始运行，跳过统计
                continue

            case_total += 1
            if case_status == "success":
                case_success += 1
            else:
                case_failed += 1

            device_details = case_detail.get("deviceDetail", [])
            for device in device_details:
                # 统计所有已经出结果的设备（不管任务是否还在运行）
                device_status = device.get("status", "").lower()
                if not device_status:  # 设备还没开始运行，跳过统计
                    continue

                device_total += 1
                if device_status in ["success", "pass"]:
                    device_success += 1
                else:
                    device_failed += 1

    success_rate = (task_success / task_total * 100) if task_total > 0 else 0

    return {
        "task_total": task_total,
        "task_success": task_success,
        "task_failed": task_failed,
        "task_running": task_running,
        "success_rate": success_rate,
        "case_total": case_total,
        "case_success": case_success,
        "case_failed": case_failed,
        "device_total": device_total,
        "device_success": device_success,
        "device_failed": device_failed,
        "latest_task_id": latest_task_id
    }


def get_failed_devices(builds: List[Dict], project_id: str) -> List[Dict]:
    """获取失败设备列表"""
    failed_devices = []
    failed_builds = [b for b in builds if b.get("buildStatus") == "FAILED"]

    for build in failed_builds:
        task_id = build.get("buildId")
        task_detail = get_task_detail(task_id, project_id)

        if not task_detail:
            continue

        case_details = task_detail.get("caseDetails", [])
        for case_detail in case_details:
            device_details = case_detail.get("deviceDetail", [])
            for device in device_details:
                device_status = device.get("status", "").lower()
                # 检查设备状态是否为失败
                if device_status in ["error", "failed", "fail"]:
                    error_msg = device.get("errorMsg", "")
                    if not error_msg:
                        error_msg = device.get("errorMessage", "未知错误")

                    failed_devices.append({
                        "task_id": task_id,
                        "task_name": build.get("buildName", ""),
                        "device_id": device.get("deviceId", ""),
                        "device_name": device.get("deviceName", ""),
                        "device_ip": device.get("ip", ""),
                        "error_msg": error_msg,
                        "task_url": f"https://uauto2.testplus.cn/project/{project_id}/taskDetail?taskId={task_id}"
                    })

    return failed_devices


PIPELINE_NAMES = {
    932: "PC 性能测试",
    1103: "Xbox 性能测试",
    1084: "PS5 性能测试",
    1090: "NS2 性能测试"
}


def get_perfeye_performance(perfeye_id: str) -> Optional[Dict]:
    """获取 Perfeye 性能数据"""
    try:
        url = f"https://perfeye.testplus.cn/api/show/task/{perfeye_id}"
        headers = {
            "Authorization": "Bearer mj6cltF&!L#yWX8k",
            "Content-Type": "application/json"
        }
        response = requests.post(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "data" in data and "LabelInfo" in data["data"]:
            label_info = data["data"]["LabelInfo"]
            if "All" in label_info:
                all_stats = label_info["All"]

                fps_stats = all_stats.get("LabelFPS", {})
                tp90 = _parse_float(fps_stats.get("TP90"))

                mem_stats = all_stats.get("LabelMemory", {})
                peak_memory = _parse_float(mem_stats.get("PeakMemory(MB)"))
                if peak_memory is None:
                    peak_memory = _parse_float(mem_stats.get("PeakMemoryDeposit(MB)"))

                jank_per_10min = _parse_float(fps_stats.get("Jank(/10min)"))

                return {
                    "tp90": tp90,
                    "peak_memory_mb": peak_memory,
                    "jank_per_10min": jank_per_10min,
                    "perfeye_id": perfeye_id
                }
        return None
    except Exception as e:
        print(f"  [警告] 获取 Perfeye {perfeye_id} 数据失败: {e}")
        return None


def _parse_float(value) -> Optional[float]:
    """解析浮点数"""
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def extract_performance_data(builds: List[Dict], project_id: str, max_samples: int = 5) -> List[Dict]:
    """从任务中提取性能数据（采样策略：获取最新任务的所有案例）"""
    perf_data_list = []

    # 优先从成功的任务中采样，如果没有成功任务则从所有任务中采样
    success_builds = [b for b in builds if b.get("buildStatus") == "SUCCESS"]
    sample_builds = success_builds[:max_samples] if success_builds else builds[:max_samples]

    for build in sample_builds:
        task_id = build.get("buildId")
        print(f"    - 采样任务 {task_id}...")
        task_detail = get_task_detail(task_id, project_id)

        if not task_detail:
            continue

        case_details = task_detail.get("caseDetails", [])
        # 遍历所有案例，不再限制数量
        for case_detail in case_details:
            device_details = case_detail.get("deviceDetail", [])
            # 每个case取第一个设备的性能数据
            for device in device_details[:1]:
                report_data = device.get("reportData", {})
                perfeye_id = report_data.get("perfeye")

                if perfeye_id:
                    perf_data = get_perfeye_performance(perfeye_id)
                    if perf_data:
                        perf_data["task_id"] = task_id
                        perf_data["device_name"] = device.get("deviceName", "")
                        perf_data["case_name"] = case_detail.get("caseName", "")
                        perf_data_list.append(perf_data)

    return perf_data_list


def calculate_baseline_stats(perf_data_list: List[Dict]) -> Dict:
    """计算性能基线统计"""
    if not perf_data_list:
        return {}

    tp90_values = [d["tp90"] for d in perf_data_list if d.get("tp90") is not None]
    memory_values = [d["peak_memory_mb"] for d in perf_data_list if d.get("peak_memory_mb") is not None]
    jank_values = [d["jank_per_10min"] for d in perf_data_list if d.get("jank_per_10min") is not None]

    baseline = {}
    if tp90_values:
        baseline["tp90_avg"] = statistics.mean(tp90_values)
        baseline["tp90_max"] = max(tp90_values)
        baseline["tp90_min"] = min(tp90_values)

    if memory_values:
        baseline["memory_avg"] = statistics.mean(memory_values)
        baseline["memory_max"] = max(memory_values)
        baseline["memory_min"] = min(memory_values)

    if jank_values:
        baseline["jank_avg"] = statistics.mean(jank_values)
        baseline["jank_max"] = max(jank_values)
        baseline["jank_min"] = min(jank_values)

    return baseline


def calculate_daily_case_stats(today_perf: List[Dict]) -> Dict:
    """按 case 名称分组统计当天性能数据
    返回: {case_name: {tp90_avg, memory_avg, jank_avg, count}}
    """
    from collections import defaultdict

    case_groups = defaultdict(list)
    for perf in today_perf:
        case_name = perf.get("case_name", "未知场景")
        case_groups[case_name].append(perf)

    case_stats = {}
    for case_name, perfs in case_groups.items():
        tp90_values = [p["tp90"] for p in perfs if p.get("tp90") is not None]
        memory_values = [p["peak_memory_mb"] for p in perfs if p.get("peak_memory_mb") is not None]
        jank_values = [p["jank_per_10min"] for p in perfs if p.get("jank_per_10min") is not None]

        stats = {"case_name": case_name, "count": len(perfs)}
        if tp90_values:
            stats["tp90_avg"] = statistics.mean(tp90_values)
        if memory_values:
            stats["memory_avg"] = statistics.mean(memory_values)
        if jank_values:
            stats["jank_avg"] = statistics.mean(jank_values)

        case_stats[case_name] = stats

    return case_stats


def detect_performance_anomaly(today_perf: List[Dict], baseline: Dict) -> List[Dict]:
    """检测性能异常"""
    anomalies = []

    if not baseline or not today_perf:
        return anomalies

    for perf in today_perf:
        anomaly_info = {
            "device_name": perf.get("device_name"),
            "case_name": perf.get("case_name"),
            "perfeye_id": perf.get("perfeye_id"),
            "issues": []
        }

        # 检查 TP90 异常
        if perf.get("tp90") and baseline.get("tp90_avg"):
            tp90_change = (perf["tp90"] - baseline["tp90_avg"]) / baseline["tp90_avg"] * 100
            if tp90_change < -10:  # TP90 下降超过 10%
                anomaly_info["issues"].append(f"TP90 下降 {abs(tp90_change):.1f}% (当前: {perf['tp90']:.1f}, 基线: {baseline['tp90_avg']:.1f})")

        # 检查内存异常
        if perf.get("peak_memory_mb") and baseline.get("memory_avg"):
            memory_change = (perf["peak_memory_mb"] - baseline["memory_avg"]) / baseline["memory_avg"] * 100
            if memory_change > 20:  # 内存增长超过 20%
                anomaly_info["issues"].append(f"内存峰值增长 {memory_change:.1f}% (当前: {perf['peak_memory_mb']:.1f}MB, 基线: {baseline['memory_avg']:.1f}MB)")

        # 检查 Jank 异常
        if perf.get("jank_per_10min") and baseline.get("jank_avg"):
            jank_change = (perf["jank_per_10min"] - baseline["jank_avg"]) / baseline["jank_avg"] * 100
            if jank_change > 30:  # Jank 增加超过 30%
                anomaly_info["issues"].append(f"Jank 增加 {jank_change:.1f}% (当前: {perf['jank_per_10min']:.1f}, 基线: {baseline['jank_avg']:.1f})")

        if anomaly_info["issues"]:
            anomalies.append(anomaly_info)

    return anomalies


def load_template(template_name: str) -> str:
    """加载模板文件"""
    template_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "templates",
        template_name
    )
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()

def generate_stats_report(pipeline_stats: Dict, project_id: str, target_date: str) -> str:
    """生成执行情况报告"""
    total_task = sum(stats['task_total'] for stats in pipeline_stats.values())
    success_task = sum(stats['task_success'] for stats in pipeline_stats.values())
    failed_task = sum(stats['task_failed'] for stats in pipeline_stats.values())
    running_task = sum(stats['task_running'] for stats in pipeline_stats.values())
    total_case = sum(stats['case_total'] for stats in pipeline_stats.values())
    success_case = sum(stats['case_success'] for stats in pipeline_stats.values())
    failed_case = sum(stats['case_failed'] for stats in pipeline_stats.values())
    total_device = sum(stats['device_total'] for stats in pipeline_stats.values())
    success_device = sum(stats['device_success'] for stats in pipeline_stats.values())
    failed_device = sum(stats['device_failed'] for stats in pipeline_stats.values())

    # 生成流水线表格行
    pipeline_rows = []
    for pipeline_id, stats in sorted(pipeline_stats.items()):
        pipeline_name = PIPELINE_NAMES.get(pipeline_id, f"流水线 {pipeline_id}")
        if stats['latest_task_id']:
            task_url = f"https://uauto2.testplus.cn/project/{project_id}/taskDetail?taskId={stats['latest_task_id']}"
            latest_link = f"[查看]({task_url})"
        else:
            latest_link = "-"
        pipeline_rows.append(
            f"| {pipeline_id} | {pipeline_name} | **{stats['case_total']}** | **{stats['case_success']}** | **{stats['case_failed']}** | **{stats['device_total']}** | **{stats['device_success']}** | **{stats['device_failed']}** | {latest_link} |"
        )
    pipeline_rows_str = "\n".join(pipeline_rows)

    # 渲染主模板
    template = load_template("report.md")
    return template.format(
        title="星砂岛物语 - 流水线执行情况报告",
        target_date=target_date,
        pipeline_rows=pipeline_rows_str,
        total_task=total_task,
        success_task=success_task,
        failed_task=failed_task,
        running_task=running_task,
        total_case=total_case,
        success_case=success_case,
        failed_case=failed_case,
        total_device=total_device,
        success_device=success_device,
        failed_device=failed_device,
        performance_sections="{performance_sections}"
    )


def generate_failed_devices_report(failed_devices_by_pipeline: Dict, project_id: str) -> str:
    """生成失败设备报告"""
    report = "\n## 二、失败设备汇总\n\n"

    if not any(failed_devices_by_pipeline.values()):
        report += "✅ **近期无失败设备**\n"
        return report

    for pipeline_id, devices in sorted(failed_devices_by_pipeline.items()):
        if not devices:
            continue

        pipeline_name = PIPELINE_NAMES.get(pipeline_id, f"流水线 {pipeline_id}")
        report += f"### {pipeline_name} ({pipeline_id})\n\n"
        report += f"共 **{len(devices)}** 台设备失败：\n\n"

        for device in devices:
            report += f"- **{device['device_name']}**"
            if device['device_ip']:
                report += f" ({device['device_ip']})"
            report += f": {device['error_msg']} - [查看任务]({device['task_url']})\n"

        report += "\n"

    return report


def get_failed_cases_summary(builds: List[Dict]) -> Dict[str, List[str]]:
    """获取失败案例汇总"""
    failed_cases = {}

    for build in builds:
        case_result = build.get("caseResult", {})
        if isinstance(case_result, dict) and "FAILED" in case_result:
            task_id = build.get("buildId")
            task_name = build.get("buildName", "")
            failed_list = case_result["FAILED"]

            if failed_list:
                failed_cases[task_id] = {
                    "task_name": task_name,
                    "failed_cases": failed_list,
                    "task_url": f"https://uauto2.testplus.cn/project/starsandisland/taskDetail?taskId={task_id}"
                }

    return failed_cases


def generate_failed_cases_report(failed_cases_by_pipeline: Dict) -> str:
    """生成失败案例报告"""
    report = "\n## 三、失败案例汇总\n\n"

    has_failed = False
    for pipeline_id, failed_cases in sorted(failed_cases_by_pipeline.items()):
        if not failed_cases:
            continue

        has_failed = True
        pipeline_name = PIPELINE_NAMES.get(pipeline_id, f"流水线 {pipeline_id}")
        report += f"### {pipeline_name} ({pipeline_id})\n\n"

        for task_id, info in failed_cases.items():
            report += f"#### [{info['task_name']}]({info['task_url']})\n\n"
            report += f"失败案例 **{len(info['failed_cases'])}** 个：\n\n"
            for case_name in info['failed_cases']:
                report += f"- {case_name}\n"
            report += "\n"

    if not has_failed:
        report += "✅ **近期无失败案例**\n"

    return report


def extract_device_config(device_name: str) -> str:
    """从设备名称中提取配置信息（用于分组）"""
    # 识别常见显卡配置
    if "3080" in device_name or "RTX 3080" in device_name:
        return "RTX 3080 (超高) - 4K"
    elif "3060" in device_name or "RTX 3060" in device_name:
        return "RTX 3060 (高) - 2K"
    elif "5080" in device_name or "RTX 5080" in device_name:
        return "RTX 5080 (超高) - 4K"
    elif "5070" in device_name or "RTX 5070" in device_name:
        return "RTX 5070 (高) - 2K"
    elif "4080" in device_name or "RTX 4080" in device_name:
        return "RTX 4080 (超高) - 4K"
    elif "4060" in device_name or "RTX 4060" in device_name:
        return "RTX 4060 (高) - 2K"
    elif "XSX" in device_name or "Xbox" in device_name:
        return "Xbox Series X"
    elif "PS5" in device_name:
        return "PS5"
    elif "NS2" in device_name or "Switch" in device_name:
        return "Nintendo Switch 2"
    else:
        # 返回第一部分作为分组
        parts = device_name.split("_")
        if len(parts) >= 3:
            return "_".join(parts[1:3])
        return device_name

def format_change(change: float, threshold: float, is_bad_when_up: bool) -> str:
    """格式化变化百分比，用加粗标记异常
    change: 变化百分比
    threshold: 异常阈值
    is_bad_when_up: True表示增长超过阈值异常（内存、Jank），False表示下降超过阈值异常（FPS）
    返回纯Markdown文本
    """
    abs_change = abs(change)
    if is_bad_when_up:
        # 内存、Jank：增长异常
        is_anomaly = change > threshold
    else:
        # FPS：下降异常
        is_anomaly = change < -threshold

    if is_anomaly:
        return f"**{abs_change:.0f}**⚠️"
    else:
        return f"{abs_change:.0f}"

def generate_anomaly_section(anomalies: List[Dict]) -> str:
    """生成异常检测部分"""
    template = load_template("anomaly_list.md")
    if not anomalies:
        return template.split("⚠️")[0].strip() + "✅ **未检测到性能异常**"

    anomaly_items = []
    for anomaly in anomalies:
        item = f"- **{anomaly['device_name']}** - {anomaly['case_name']}\n"
        for issue in anomaly['issues']:
            item += f"  - {issue}\n"
        item += f"  - [查看 Perfeye](https://perfeye.testplus.cn/case/{anomaly['perfeye_id']}/report)"
        anomaly_items.append(item)

    return template.format(
        count=len(anomalies),
        anomaly_items="\n\n".join(anomaly_items)
    ).split("✅")[0].strip()

def generate_performance_report(baseline_by_pipeline: Dict, anomalies_by_pipeline: Dict, today_perf_by_pipeline: Dict) -> str:
    """生成性能对比报告
    包含:
    1. 当天成功案例按场景分组表格，表格内直接显示当天/基线对比
    2. 性能异常检测结果
    使用独立模板文件渲染
    """
    pipeline_sections = []
    has_data = False

    for pipeline_id, baseline in sorted(baseline_by_pipeline.items()):
        if not baseline:
            continue

        has_data = True
        pipeline_name = PIPELINE_NAMES.get(pipeline_id, f"流水线 {pipeline_id}")
        today_perf = today_perf_by_pipeline.get(pipeline_id, [])

        config_tables_content = ""
        if today_perf:
            # 按设备配置分组
            from collections import defaultdict
            config_groups = defaultdict(list)
            for perf in today_perf:
                config = extract_device_config(perf.get("device_name", ""))
                config_groups[config].append(perf)

            # 每个配置生成一个表格
            config_template = load_template("config_table.md")
            for config_name, perfs in sorted(config_groups.items()):
                # 按 case 分组计算平均
                case_stats = defaultdict(list)
                for perf in perfs:
                    case_name = perf.get("case_name", "未知场景")
                    case_stats[case_name].append(perf)

                # 计算每个 case 的平均值
                case_avg = {}
                for case_name, perf_list in case_stats.items():
                    tp90_values = [p["tp90"] for p in perf_list if p.get("tp90") is not None]
                    memory_values = [p["peak_memory_mb"] for p in perf_list if p.get("peak_memory_mb") is not None]
                    jank_values = [p["jank_per_10min"] for p in perf_list if p.get("jank_per_10min") is not None]
                    avg = {}
                    if tp90_values:
                        avg["tp90_avg"] = statistics.mean(tp90_values)
                    if memory_values:
                        avg["memory_avg"] = statistics.mean(memory_values)
                    if jank_values:
                        avg["jank_avg"] = statistics.mean(jank_values)
                    avg["count"] = len(perf_list)
                    case_avg[case_name] = avg

                baseline_tp90_avg = baseline.get("tp90_avg")
                baseline_memory_avg = baseline.get("memory_avg")
                baseline_jank_avg = baseline.get("jank_avg")

                # 获取第一个设备信息用于填充表头
                first_perf = perfs[0]
                device_full_name = first_perf.get("device_name", "unknown")
                # 提取简化设备名
                import re
                short_name_match = re.search(r"i7.*RTX\s*\d+.*|i5.*RTX\s*\d+.*|R\d+.*RTX\s*\d+.*", device_full_name)
                if short_name_match:
                    device_name = short_name_match.group(0)
                else:
                    parts = device_full_name.split("_")
                    if len(parts) >= 3:
                        device_name = "_".join(parts[2:4])
                    else:
                        device_name = device_full_name
                # 画质（默认中）
                quality = "中"

                # 基线数值
                base_tp90 = baseline_tp90_avg if baseline_tp90_avg is not None else 0
                base_memory = baseline_memory_avg if baseline_memory_avg is not None else 0
                base_jank = baseline_jank_avg if baseline_jank_avg is not None else 0

                # 生成 case 行
                case_rows = []
                for case_name, stats in sorted(case_avg.items()):
                    # FPS TP90 + 变化百分比
                    if "tp90_avg" in stats and baseline_tp90_avg:
                        tp90_val = f"{stats['tp90_avg']:.1f}"
                        change = (stats["tp90_avg"] - baseline_tp90_avg) / baseline_tp90_avg * 100
                        change_str = format_change(change, 10, is_bad_when_up=False)
                    elif "tp90_avg" in stats:
                        tp90_val = f"{stats['tp90_avg']:.1f}"
                        change_str = "-"
                    else:
                        tp90_val = "-"
                        change_str = "-"

                    # 内存峰值 + 变化百分比
                    if "memory_avg" in stats and baseline_memory_avg:
                        memory_val = f"{stats['memory_avg']:.0f}"
                        change = (stats["memory_avg"] - baseline_memory_avg) / baseline_memory_avg * 100
                        change_mem_str = format_change(change, 20, is_bad_when_up=True)
                    elif "memory_avg" in stats:
                        memory_val = f"{stats['memory_avg']:.0f}"
                        change_mem_str = "-"
                    else:
                        memory_val = "-"
                        change_mem_str = "-"

                    # Jank
                    if "jank_avg" in stats and baseline_jank_avg:
                        jank_val = f"{stats['jank_avg']:.1f}"
                    elif "jank_avg" in stats:
                        jank_val = f"{stats['jank_avg']:.1f}"
                    else:
                        jank_val = "-"

                    # 获取第一个性能数据的 perfeye id 生成链接
                    first_perf = perfs[0]
                    perfeye_id = first_perf.get("perfeye_id")
                    if perfeye_id:
                        perfeye_link = f"[查看](https://perfeye.testplus.cn/case/{perfeye_id}/report)"
                    else:
                        perfeye_link = "-"

                    case_rows.append(f"| {case_name} | {tp90_val} | {change_str} | {memory_val} | {change_mem_str} | {jank_val} | - | {perfeye_link} |")

                # 渲染配置表格 - 模板中已经包含表头，替换所有占位符
                case_rows_str = "\n".join(case_rows)
                config_table = config_template.format(
                    config_name=config_name,
                    device_name=device_name,
                    quality=quality,
                    tp90_baseline=f"{base_tp90:.1f}" if base_tp90 else "FPS",
                    memory_baseline=f"{base_memory:.0f}" if base_memory else "内存峰值",
                    jank_baseline=f"{base_jank:.0f}" if base_jank else "Jank",
                    case_rows=case_rows_str
                )

                config_tables_content += config_table

        # 生成异常部分
        anomalies = anomalies_by_pipeline.get(pipeline_id, [])
        anomaly_section = generate_anomaly_section(anomalies)

        # 渲染流水线区块
        pipeline_template = load_template("pipeline_section.md")
        pipeline_section = pipeline_template.format(
            pipeline_name=pipeline_name,
            pipeline_id=pipeline_id,
            config_tables=config_tables_content,
            anomaly_section=anomaly_section
        )
        pipeline_sections.append(pipeline_section)

    if not has_data:
        return "⚠️ **暂无性能数据**\n"

    return "\n".join(pipeline_sections)


def generate_html_report(pipeline_stats: Dict, baseline_by_pipeline: Dict, today_perf_by_pipeline: Dict, all_cases_by_pipeline: Dict, project_id: str, target_date: str) -> str:
    """生成 HTML 格式报告（符合 SKILL.md 模板）
    all_cases_by_pipeline: 每个流水线的所有案例列表（包括没有性能数据的）
    """
    from datetime import datetime

    # 计算总计数据
    total_tasks = sum(stats['task_total'] for stats in pipeline_stats.values())
    tasks_success = sum(stats['task_success'] for stats in pipeline_stats.values())
    tasks_failed = sum(stats['task_failed'] for stats in pipeline_stats.values())
    tasks_running = sum(stats['task_running'] for stats in pipeline_stats.values())

    # 生成流水线行（第一部分：执行情况概览）
    pipeline_rows_html = ""
    for pipeline_id, stats in sorted(pipeline_stats.items()):
        pipeline_name = PIPELINE_NAMES.get(pipeline_id, f"流水线 {pipeline_id}")

        # 判断任务状态
        if stats['task_running'] > 0:
            task_status = "运行中"
            status_class = "status-running"
        elif stats['task_failed'] > 0:
            task_status = "失败"
            status_class = "status-failed"
        elif stats['task_success'] > 0:
            task_status = "成功"
            status_class = "status-success"
        else:
            task_status = "等待中"
            status_class = "status-running"

        task_link = f"https://uauto2.testplus.cn/project/{project_id}/taskDetail?taskId={stats['latest_task_id']}" if stats['latest_task_id'] else "#"

        pipeline_rows_html += f"""
                        <tr>
                            <td><strong>{pipeline_id}</strong></td>
                            <td>{pipeline_name}</td>
                            <td class="{status_class}">{task_status}</td>
                            <td>{stats['case_total']}</td>
                            <td class="status-success">{stats['case_success']}</td>
                            <td class="status-failed">{stats['case_failed']}</td>
                            <td>{stats['device_total']}</td>
                            <td class="status-success">{stats['device_success']}</td>
                            <td class="status-failed">{stats['device_failed']}</td>
                            <td><a href="{task_link}" class="link" target="_blank">查看详情</a></td>
                        </tr>"""

    # 生成性能数据对比部分（第二部分）
    performance_sections_html = ""
    for pipeline_id, baseline in sorted(baseline_by_pipeline.items()):
        if not baseline:
            continue

        pipeline_name = PIPELINE_NAMES.get(pipeline_id, f"流水线 {pipeline_id}")
        today_perf = today_perf_by_pipeline.get(pipeline_id, [])
        all_cases = all_cases_by_pipeline.get(pipeline_id, [])

        # 获取基线数据
        baseline_fps = f"{baseline.get('tp90_avg', 0):.1f}" if baseline.get('tp90_avg') else "-"
        baseline_memory = f"{baseline.get('memory_avg', 0):.0f}" if baseline.get('memory_avg') else "-"
        baseline_jank = f"{baseline.get('jank_avg', 0):.1f}" if baseline.get('jank_avg') else "-"

        # 将性能数据按案例名称组织成字典
        perf_by_case = {}
        for perf in today_perf:
            case_name = perf.get("case_name", "")
            if case_name not in perf_by_case:
                perf_by_case[case_name] = []
            perf_by_case[case_name].append(perf)

        # 生成测试场景行（遍历所有案例）
        test_cases_html = ""
        for case_name in all_cases:
            perf_list = perf_by_case.get(case_name, [])

            if perf_list:
                # 有性能数据，计算平均值和范围
                tp90_values = [p["tp90"] for p in perf_list if p.get("tp90") is not None]
                memory_values = [p["peak_memory_mb"] for p in perf_list if p.get("peak_memory_mb") is not None]
                jank_values = [p["jank_per_10min"] for p in perf_list if p.get("jank_per_10min") is not None]
                device_count = len(perf_list)

                # FPS TP90
                if tp90_values:
                    fps_value = statistics.mean(tp90_values)
                    fps_min = min(tp90_values)
                    fps_max = max(tp90_values)
                    fps_value_str = f"{fps_value:.1f}"
                    fps_range_str = f"{fps_min:.1f}~{fps_max:.1f}" if len(tp90_values) > 1 else "-"
                    fps_class = "perf-good" if fps_value >= 60 else "perf-bad"

                    if baseline.get('tp90_avg'):
                        fps_change = (fps_value - baseline['tp90_avg']) / baseline['tp90_avg'] * 100
                        fps_change_str = f"{fps_change:+.1f}%"
                        fps_change_class = "perf-bad" if fps_change < -10 else "perf-good"
                    else:
                        fps_change_str = "-"
                        fps_change_class = ""
                else:
                    fps_value_str = "-"
                    fps_range_str = "-"
                    fps_class = ""
                    fps_change_str = "-"
                    fps_change_class = ""

                # 内存峰值
                if memory_values:
                    memory_value = statistics.mean(memory_values)
                    memory_min = min(memory_values)
                    memory_max = max(memory_values)
                    memory_value_str = f"{memory_value:.0f}"
                    memory_range_str = f"{memory_min:.0f}~{memory_max:.0f}" if len(memory_values) > 1 else "-"
                    memory_class = "perf-good" if memory_value <= 2048 else "perf-bad"

                    if baseline.get('memory_avg'):
                        memory_change = (memory_value - baseline['memory_avg']) / baseline['memory_avg'] * 100
                        memory_change_str = f"{memory_change:+.1f}%"
                        memory_change_class = "perf-bad" if memory_change > 20 else "perf-good"
                    else:
                        memory_change_str = "-"
                        memory_change_class = ""
                else:
                    memory_value_str = "-"
                    memory_range_str = "-"
                    memory_class = ""
                    memory_change_str = "-"
                    memory_change_class = ""

                # Jank
                if jank_values:
                    jank_value = statistics.mean(jank_values)
                    jank_min = min(jank_values)
                    jank_max = max(jank_values)
                    jank_value_str = f"{jank_value:.1f}"
                    jank_range_str = f"{jank_min:.1f}~{jank_max:.1f}" if len(jank_values) > 1 else "-"
                    jank_class = "perf-good" if jank_value <= 10 else "perf-bad"

                    if baseline.get('jank_avg'):
                        jank_change = (jank_value - baseline['jank_avg']) / baseline['jank_avg'] * 100
                        jank_change_str = f"{jank_change:+.1f}%"
                        jank_change_class = "perf-bad" if jank_change > 50 else "perf-good"
                    else:
                        jank_change_str = "-"
                        jank_change_class = ""
                else:
                    jank_value_str = "-"
                    jank_range_str = "-"
                    jank_class = ""
                    jank_change_str = "-"
                    jank_change_class = ""

                # Perfeye 链接
                perfeye_id = perf_list[0].get("perfeye_id") if perf_list else None
                perfeye_link = f'<a href="https://perfeye.testplus.cn/case/{perfeye_id}/report" class="link" target="_blank">查看</a>' if perfeye_id else "-"

                device_count_str = f"{device_count}台"
            else:
                # 没有性能数据，全部显示 "-"
                fps_value_str = "-"
                fps_range_str = "-"
                fps_class = ""
                fps_change_str = "-"
                fps_change_class = ""
                memory_value_str = "-"
                memory_range_str = "-"
                memory_class = ""
                memory_change_str = "-"
                memory_change_class = ""
                jank_value_str = "-"
                jank_range_str = "-"
                jank_class = ""
                jank_change_str = "-"
                jank_change_class = ""
                perfeye_link = "-"
                device_count_str = "-"

            test_cases_html += f"""
                        <tr>
                            <td>{case_name}</td>
                            <td>{device_count_str}</td>
                            <td class="{fps_class}">{fps_value_str}</td>
                            <td style="font-size: 11px; color: #666;">{fps_range_str}</td>
                            <td class="{fps_change_class}">{fps_change_str}</td>
                            <td class="{memory_class}">{memory_value_str}</td>
                            <td style="font-size: 11px; color: #666;">{memory_range_str}</td>
                            <td class="{memory_change_class}">{memory_change_str}</td>
                            <td class="{jank_class}">{jank_value_str}</td>
                            <td style="font-size: 11px; color: #666;">{jank_range_str}</td>
                            <td class="{jank_change_class}">{jank_change_str}</td>
                            <td>{perfeye_link}</td>
                        </tr>"""

        performance_sections_html += f"""
                <h3 style="color: #667eea; margin-top: 30px;">{pipeline_name} ({pipeline_id})</h3>
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
                            <td>{baseline_fps}</td>
                            <td>-</td>
                            <td>{baseline_memory}</td>
                            <td>-</td>
                            <td>{baseline_jank}</td>
                            <td>-</td>
                            <td>-</td>
                        </tr>
{test_cases_html}
                    </tbody>
                </table>"""

    # 生成完整 HTML
    report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>星砂岛物语 - 性能监控报告</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 600;
        }}
        .header .date {{
            margin-top: 10px;
            font-size: 14px;
            opacity: 0.9;
        }}
        .content {{
            padding: 30px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section-title {{
            font-size: 20px;
            font-weight: 600;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}
        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px;
            text-align: center;
            font-weight: 600;
            font-size: 13px;
        }}
        td {{
            padding: 12px;
            text-align: center;
            border-bottom: 1px solid #e0e0e0;
            font-size: 13px;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}
        .status-success {{
            color: #28a745;
            font-weight: 600;
        }}
        .status-failed {{
            color: #dc3545;
            font-weight: 600;
        }}
        .status-running {{
            color: #ffc107;
            font-weight: 600;
        }}
        .perf-good {{
            background-color: #d4edda;
            color: #155724;
            font-weight: 600;
        }}
        .perf-bad {{
            background-color: #f8d7da;
            color: #721c24;
            font-weight: 600;
        }}
        .baseline {{
            background-color: #e7f3ff;
            font-weight: 600;
        }}
        .link {{
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
        }}
        .link:hover {{
            text-decoration: underline;
        }}
        .summary {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-top: 15px;
        }}
        .summary-item {{
            display: inline-block;
            margin-right: 30px;
            font-size: 14px;
        }}
        .summary-item strong {{
            color: #667eea;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎮 星砂岛物语 - 性能监控报告</h1>
            <div class="date">统计时间：{report_date}</div>
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
{pipeline_rows_html}
                    </tbody>
                </table>

                <div class="summary">
                    <div class="summary-item"><strong>任务总数：</strong>{total_tasks}</div>
                    <div class="summary-item"><strong>成功：</strong><span class="status-success">{tasks_success}</span></div>
                    <div class="summary-item"><strong>失败：</strong><span class="status-failed">{tasks_failed}</span></div>
                    <div class="summary-item"><strong>运行中：</strong><span class="status-running">{tasks_running}</span></div>
                </div>
            </div>

            <!-- 第二部分：性能数据对比 -->
            <div class="section">
                <div class="section-title">二、性能数据对比（今日 vs 昨日基线）</div>
{performance_sections_html}
            </div>
        </div>
    </div>
</body>
</html>"""

    return html


def get_all_case_names(builds: List[Dict], project_id: str) -> List[str]:
    """获取任务中的所有案例名称列表"""
    all_cases = []
    seen_cases = set()

    # 从最新的任务中获取案例列表
    for build in builds[:1]:  # 只取最新的任务
        task_id = build.get("buildId")
        task_detail = get_task_detail(task_id, project_id)

        if not task_detail:
            continue

        case_details = task_detail.get("caseDetails", [])
        for case_detail in case_details:
            case_name = case_detail.get("caseName", "")
            if case_name and case_name not in seen_cases:
                all_cases.append(case_name)
                seen_cases.add(case_name)

    return all_cases


def main():
    parser = argparse.ArgumentParser(description="自动化任务性能监控脚本")
    parser.add_argument("--project", type=str, default="starsandisland", help="项目 ID")
    parser.add_argument("--pipelines", type=str, required=True, help="流水线 ID 列表，逗号分隔")
    parser.add_argument("--mode", type=str, default="stats", choices=["stats", "anomaly", "full"], help="执行模式")
    parser.add_argument("--date", type=str, default="", help="统计日期 YYYY-MM-DD，默认为当天")
    parser.add_argument("--output", type=str, default="pipeline_stats.md", help="输出文件名")
    parser.add_argument("--format", type=str, default="markdown", choices=["markdown", "html"], help="输出格式")

    args = parser.parse_args()

    project_id = args.project
    pipeline_ids = [int(x.strip()) for x in args.pipelines.split(",")]
    mode = args.mode
    output_file = args.output

    # 确定统计日期
    if args.date:
        target_date = args.date
    else:
        target_date = datetime.now().strftime("%Y-%m-%d")

    # 当天的时间范围
    today_start = f"{target_date} 00:00:00"
    today_end = f"{target_date} 23:59:59"

    # 近一周的时间范围（用于性能基线）
    week_ago = (datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")
    week_start = f"{week_ago} 00:00:00"
    week_end = f"{target_date} 23:59:59"

    print(f"开始查询 {project_id} 项目的流水线执行情况...")
    print(f"流水线 ID: {pipeline_ids}")
    print(f"统计日期: {target_date}")
    print(f"性能基线: {week_ago} ~ {target_date}\n")

    pipeline_stats = {}
    failed_devices_by_pipeline = {}
    failed_cases_by_pipeline = {}
    baseline_by_pipeline = {}
    anomalies_by_pipeline = {}
    today_perf_by_pipeline = {}  # 当天成功案例的性能数据，按case分组
    all_cases_by_pipeline = {}  # 每个流水线的所有案例列表

    for pipeline_id in pipeline_ids:
        print(f"正在查询流水线 {pipeline_id}...")

        # 获取当天的构建记录（用于统计）
        today_builds = get_pipeline_builds(pipeline_id, project_id, today_start, today_end)
        stats = calculate_pipeline_stats(today_builds, project_id)
        pipeline_stats[pipeline_id] = stats

        # 获取所有案例列表
        all_cases = get_all_case_names(today_builds, project_id)
        all_cases_by_pipeline[pipeline_id] = all_cases

        failed_devices = get_failed_devices(today_builds, project_id)
        failed_devices_by_pipeline[pipeline_id] = failed_devices

        failed_cases = get_failed_cases_summary(today_builds)
        failed_cases_by_pipeline[pipeline_id] = failed_cases

        print(f"  - 当天任务: {stats['task_total']} 次，成功 {stats['task_success']}，失败 {stats['task_failed']}")
        print(f"  - Case统计: {stats['case_total']} 个，成功 {stats['case_success']}，失败 {stats['case_failed']}")
        print(f"  - 设备统计: {stats['device_total']} 台，成功 {stats['device_success']}，失败 {stats['device_failed']}")

        # 获取近一周的构建记录（用于性能基线）
        print(f"  - 正在提取性能数据...")
        week_builds = get_pipeline_builds(pipeline_id, project_id, week_start, week_end)

        # 提取近一周的性能数据作为基线
        baseline_perf_data = extract_performance_data(week_builds, project_id)
        baseline = calculate_baseline_stats(baseline_perf_data)
        baseline_by_pipeline[pipeline_id] = baseline

        # 提取当天的性能数据
        today_perf_data = extract_performance_data(today_builds, project_id)

        # 保存当天性能数据，用于按case分组分析
        today_perf_by_pipeline[pipeline_id] = today_perf_data

        # 检测性能异常
        anomalies = detect_performance_anomaly(today_perf_data, baseline)
        anomalies_by_pipeline[pipeline_id] = anomalies

        if baseline:
            print(f"  - 性能基线: TP90={baseline.get('tp90_avg', 0):.1f}, 内存={baseline.get('memory_avg', 0):.1f}MB, Jank={baseline.get('jank_avg', 0):.1f}")
        if anomalies:
            print(f"  - [警告] 检测到 {len(anomalies)} 个性能异常")
        print()

    # 生成报告
    if args.format == "html":
        # 生成 HTML 格式报告
        report = generate_html_report(pipeline_stats, baseline_by_pipeline, today_perf_by_pipeline, all_cases_by_pipeline, project_id, target_date)
    else:
        # 生成 Markdown 格式报告
        report_template = generate_stats_report(pipeline_stats, project_id, target_date)
        # 跳过失败设备汇总和失败案例汇总
        # report += generate_failed_devices_report(failed_devices_by_pipeline, project_id)
        # report += generate_failed_cases_report(failed_cases_by_pipeline)
        performance_content = generate_performance_report(baseline_by_pipeline, anomalies_by_pipeline, today_perf_by_pipeline)
        report = report_template.format(performance_sections=performance_content)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n报告已生成: {output_file}")


if __name__ == "__main__":
    main()


