#!/usr/bin/env python3
"""
测试重试指定任务中的失败设备
"""

import os
import sys
from dotenv import load_dotenv

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from __init__ import get_task_info, manage_device_retry

# 加载环境变量
load_dotenv('../auto-platform-query/.env')

task_url = 'https://uauto2.testplus.cn/project/starsandisland/taskDetail?taskId=142612'
project_id = os.getenv('AUTOMATION_PROJECT_ID', 'starsandisland')
user_uid = 'AI-AUTO-RUN'
# 使用环境变量中的 API 地址
base_url = 'https://automation-api.testplus.cn'

print("=" * 60)
print("1. 获取任务信息...")
print("=" * 60)

import requests
import json
# 先调试请求
url = f"{base_url}/api/tasks/detail/142612"
params = {"projectId": project_id}
headers = {"K-USER-UID": user_uid}
print(f"请求 URL: {url}")
print(f"参数: {params}")
print(f"Headers: {headers}")
response = requests.get(url, params=params, headers=headers, allow_redirects=True)
print(f"状态码: {response.status_code}")
print()

# 打印完整数据结构
full_data = response.json()
if full_data.get('code') == 0:
    data = full_data.get('data', {})
    print(f"数据 keys: {list(data.keys())}")
    print(f"caseDetails 存在: {'caseDetails' in data}, 数量: {len(data.get('caseDetails', []))}")
    if data.get('caseDetails'):
        first_case = data['caseDetails'][0]
        print(f" 第一个 case keys: {list(first_case.keys())}")
        print(f" deviceList 存在: {'deviceList' in first_case}, 数量: {len(first_case.get('deviceList', []))}")
        if first_case.get('deviceList'):
            first_device = first_case['deviceList'][0]
            print(f" 第一个设备 keys: {list(first_device.keys())}")
            print(f" 第一个设备: {json.dumps(first_device, indent=2, ensure_ascii=False)}")
print()

result = get_task_info(task_url, project_id, user_uid, base_url)

if not result['success']:
    print(f"获取任务失败: {result.get('message', '未知错误')}")
    sys.exit(1)

print(f"任务 ID: {result['task_id']}")
print(f"任务状态: {result['task_status']}")
print(f"总设备数: {result['total_devices']}")
print(f"失败设备: {result['failed_devices_count']}")
print(f"成功设备: {result['success_devices_count']}")
print(f"运行中设备: {result['running_devices_count']}")
print()

if result['failed_devices_count'] > 0:
    print("失败设备列表:")
    for i, device in enumerate(result['failed_devices'], 1):
        print(f"  {i}. 设备ID={device['device_id']}, buildDeviceId={device['build_device_id']}, 名称={device['device_name']}, 状态={device['status']}")
    print()

    # 获取 build_id 和 model
    build_id = result['failed_devices'][0]['build_id']
    model = result['model']
    print(f"构建 ID: {build_id}")
    print()

    print("=" * 60)
    print(f"2. 开始重试 {result['failed_devices_count']} 个失败设备...")
    print("=" * 60)

    # 重试所有失败设备，使用 retry_type=FAILED，传入原 model
    retry_result = manage_device_retry(
        task_id=result['task_id'],
        project_id=project_id,
        user_id=user_uid,
        build_id=build_id,
        retry_type="FAILED",
        model=model,
        base_url=base_url
    )

    # 直接看 API 返回
    import requests
    import json
    url = f"{base_url}/api/build/retry?projectId={project_id}"
    headers = {"K-USER-UID": user_uid}
    data = {
        "userId": user_uid,
        "buildId": build_id,
        "buildCaseId": None,
        "retryType": "FAILED",
        "model": model
    }
    response = requests.post(url, headers=headers, json=data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.text}")
    print()
    print("重试结果:")
    print(retry_result)
else:
    print("没有发现失败设备，不需要重试。")
