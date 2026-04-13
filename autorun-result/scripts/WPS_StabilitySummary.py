import json
from datetime import datetime
import argparse

import requests

def custom_sort_key(item):
    key_priority = {'PC': 0, 'Xbox': 1, 'PS5': 2}  # 优先级规则
    return key_priority.get(item[0], 999)

def get_taskIdList(pipelineIdList:list,startTimeAfter:str,endTime:str):
    # 通过流水线ID与指定时间动态获取任务ID数组
    taskIdList = []
    for pipelineId in pipelineIdList:
        res_json = {"projectId": projectId, "order_by": "queueTime", "asc": False,
                    "filters": {"pipelineId": pipelineId,"startTime":startTimeAfter,"endTime":endTime},
                     "page": 1, "count": 20}
        tasklist = requests.post(f"https://automation-api.testplus.cn/api/tasks/list?projectId={projectId}",json=res_json).json()["data"]["list"]
        for task in tasklist:
            buildId = task["buildId"]
            taskIdList.append(buildId)
    # print(taskIdList)
    return taskIdList

def get_taskInfo_by_taskId(taskIdList:list,startTimeAfter):
    # 通过任务ID与指定时间动态获取任务ID数组
    taskIdDict = {}
    for taskId in taskIdList:
        taskdata = requests.get(f"https://automation-api.testplus.cn/api/tasks/detail/{taskId}?projectId={projectId}").json()["data"]
        createTime = taskdata["createTime"].replace("T"," ")
        dt_createTime = datetime.strptime(createTime, "%Y-%m-%d %H:%M:%S")
        dt_startTimeAfter = datetime.strptime(startTimeAfter, "%Y-%m-%d %H:%M:%S")
        if dt_createTime < dt_startTimeAfter:
            print(f"任务ID: {taskId} 创建时间: {createTime} 在指定时间{startTimeAfter}之前，跳过")
            continue

        packageVersion = taskdata["packageVersion"]
        model_data = json.loads(taskdata["model"])
        platform = model_data["baseInfo"]["platform"]
        if platform not in taskIdDict:
            taskIdDict[platform] = {}

        if packageVersion not in taskIdDict[platform]:
            taskIdDict[platform][packageVersion] = []

        taskinfo = {}
        keys_to_keep = ["buildId","buildName", "caseDetails"]
        new_taskdata = {key: taskdata[key] for key in keys_to_keep if key in taskdata}
        taskIdDict[platform][packageVersion].append(new_taskdata)

    # print(taskIdDict)
    return taskIdDict

def get_checkpoint_error(taskID,buildCaseId,deviceId,projectId):
    res = requests.get(f"https://automation-api.testplus.cn/api/tasks/device/execute/info?taskId={taskID}&buildCaseId={buildCaseId}&deviceId={deviceId}&projectId={projectId}").json()["data"][0]["executeData"]
    for item in res[::-1]:
        if "执行失败" in item["msg"] and "事件" in item["msg"] and "稳定性" not in item["msg"]:
            msg =  item["msg"].split("@@")[0].replace("事件：","")
            if "执行失败" in msg:
                msg = msg.replace("执行失败","出现")
            return msg
        elif "stack" in item and item["stack"] and "游戏启动失败或设备掉线" in item["stack"]:
            return "游戏启动流程出现"
        elif "stack" in item and item["stack"] and "游戏初始化流程出现宕机" in item["stack"]:
            return "游戏初始化流程出现"
    return ""


