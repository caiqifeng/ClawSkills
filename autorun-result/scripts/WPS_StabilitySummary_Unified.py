from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from datetime import datetime, timedelta
import os
from typing import Dict, List, Set, Tuple
import argparse

import openpyxl
import requests


def custom_sort_key(item):
    key_priority = {"PC": 0, "Xbox": 1, "PS5": 2, "android": 3, "ios": 4, "NS2": 5}
    return key_priority.get(item[0], 999)


def get_taskIdList(pipelineIdList: list, startTimeAfter: str, endTime: str, projectId: str):
    taskIdList = []
    for pipelineId in pipelineIdList:
        res_json = {
            "projectId": projectId,
            "order_by": "queueTime",
            "asc": False,
            "filters": {
                "pipelineId": pipelineId,
                "startTime": startTimeAfter,
                "endTime": endTime,
            },
            "page": 1,
            "count": 20,
        }
        tasklist = requests.post(
            f"https://automation-api.testplus.cn/api/tasks/list?projectId={projectId}",
            json=res_json,
        ).json()["data"]["list"]
        for task in tasklist:
            buildId = task["buildId"]
            taskIdList.append(buildId)
    return taskIdList


def get_taskInfo_by_taskId(taskIdList: list, projectId: str):
    taskIdDict = {}
    for taskId in taskIdList:
        taskdata = requests.get(
            f"https://automation-api.testplus.cn/api/tasks/detail/{taskId}?projectId={projectId}"
        ).json()["data"]

        packageVersion = taskdata["packageVersion"]
        model_data = json.loads(taskdata["model"])
        platform = model_data["baseInfo"]["platform"]
        if platform not in taskIdDict:
            taskIdDict[platform] = {}

        if packageVersion not in taskIdDict[platform]:
            taskIdDict[platform][packageVersion] = []

        taskinfo = {}
        keys_to_keep = ["buildId", "buildName", "caseDetails"]
        new_taskdata = {key: taskdata[key] for key in keys_to_keep if key in taskdata}
        taskIdDict[platform][packageVersion].append(new_taskdata)

    return taskIdDict


