# coding=utf-8
import re
from datetime import datetime, timedelta
import json
import requests
import csv
import os
import subprocess
#from base import to_bool, to_lower_str, to_str

UNITY_PRJ = r"F:/Downloads/ShaderCSV" ##to_str(r"F:/Downloads/ShaderCSV")
BRANCH_STR = "trunk" #to_str(r"${BRANCH}")
LOG_STATISTIC_URL = "http://10.11.10.112:8686/api/statistic"

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


def resolve_appkey(project: str) -> str:
    return PROJECT_APPKEYS.get(project, project)


def resolve_levels(levels=None):
    if not levels:
        return ["Exception", "Error"]

    if isinstance(levels, str):
        levels = re.split(r"[,，\s]+", levels.strip())

    result = []
    for level in levels:
        if level:
            result.append(LEVEL_ALIASES.get(level, level))
    return result or ["Exception", "Error"]


def resolve_time_range(time_desc: str = None, today: datetime = None):
    today = today or datetime.today()
    if not time_desc:
        return today.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

    time_desc = time_desc.strip()
    if time_desc in ("今天", "today"):
        return today.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    if time_desc in ("昨天", "yesterday"):
        yesterday = today - timedelta(days=1)
        return yesterday.strftime("%Y-%m-%d"), yesterday.strftime("%Y-%m-%d")
    if time_desc in ("最近一周", "近一周", "最近7天", "近7天", "last7days"):
        return (today - timedelta(days=7)).strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

    return time_desc, time_desc


def get_log_data(
    appkey: str,
    log_string: str = "",
    fromtime: str = (datetime.today() - timedelta(days=15)).strftime("%Y-%m-%d"),
    totime: str = datetime.today().strftime("%Y-%m-%d"),
    levels=None,
    project_versions: str = None,  # "0.7.0.426684"
	project_branch: str =None,
) -> str:
    if fromtime > totime:
        raise Exception("fromtime should be less than totime.")

    # 获取CSV文件
    url = LOG_STATISTIC_URL
    payload = {
        "appkey": resolve_appkey(appkey),  # "jxsj4"
        "from": 0,
        "size": 30000, #redis缓存过液数量,大于10000时传参生效(如不传或传参<10000,则默认10000
        "limit": 30000, #若未命中redis缓存,调es api时的透传参数,默认5000
        "fromtime": fromtime,
        "totime": totime,
        "merge_type": 0,
        "levels": resolve_levels(levels),
        "compare_with_project_version": "gte",  # 大于等于
        "skip": 0,
        "log_string": log_string or "",
        "branch": project_branch #"branches-rel/b_MechaWar_release"#,"trunk"#
    }
    if project_versions:
        payload["project_versions"] = [project_versions]  # 版本号
        
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        rt = json.loads(response.content)
    except requests.exceptions.SSLError:
        response = subprocess.run(
            [
                "curl.exe",
                "-sS",
                "-X",
                "POST",
                "-H",
                "Content-Type: application/json",
                "-d",
                "@-",
                url,
            ],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )
        rt = json.loads(response.stdout)
    
    print("请求参数：", payload)
    row_count = len(rt["data"])
    print("排除前行数：", row_count)
    
    return rt["data"]


def process_log_string(datas, result_file: str = "processed.csv", count_threshold: int = 0):
    csv_datas = [["ShaderName", "PassType", "Keywords"]]

    # 定义一个函数来处理logstring列
    def process_logstring(logstring):
        shader_name = re.search(r"ShaderName: (.*?)   ", logstring).group(1)
        pass_type = re.search(r"PassType:(.*?)(\n| )", logstring).group(1)
        keyword = re.search(r"Keywords:(.*?)   ", logstring).group(1)
        return shader_name, pass_type, keyword

    for item in datas:
        if item["count"] < count_threshold:
            continue

        ShaderName, PassType, Keywords = process_logstring(item["vector"])

        found = False
        for csv_item in csv_datas:
            if ShaderName in csv_item and PassType in csv_item and Keywords in csv_item:
                found = True
                break

        if not found:
            csv_datas.append([ShaderName, PassType, Keywords])

    row_count = len(csv_datas)
    print("排除后行数：",row_count)
    
    csv_file = os.path.join(UNITY_PRJ, result_file)
    # 打开或创建CSV文件并指定编码格式为UTF-8
    with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
        # 初始化CSV writer对象
        writer = csv.writer(file)

        # 将数据逐行写入CSV文件
        for row in csv_datas:
            writer.writerow(row)


if __name__ == "__main__":
    #print("=====================Shader Keywords==========================")
    #print("时间：", datetime.now())
    #data_NotPerfectly = get_log_data(
    #    appkey="mecha",
    #    # fromtime="2024-02-19",
    #    # totime="2024-02-19",
    #    log_string="Keywords not perfectly matched. ShaderName:",
    #    # project_versions="0.7.0.426684",
    #)
    #
    #data_WarmupCollect = get_log_data(
    #    appkey="mecha",
    #    # fromtime="2024-02-19",
    #    # totime="2024-02-19",
    #    log_string="ShaderVariants collect when using. ShaderName:",
    #    project_versions="0.10.0.715438", 
    #)
    #data_NotPerfectly_All = data_NotPerfectly + data_WarmupCollect
    #process_log_string(data_NotPerfectly_All)
    #
    print("=====================Shader Warmup==========================")
    print("时间：", datetime.now())
    data_warmup = get_log_data(
        appkey="mecha",
        # fromtime="2024-02-19",
        # totime="2024-02-19",
        log_string="ShaderVariants collect when using. ShaderName:",
        project_versions="0.10.0.715438", 
		project_branch = BRANCH_STR #"branches-rel/b_MechaWar_release"#,"trunk"#
    )
    process_log_string(data_warmup, result_file="processed_warmup.csv")

    print("=====================Shader InBattle ALL==========================")
    print("时间：", datetime.now())
    data_inbattle = get_log_data(
        appkey="mecha",
        fromtime = (datetime.today() - timedelta(days=360)).strftime("%Y-%m-%d"),
        totime = datetime.today().strftime("%Y-%m-%d"),
        log_string="InBattle ShaderVariants collect when using. ShaderName:",
        project_versions="0.10.0.752368", ## 从27号开始采集
		project_branch = BRANCH_STR #"branches-rel/b_MechaWar_release"#,"trunk"#
    )
    process_log_string(data_inbattle, result_file="processed_inbattle_all.csv")

    print("=====================Shader InBattle Strip==========================")
    print("时间：", datetime.now())
    data_inbattle = get_log_data(
        appkey="mecha",
        fromtime = (datetime.today() - timedelta(days=360)).strftime("%Y-%m-%d"),
        totime = datetime.today().strftime("%Y-%m-%d"),
        log_string="InBattle ShaderVariants collect when using. ShaderName:",
        project_versions="0.10.0.752368",
    )
    process_log_string(data_inbattle, result_file="processed_inbattle_strip.csv", count_threshold=40)
