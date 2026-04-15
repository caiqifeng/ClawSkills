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
    # 通过流水线ID与指定时间动态获取任务ID数组
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


def get_taskInfo_by_taskId(taskIdList: list, startTimeAfter, projectId: str):
    # 通过任务ID与指定时间动态获取任务ID数组
    taskIdDict = {}
    for taskId in taskIdList:
        taskdata = requests.get(
            f"https://automation-api.testplus.cn/api/tasks/detail/{taskId}?projectId={projectId}"
        ).json()["data"]
        createTime = taskdata["createTime"].replace("T", " ")
        dt_createTime = datetime.strptime(createTime, "%Y-%m-%d %H:%M:%S")
        dt_startTimeAfter = datetime.strptime(startTimeAfter, "%Y-%m-%d %H:%M:%S")
        if dt_createTime < dt_startTimeAfter:
            print(
                f"任务ID: {taskId} 创建时间: {createTime} 在指定时间{startTimeAfter}之前，跳过"
            )
            continue

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
    """单个 perfeyeID 的处理逻辑"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.66 Safari/537.36 Edg/103.0.1264.44",
        "Authorization": "Bearer mj6cltF&!L#yWX8k",
    }
    url = f"https://perfeye.woa.com/api/v1/case/{perfeyeID}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 0 and "data" in data:
            case_data = data["data"]
            case_ex_list = case_data.get("case_ex", [])
            return case_ex_list
        else:
            print(f"perfeyeID {perfeyeID} 返回数据异常: {data}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"请求 perfeyeID {perfeyeID} 时出错: {e}")
        return []


def batch_find_case_ex(perfeye_ids: List[str], max_workers: int = 10) -> Dict[str, List[str]]:
    """批量并发查询 perfeyeID 的 case_ex"""
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_id = {executor.submit(find_case_ex_by_id, pid): pid for pid in perfeye_ids}
        for future in as_completed(future_to_id):
            perfeye_id = future_to_id[future]
            try:
                case_ex_list = future.result()
                results[perfeye_id] = case_ex_list
            except Exception as e:
                print(f"处理 perfeyeID {perfeye_id} 时发生异常: {e}")
                results[perfeye_id] = []
    return results


def get_checkpoint_error(taskID, buildCaseId, deviceId, projectId):
    res = requests.get(
        f"https://automation-api.testplus.cn/api/tasks/device/execute/info?taskId={taskID}&buildCaseId={buildCaseId}&deviceId={deviceId}&projectId={projectId}"
    ).json()["data"][0]["executeData"]
    for item in res[::-1]:
        if "执行失败" in item["msg"] and "事件" in item["msg"] and "稳定性" not in item["msg"]:
            msg = item["msg"].split("@@")[0].replace("事件：", "")
            if "执行失败" in msg:
                msg = msg.replace("执行失败", "出现")
            return msg
        elif "stack" in item and item["stack"] and "游戏启动失败或设备掉线" in item["stack"]:
            return "游戏启动流程出现"
        elif "stack" in item and item["stack"] and "游戏初始化流程出现宕机" in item["stack"]:
            return "游戏初始化流程出现"
    return ""


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
                    deviceId = caseDetail["deviceId"]
                    deviceName = caseDetail["deviceName"]
                    deviceIp = caseDetail.get("deviceIp", "")
                    buildCaseId = caseDetail["buildCaseId"]
                    duration = caseDetail["duration"]
                    hours = duration // 3600
                    minutes = (duration % 3600) // 60
                    seconds = duration % 60
                    duration_str = f"{hours}小时{minutes}分{seconds}秒"

                    machineCount += 1
                    versionMachineCount += 1

                    if duration >= Regulation_hours * 3600:
                        run_enough_device += 1
                        version_run_enough_device += 1

                    # 检测异常
                    is_abnormal = False
                    abnormal_reason = ""
                    links = []

                    # Crasheye链接
                    crasheye_link = ""
                    if "crasheyeId" in caseDetail and caseDetail["crasheyeId"]:
                        crasheye_id = caseDetail["crasheyeId"]
                        crasheye_link = f"https://crasheye.woa.com/crasheye/crash/{crasheye_id}"
                        is_abnormal = True
                        abnormal_reason = "Crasheye"

                    # 系统日志链接
                    system_log_link = ""
                    if "systemLogUrl" in caseDetail and caseDetail["systemLogUrl"]:
                        system_log_link = caseDetail["systemLogUrl"]

                    # 游戏日志链接
                    game_log_link = ""
                    if "gameLogUrl" in caseDetail and caseDetail["gameLogUrl"]:
                        game_log_link = caseDetail["gameLogUrl"]

                    # Perfeye链接
                    perfeye_link = ""
                    if "perfeyeId" in caseDetail and caseDetail["perfeyeId"]:
                        perfeye_id = caseDetail["perfeyeId"]
                        perfeye_link = f"https://perfeye.woa.com/case/{perfeye_id}"

                    # 检测checkpoint错误
                    checkpoint_error = ""
                    if not is_abnormal:
                        checkpoint_error = get_checkpoint_error(buildId, buildCaseId, deviceId, projectId)
                        if checkpoint_error:
                            is_abnormal = True
                            abnormal_reason = checkpoint_error

                    if is_abnormal:
                        device_info = f"    - {deviceName}"
                        if deviceIp:
                            device_info += f"@{deviceIp}"
                        device_info += f"执行了{duration_str}"

                        if checkpoint_error:
                            device_info += f"，在{checkpoint_error}"

                        # 添加链接
                        link_parts = []
                        if crasheye_link:
                            link_parts.append(f"[Crasheye]({crasheye_link})")
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
    parser.add_argument("--project", type=str, required=True, help="项目ID (jxsj4 或 start)")
    parser.add_argument("--pipelines", type=str, required=True, help="流水线ID列表，逗号分隔")
    parser.add_argument("--date", type=str, default="", help="统计日期 YYYY-MM-DD")
    parser.add_argument("--output", type=str, default="Stability_Summary.md", help="输出文件名")

    args = parser.parse_args()

    projectId = args.project
    pipelineIdList = [int(x.strip()) for x in args.pipelines.split(",")]
    Regulation_hours = 4

    startTimeAfter = args.date if args.date else ""
    if not startTimeAfter:
        start_of_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        startTimeAfter = start_of_day.strftime("%Y-%m-%d %H:%M:%S")

    if ":" not in startTimeAfter:
        startTimeAfter = startTimeAfter + " 00:00:00"

    endTime = ""
    if not endTime:
        endTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    taskIdList = get_taskIdList(pipelineIdList, startTimeAfter, endTime, projectId)

    extend_taskIdList = []
    taskIdList.extend(extend_taskIdList)

    delete_taskIdList = []
    taskIdList = [task for task in taskIdList if task not in delete_taskIdList]

    taskInfo = get_taskInfo_by_taskId(taskIdList, startTimeAfter, projectId)
    taskInfo = dict(sorted(taskInfo.items(), key=custom_sort_key))
    print(taskInfo)

    msg = get_task_msg(taskInfo, Regulation_hours, projectId)

    project_name = "《剑侠世界4》" if projectId == "jxsj4" else "《星砂岛物语》"
    Title = f"#### **{startTimeAfter.split(' ')[0].replace('-', '.')}{project_name}稳定性汇总**\n"
    All_Summary = Title + msg

    filename = args.output
    with open(filename, "w", encoding="utf-8") as file:
        file.write(All_Summary)

    print(f"报告已生成: {filename}")