def find_case_ex_by_id(perfeyeID: str) -> List[str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.66 Safari/537.36 Edg/103.0.1264.44",
        "Authorization": "Bearer mj6cltF&!L#yWX8k",
    }
    url = f"https://perfeye.testplus.cn/api/v1/case/{perfeyeID}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 0 and "data" in data:
            case_data = data["data"]
            case_ex_list = case_data.get("case_ex", [])
            return case_ex_list
        else:
            print(f"perfeyeID {perfeyeID} 返回数据异常：{data}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"请求 perfeyeID {perfeyeID} 时出错：{e}")
        return []


def batch_find_case_ex(perfeye_ids: List[str], max_workers: int = 10) -> Dict[str, List[str]]:
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_id = {executor.submit(find_case_ex_by_id, pid): pid for pid in perfeye_ids}
        for future in as_completed(future_to_id):
            perfeye_id = future_to_id[future]
            try:
                case_ex_list = future.result()
                results[perfeye_id] = case_ex_list
            except Exception as e:
                print(f"处理 perfeyeID {perfeye_id} 时发生异常：{e}")
                results[perfeye_id] = []
    return results


def get_task_msg(taskIdDict: dict, Regulation_hours: int, projectId: str):
    msg = ""
    index = 0
    INDEX_LIST = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
    for platform, versionDict in taskIdDict.items():
        msg += f"\n\n**{INDEX_LIST[index]}、{platform}**"
        index += 1
        version_msg = ""
        versionMachineCount = 0
        version_run_enough_device = 0
        for version, taskInfoList in versionDict.items():
            version_msg += f"\n\n - （版本：v{version}）\n"
            task_index = 1
            for taskInfo in taskInfoList:
                buildId = taskInfo["buildId"]
                buildName = taskInfo["buildName"]
                caseDetails = taskInfo["caseDetails"]

                task_url = f"https://uauto2.testplus.cn/project/{projectId}/taskDetail?taskId={buildId}"
                task_msg = f"   - {task_index}.[{buildName}]({task_url}) 任务执行汇总："
                task_index += 1

                machineCount = 0
                run_enough_device = 0
                abnormal_device_list = []

                for caseDetail in caseDetails:
                    buildCaseId = caseDetail["buildCaseId"]

                    deviceDetailList = caseDetail.get("deviceDetail", [])
                    for deviceDetail in deviceDetailList:
                        deviceId = deviceDetail.get("deviceId", "")
                        deviceName = deviceDetail.get("deviceName", "")
                        deviceIp = deviceDetail.get("ip", "")

                        # 计算每个设备的执行时长
                        startTime = deviceDetail.get("startTime", "")
                        endTime = deviceDetail.get("endTime", "")
                        duration = 0
                        if startTime and endTime:
                            try:
                                dt_start = datetime.strptime(startTime, "%Y-%m-%dT%H:%M:%S")
                                dt_end = datetime.strptime(endTime, "%Y-%m-%dT%H:%M:%S")
                                duration = int((dt_end - dt_start).total_seconds())
                            except:
                                duration = 0

                        hours = duration // 3600
                        minutes = (duration % 3600) // 60
                        seconds = duration % 60
                        duration_str = f"{hours}小时{minutes}分{seconds}秒"

                        # 获取链接信息
                        reportData = deviceDetail.get("reportData", {})

                        crasheye_link = ""
                        if "Crasheye" in reportData:
                            crasheye_link = reportData["Crasheye"]
                        elif "crasheyeId" in reportData:
                            crasheye_link = f"https://crasheye2.testplus.cn/crasheye/crash/{reportData['crasheyeId']}"
                        elif "crasheyeDumpKeys" in reportData and len(reportData["crasheyeDumpKeys"]) > 0:
                            # jxsj4项目使用crasheyeDumpKeys格式，构建搜索链接
                            first_key = reportData["crasheyeDumpKeys"][0]
                            appkey = reportData.get("appkey", "uusp2yf6")
                            today_str = target_date.split(" ")[0].replace("-", "-")
                            crasheye_link = f"https://crasheye2.testplus.cn/project/{projectId}/vk/{appkey}/error?startTime={today_str}&endTime={today_str}&searchs={first_key}"
                        else:
                            # 检查reportData中是否包含异常关键词，如果有则构建Crasheye搜索链接
                            abnormal_keywords = ["疑似闪退", "疑似卡死", "crasheye宕机", "socket崩溃"]
                            has_abnormal = False
                            for report_key in reportData.keys():
                                for keyword in abnormal_keywords:
                                    if keyword in report_key:
                                        has_abnormal = True
                                        break
                                if has_abnormal:
                                    break
                            if has_abnormal:
                                # 构建当天的Crasheye搜索页面，使用默认appkey
                                appkey = reportData.get("appkey", "uusp2yf6")
                                today_str = target_date.split(" ")[0].replace("-", "-")
                                crasheye_link = f"https://crasheye2.testplus.cn/project/{projectId}/vk/{appkey}/error?startTime={today_str}&endTime={today_str}"

                        system_log_link = ""
                        game_log_link = ""
                        logUrls = deviceDetail.get("logUrl", [])
                        for log_url in logUrls:
                            if "system-log" in log_url or "xgsdk" in log_url:
                                system_log_link = log_url
                            elif "Player.log" in log_url or "game-log" in log_url or "PlayerLog" in log_url:
                                game_log_link = log_url

                        perfeye_link = ""
                        if "perfeye" in reportData:
                            perfeye_id = reportData["perfeye"]
                            perfeye_link = f"https://perfeye.testplus.cn/case/{perfeye_id}/report"

                        machineCount += 1
                        versionMachineCount += 1

                        if duration >= Regulation_hours * 3600:
                            run_enough_device += 1
                            version_run_enough_device += 1

                        is_abnormal = False
                        crash_type_name = ""

                        if crasheye_link:
                            is_abnormal = True

                        # 检查是否包含异常关键词，满足也判定为异常
                        # 异常关键词包括：疑似闪退、疑似卡死、crasheye宕机
                        abnormal_keywords = ["疑似闪退", "疑似卡死", "crasheye宕机", "socket崩溃"]
                        # 检查reportData的key名称（异常类型作为key存储，优先级最高）
                        for report_key in reportData.keys():
                            for keyword in abnormal_keywords:
                                if keyword in report_key:
                                    is_abnormal = True
                                    if not crash_type_name:
                                        crash_type_name = keyword
                        # 检查case名称
                        if not crash_type_name:
                            case_name = caseDetail.get("caseName", "")
                            for keyword in abnormal_keywords:
                                if keyword in case_name:
                                    is_abnormal = True
                                    crash_type_name = keyword
                                    break
                        # 检查设备名称
                        if not crash_type_name:
                            for keyword in abnormal_keywords:
                                if keyword in deviceName:
                                    is_abnormal = True
                                    crash_type_name = keyword
                                    break

                        if is_abnormal:
                            device_info = f"    - {deviceName}"
                            if deviceIp:
                                device_info += f"({deviceIp})"
                            device_info += f"执行了{duration_str}"

                            link_parts = []
                            if crasheye_link:
                                link_text = crash_type_name if crash_type_name else "Crasheye"
                                link_parts.append(f"[{link_text}]({crasheye_link})")
                            if system_log_link:
                                link_parts.append(f"[系统日志]({system_log_link})")
                            if game_log_link:
                                link_parts.append(f"[游戏日志]({game_log_link})")
                            if perfeye_link:
                                link_parts.append(f"[Perfeye]({perfeye_link})")

                            if link_parts:
                                device_info += " " + " | ".join(link_parts)

                            abnormal_device_list.append(device_info)

                task_msg += f"共**{machineCount}台**设备，其中**{run_enough_device}台**设备执行超过4小时，"
                if abnormal_device_list:
                    task_msg += f"发现**{len(abnormal_device_list)}台**异常\n"
                    task_msg += "\n".join(abnormal_device_list)
                else:
                    task_msg += "未发现异常"

                version_msg += task_msg + "\n"

        msg += f"共**{versionMachineCount}台**设备，其中**{version_run_enough_device}台**执行超过4小时。"
        msg += version_msg

    return msg


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="稳定性测试汇总脚本")
    parser.add_argument("--project", type=str, required=True, help="项目 ID (jxsj4 或 start)")
    parser.add_argument("--pipelines", type=str, required=True, help="流水线 ID 列表，逗号分隔")
    parser.add_argument("--date", type=str, default="", help="统计日期 YYYY-MM-DD")
    parser.add_argument("--output", type=str, default="Stability_Summary.md", help="输出文件名")

    args = parser.parse_args()

    projectId = args.project
    pipelineIdList = [int(x.strip()) for x in args.pipelines.split(",")]
    Regulation_hours = 4

    target_date = args.date if args.date else ""
    if not target_date:
        today = datetime.now()
        target_date = today.strftime("%Y-%m-%d")
    
    if ":" not in target_date:
        target_date = target_date + " 00:00:00"
    
    startTimeAfter = target_date
    end_of_day = target_date.split(" ")[0] + " 23:59:59"
    endTime = end_of_day

    taskIdList = get_taskIdList(pipelineIdList, startTimeAfter, endTime, projectId)

    extend_taskIdList = []
    taskIdList.extend(extend_taskIdList)

    delete_taskIdList = []
    taskIdList = [task for task in taskIdList if task not in delete_taskIdList]

    taskInfo = get_taskInfo_by_taskId(taskIdList, projectId)
    taskInfo = dict(sorted(taskInfo.items(), key=custom_sort_key))
    print(taskInfo)

    msg = get_task_msg(taskInfo, Regulation_hours, projectId)

    project_name = "《剑侠世界4》" if projectId == "jxsj4" else "《星砂岛物语》"
    Title = f"# {startTimeAfter.split(' ')[0].replace('-', '.')}{project_name}稳定性汇总\n\n"
    All_Summary = Title + msg

    filename = args.output
    with open(filename, "w", encoding="utf-8") as file:
        file.write(All_Summary)

    print(f"报告已生成：{filename}")