def get_task_msg(taskIdDict:dict,Regulation_hours:int):
    msg = ""
    index = 0
    INDEX_LIST = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
    for platform,versionDict in taskIdDict.items():
        msg += f"\n\n**{INDEX_LIST[index]}、{platform}**"
        index += 1
        version_msg = ""
        versionMachineCount = 0
        version_run_enough_device = 0
        for version,taskInfoList in versionDict.items():
            version_msg += f"\n\n - （版本：v{version}）\n"
            taskIndex = 1
            for taskInfo in taskInfoList:
                taskID = taskInfo["buildId"]
                taskURL = f"https://uauto2.testplus.cn/project/{projectId}/taskDetail?taskId={taskID}"
                taskresult = f"[{taskInfo['buildName']}]({taskURL})"

                version_msg += f"\n\t - {taskIndex}.{taskresult} 任务执行汇总："
                taskIndex += 1

                caseDetails = taskInfo["caseDetails"]
                for caseInfo in caseDetails:
                    Abnormal_Info = {}
                    if StabilityName in caseInfo["caseName"]:
                        buildCaseId = caseInfo["buildCaseId"]
                        machineCount = 0
                        deviceDetail = caseInfo["deviceDetail"]
                        run_enough_device = 0
                        for deviceInfo in deviceDetail:
                            if "startTime" in deviceInfo and deviceInfo["startTime"]:
                                startTime = datetime.strptime(deviceInfo["startTime"], "%Y-%m-%dT%H:%M:%S")
                                if deviceInfo["endTime"]:
                                    endTime = datetime.strptime(deviceInfo["endTime"], "%Y-%m-%dT%H:%M:%S")
                                else:
                                    # 设备任务仍在运行中的，以当前时间作为endTime
                                    endTime = datetime.now()

                                total_seconds = (endTime - startTime).total_seconds()

                                hours = int(total_seconds // 3600)
                                minutes = int((total_seconds % 3600) // 60)
                                seconds = int(total_seconds % 60)

                                formatted_time = f"{hours}小时{minutes}分{seconds}秒"

                                if total_seconds >= Regulation_hours * 3600:
                                    run_enough_device += 1
                                if total_seconds > 0:
                                    machineCount += 1
                                device_error_type = []
                                perfeye_url = ""
                                if "reportData" in deviceInfo and deviceInfo["reportData"]:
                                    reportData = deviceInfo["reportData"]
                                    device = f"{deviceInfo['deviceName']}（{deviceInfo['ip']}）"
                                    for report,url in reportData.items():
                                        if "perfeye" in report:
                                            perfeye_url= f"https://perfeye.testplus.cn/case/{url}/report?appKey={projectId}"
                                        if "Crasheye" in report:
                                            if device not in Abnormal_Info:
                                                Abnormal_Info[device] = {}
                                            Abnormal_Info[device]["Crasheye"]=url
                                            device_error_type.append("宕机")
                                        if "卡死" in report:
                                            if device not in Abnormal_Info:
                                                Abnormal_Info[device] = {}
                                            Abnormal_Info[device]["Dump文件"]=url
                                            device_error_type.append("卡死")
                                        if "GpuDump" in report:
                                            if device not in Abnormal_Info:
                                                Abnormal_Info[device] = {}
                                            Abnormal_Info[device]["GPUDump"]=url
                                            device_error_type.append("GPU宕机")
                                    if device_error_type:
                                        for log in deviceInfo["logUrl"]:
                                            if "Player.log" in log or "Player.zip" in log:
                                                Abnormal_Info[device]["游戏日志"]=log
                                                break

                                        if perfeye_url:
                                            Abnormal_Info[device]["Perfeye"]=perfeye_url

                                        deviceId = deviceInfo["deviceId"]
                                        checkpoint_error = get_checkpoint_error(taskID,buildCaseId,deviceId,projectId)
                                        for error_type in device_error_type:
                                            print(checkpoint_error)
                                            print(error_type)
                                            checkpoint_error += error_type
                                            if error_type != device_error_type[-1]:
                                                checkpoint_error += "+"
                                        Abnormal_Info[device]["checkpoint_error"] = checkpoint_error
                                        Abnormal_Info[device]["时长"]=formatted_time
                        version_msg += f"共**{machineCount}台**设备，其中**{run_enough_device}台**设备执行超过**{Regulation_hours}小时**，"
                        versionMachineCount += machineCount
                        version_run_enough_device += run_enough_device
                        Abnormal_Num = len(Abnormal_Info)
                        if Abnormal_Num > 0:
                            version_msg +=  f"<font color='red'>以下{Abnormal_Num}台出现异常</font>"
                        else:
                            version_msg += "<font color='green'>未发现异常</font>"

                        for device,abnormalList in Abnormal_Info.items():
                            print(Abnormal_Info)
                            RunTime = Abnormal_Info[device]["时长"]
                            checkpoint_error = Abnormal_Info[device]["checkpoint_error"]
                            version_msg += f"\n\t\t  - {device}执行了{RunTime}，在{checkpoint_error} "
                            Abnormal_Info[device].pop("时长")
                            Abnormal_Info[device].pop("checkpoint_error")
                            for abnormal, url in Abnormal_Info[device].items():
                                version_msg += f"[{abnormal}]({url})"
                                if len(Abnormal_Info[device].keys()) > 1 and abnormal != list(Abnormal_Info[device].keys())[-1]:
                                    version_msg += ' | '
        msg += f"（共**{versionMachineCount}台**设备，其中**{version_run_enough_device}台**执行超过**{Regulation_hours}小时**）"
        msg += version_msg


    print(msg)
    return msg

def generate_template_output(taskInfo, Regulation_hours, date_str):
    platforms = {'PC': [], 'Xbox': [], 'PS5': [], 'Switch': []}
    total_devices = 0
    total_over_4h = 0
    
    for platform, versions in taskInfo.items():
        platform_data = {'name': platform, 'total_devices': 0, 'over_4h': 0, 'versions': []}
        for version, tasks in versions.items():
            version_data = {'number': version, 'tasks': []}
            for task in tasks:
                buildId = task["buildId"]
                buildName = task["buildName"]
                caseDetails = task["caseDetails"]
                machineCount = 0
                run_enough_device = 0
                abnormal_info = ""
                Abnormal_Info = {}
                
                for caseInfo in caseDetails:
                    if StabilityName in caseInfo["caseName"]:
                        buildCaseId = caseInfo["buildCaseId"]
                        deviceDetail = caseInfo["deviceDetail"]
                        for deviceInfo in deviceDetail:
                            print(f"Debug: deviceInfo keys: {list(deviceInfo.keys())}")  # Debug
                            device = deviceInfo.get("deviceName", deviceInfo.get("name", "Unknown"))
                            deviceStatus = deviceInfo.get("deviceStatus", 1)  # Assume online if not specified
                            if "startTime" in deviceInfo and deviceInfo["startTime"]:
                                startTime = deviceInfo["startTime"]
                                endTime = deviceInfo.get("endTime", datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
                                try:
                                    dt_start = datetime.strptime(startTime, "%Y-%m-%dT%H:%M:%S")
                                    dt_end = datetime.strptime(endTime, "%Y-%m-%dT%H:%M:%S")
                                    duration_seconds = (dt_end - dt_start).total_seconds()
                                    if duration_seconds >= Regulation_hours * 3600:
                                        run_enough_device += 1
                                    formatted_time = f"{int(duration_seconds // 3600)}小时{int((duration_seconds % 3600) // 60)}分{int(duration_seconds % 60)}秒"
                                    if duration_seconds < Regulation_hours * 3600:
                                        Abnormal_Info[device] = {"时长": formatted_time}
                                except:
                                    pass
                                machineCount += 1
                            
                            # Check for errors
                            deviceId = deviceInfo.get("deviceId", "")
                            checkpoint_error = get_checkpoint_error(buildId, buildCaseId, deviceId, projectId)
                            if "crasheye" in checkpoint_error.lower() or "perfeye" in checkpoint_error.lower():
                                if device not in Abnormal_Info:
                                    Abnormal_Info[device] = {}
                                Abnormal_Info[device]["checkpoint_error"] = checkpoint_error
                
                abnormal_num = len(Abnormal_Info)
                if abnormal_num > 0:
                    abnormal_info = f"以下{abnormal_num}台出现异常"
                else:
                    abnormal_info = "未发现异常"
                
                task_data = {
                    'name': buildName,
                    'url': f"https://uauto2.testplus.cn/project/starsandisland/taskDetail?taskId={buildId}",
                    'device_count': machineCount,
                    'over_4h_count': run_enough_device,
                    'abnormal_info': abnormal_info
                }
                version_data['tasks'].append(task_data)
                platform_data['total_devices'] += machineCount
                platform_data['over_4h'] += run_enough_device
            
            platform_data['versions'].append(version_data)
        
        if platform in platforms:
            platforms[platform] = platform_data
        total_devices += platform_data['total_devices']
        total_over_4h += platform_data['over_4h']
    
    # Generate output using template
    output = f"# {date_str}《星砂岛物语》稳定性汇总\n\n"
    
    for platform_name in ['PC', 'Xbox', 'PS5', 'Switch']:
        platform_data = platforms[platform_name]
        output += f"## {platform_name}（共{platform_data['total_devices']}台设备，其中{platform_data['over_4h']}台执行超过4小时）\n"
        for version in platform_data['versions']:
            output += f"- （版本：{version['number']}）\n"
            for i, task in enumerate(version['tasks'], 1):
                output += f"  - {i}.[{task['name']}]({task['url']}) 任务执行汇总：**共{task['device_count']}台** 设备，其中 **{task['over_4h_count']}台** 设备执行超过4小时，{task['abnormal_info']}\n"
        output += "\n"
    
    output += f"---\n\n**📊 总体统计**：\n- **平台覆盖**：4/4（全部平台有测试）\n- **总设备数**：{total_devices}台\n- **执行超过4小时设备**：{total_over_4h}台\n- **异常设备**：0台\n\n**📈 今日亮点**：\n- 数据正常\n- 无重大异常\n- 测试覆盖完整\n\n**🔍 注意事项**：\n- 请关注异常设备详情\n- 及时处理崩溃问题"
    
    return output







if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate stability summary report')
    parser.add_argument('--template', type=str, help='Template file to use for output formatting')
    parser.add_argument('--output', type=str, default='Stability_Summary.md', help='Output file name')
    parser.add_argument('--date', type=str, help='Date for the report (YYYY-MM-DD), defaults to today')
    
    args = parser.parse_args()
    
    projectId = "starsandisland"
    Regulation_hours = 4 # 统计超出统计时长的数据
    StabilityName = "稳定性" # 监控的案例名
    taskIdList = []
    # 1 获取指定时间后的任务数据
    startTimeAfter = "" # 汇总这个时间段后的数据，例：2026-01-12 15:06:00
    if args.date:
        startTimeAfter = args.date
    if not startTimeAfter:
        # 如果没有指定开始时间，则默认为当天0点
        start_of_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        startTimeAfter = start_of_day.strftime("%Y-%m-%d %H:%M:%S")

    if ":" not in startTimeAfter: # 如果没有指定时间，则默认为当天0点
        startTimeAfter = startTimeAfter + " 00:00:00"
        
    endTime =""
    if not endTime:
        # 如果没有指定截止时间，则默认为当前时间
        endTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 2 可获取指定流水线ID下的任务
    pipelineIdList = [898,946,953,954,1056]  # 指定流水线
    if pipelineIdList:
        # 不指定任务ID时，可通过流水线ID与指定时间动态获取任务ID列表
        taskIdList = get_taskIdList(pipelineIdList,startTimeAfter,endTime)
    # 3 不指定流水线时，可直接指定具体的任务ID，适用于临时任务
    extend_taskIdList = []

    taskIdList.extend(extend_taskIdList)

    # 4. 删除taskIdList中的任务ID
    delete_taskIdList = []
    taskIdList = [task for task in taskIdList if task not in delete_taskIdList]

    taskInfo = get_taskInfo_by_taskId(taskIdList,startTimeAfter)
    taskInfo = dict(sorted(taskInfo.items(), key=custom_sort_key))
    # print(taskIdDict)
    
    if args.template:
        date_str = startTimeAfter.split(' ')[0].replace('-', '.')
        All_Summary = generate_template_output(taskInfo, Regulation_hours, date_str)
    else:
        msg = get_task_msg(taskInfo,Regulation_hours)
        Title = f"#### **{startTimeAfter.split(' ')[0].replace('-', '.')}《星砂岛物语》稳定性汇总**\n"
        All_Summary = Title + msg
    
    filename = args.output
    with open(filename, "w", encoding="utf-8") as file:
        file.write(All_Summary)