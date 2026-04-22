#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化任务性能监控脚本
监控流水线执行情况、失败设备、性能数据和异常检测
"""

import sys
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
    """从任务中提取性能数据（采样策略：只从成功任务中采样，限制数量）"""
    perf_data_list = []
    sampled_count = 0

    # 优先从成功的任务中采样
    success_builds = [b for b in builds if b.get("buildStatus") == "SUCCESS"]
    sample_builds = success_builds[:max_samples] if success_builds else builds[:max_samples]

    for build in sample_builds:
        task_id = build.get("buildId")
        print(f"    - 采样任务 {task_id}...")
        task_detail = get_task_detail(task_id, project_id)

        if not task_detail:
            continue

        case_details = task_detail.get("caseDetails", [])
        for case_detail in case_details[:3]:  # 每个任务最多采样3个case
            device_details = case_detail.get("deviceDetail", [])
            for device in device_details[:2]:  # 每个case最多采样2个设备
                report_data = device.get("reportData", {})
                perfeye_id = report_data.get("perfeye")

                if perfeye_id:
                    perf_data = get_perfeye_performance(perfeye_id)
                    if perf_data:
                        perf_data["task_id"] = task_id
                        perf_data["device_name"] = device.get("deviceName", "")
                        perf_data["case_name"] = case_detail.get("caseName", "")
                        perf_data_list.append(perf_data)
                        sampled_count += 1

        if sampled_count >= 10:  # 总共最多采样10个性能数据点
            break

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


def generate_stats_report(pipeline_stats: Dict, project_id: str, target_date: str) -> str:
    """生成执行情况报告"""
    report = f"# 星砂岛物语 - 流水线执行情况报告\n\n"
    report += f"**统计时间**: {target_date}\n\n"
    report += f"## 一、执行概览\n\n"
    report += "| 流水线 ID | 流水线名称 | Case 总数 | Case 成功 | Case 失败 | 设备总数 | 设备成功 | 设备失败 | 最新任务 |\n"
    report += "|-----------|-----------|----------|----------|----------|---------|---------|---------|----------|\n"

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

    for pipeline_id, stats in sorted(pipeline_stats.items()):
        pipeline_name = PIPELINE_NAMES.get(pipeline_id, f"流水线 {pipeline_id}")

        # 添加最新任务超链接
        if stats['latest_task_id']:
            task_url = f"https://uauto2.testplus.cn/project/{project_id}/taskDetail?taskId={stats['latest_task_id']}"
            latest_link = f"[查看]({task_url})"
        else:
            latest_link = "-"

        report += f"| {pipeline_id} | {pipeline_name} | **{stats['case_total']}** | **{stats['case_success']}** | **{stats['case_failed']}** | **{stats['device_total']}** | **{stats['device_success']}** | **{stats['device_failed']}** | {latest_link} |\n"

    report += f"\n"
    report += f"**总计**:\n"
    report += f"- 任务层级：共 **{total_task}** 次，成功 **{success_task}** 次，失败 **{failed_task}** 次，运行中 **{running_task}** 次\n"
    report += f"- Case层级：共 **{total_case}** 个，成功 **{success_case}** 个，失败 **{failed_case}** 个\n"
    report += f"- 设备层级：共 **{total_device}** 台，成功 **{success_device}** 台，失败 **{failed_device}** 台\n"

    return report


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


def generate_performance_report(baseline_by_pipeline: Dict, anomalies_by_pipeline: Dict, today_perf_by_pipeline: Dict) -> str:
    """生成性能对比报告
    包含:
    1. 当天成功案例按场景分组表格，表格内直接显示当天/基线对比
    2. 性能异常检测结果
    """
    report = "\n## 二、性能数据对比\n\n"

    has_data = False
    for pipeline_id, baseline in sorted(baseline_by_pipeline.items()):
        if not baseline:
            continue

        has_data = True
        pipeline_name = PIPELINE_NAMES.get(pipeline_id, f"流水线 {pipeline_id}")
        report += f"### {pipeline_name} ({pipeline_id})\n\n"

        # 当天成功案例 - 按场景分组，表格内直接对比基线
        today_perf = today_perf_by_pipeline.get(pipeline_id, [])
        if today_perf:
            case_stats = calculate_daily_case_stats(today_perf)
            report += "| 测试场景 | FPS TP90/基线 | 内存峰值（MB）/基线 | Jank（/10min）/基线 |\n"
            report += "|----------|---------------|---------------------|--------------------|\n"

            for case_name, stats in sorted(case_stats.items()):
                # TP90: 当天/基线 + 变化百分比
                if "tp90_avg" in stats and baseline.get("tp90_avg"):
                    change = (stats["tp90_avg"] - baseline["tp90_avg"]) / baseline["tp90_avg"] * 100
                    arrow = "↑" if change > 0 else "↓"
                    emoji = "⚠️" if change < -10 else ""
                    tp90_cell = f"{stats['tp90_avg']:.1f} / {baseline['tp90_avg']:.1f} ({arrow}{abs(change):.1f}%) {emoji}"
                elif "tp90_avg" in stats:
                    tp90_cell = f"{stats['tp90_avg']:.1f} / -"
                elif baseline.get("tp90_avg"):
                    tp90_cell = f"- / {baseline['tp90_avg']:.1f}"
                else:
                    tp90_cell = "- / -"

                # 内存: 当天/基线 + 变化百分比
                if "memory_avg" in stats and baseline.get("memory_avg"):
                    change = (stats["memory_avg"] - baseline["memory_avg"]) / baseline["memory_avg"] * 100
                    arrow = "↑" if change > 0 else "↓"
                    emoji = "⚠️" if change > 20 else ""
                    memory_cell = f"{stats['memory_avg']:.1f} / {baseline['memory_avg']:.1f} ({arrow}{abs(change):.1f}%) {emoji}"
                elif "memory_avg" in stats:
                    memory_cell = f"{stats['memory_avg']:.1f} / -"
                elif baseline.get("memory_avg"):
                    memory_cell = f"- / {baseline['memory_avg']:.1f}"
                else:
                    memory_cell = "- / -"

                # Jank: 当天/基线 + 变化百分比
                if "jank_avg" in stats and baseline.get("jank_avg"):
                    change = (stats["jank_avg"] - baseline["jank_avg"]) / baseline["jank_avg"] * 100
                    arrow = "↑" if change > 0 else "↓"
                    emoji = "⚠️" if change > 30 else ""
                    jank_cell = f"{stats['jank_avg']:.1f} / {baseline['jank_avg']:.1f} ({arrow}{abs(change):.1f}%) {emoji}"
                elif "jank_avg" in stats:
                    jank_cell = f"{stats['jank_avg']:.1f} / -"
                elif baseline.get("jank_avg"):
                    jank_cell = f"- / {baseline['jank_avg']:.1f}"
                else:
                    jank_cell = "- / -"

                report += f"| {case_name} | {tp90_cell} | {memory_cell} | {jank_cell} |\n"

            report += "\n"

        # 显示异常
        anomalies = anomalies_by_pipeline.get(pipeline_id, [])
        if anomalies:
            report += f"### 性能异常检测\n\n"
            report += f"⚠️ **检测到 {len(anomalies)} 个性能异常**：\n\n"
            for anomaly in anomalies:
                report += f"- **{anomaly['device_name']}** - {anomaly['case_name']}\n"
                for issue in anomaly['issues']:
                    report += f"  - {issue}\n"
                report += f"  - [查看 Perfeye](https://perfeye.testplus.cn/case/{anomaly['perfeye_id']}/report)\n"
                report += "\n"
        else:
            report += f"### 性能异常检测\n\n✅ **未检测到性能异常**\n\n"

        report += "\n"

    if not has_data:
        report += "⚠️ **暂无性能数据**\n"

    return report


def main():
    parser = argparse.ArgumentParser(description="自动化任务性能监控脚本")
    parser.add_argument("--project", type=str, default="starsandisland", help="项目 ID")
    parser.add_argument("--pipelines", type=str, required=True, help="流水线 ID 列表，逗号分隔")
    parser.add_argument("--mode", type=str, default="stats", choices=["stats", "anomaly", "full"], help="执行模式")
    parser.add_argument("--date", type=str, default="", help="统计日期 YYYY-MM-DD，默认为当天")
    parser.add_argument("--output", type=str, default="pipeline_stats.md", help="输出文件名")

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

    for pipeline_id in pipeline_ids:
        print(f"正在查询流水线 {pipeline_id}...")

        # 获取当天的构建记录（用于统计）
        today_builds = get_pipeline_builds(pipeline_id, project_id, today_start, today_end)
        stats = calculate_pipeline_stats(today_builds, project_id)
        pipeline_stats[pipeline_id] = stats

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
    report = generate_stats_report(pipeline_stats, project_id, target_date)
    # 跳过失败设备汇总和失败案例汇总
    # report += generate_failed_devices_report(failed_devices_by_pipeline, project_id)
    # report += generate_failed_cases_report(failed_cases_by_pipeline)
    report += generate_performance_report(baseline_by_pipeline, anomalies_by_pipeline, today_perf_by_pipeline)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n报告已生成: {output_file}")


if __name__ == "__main__":
    main()


