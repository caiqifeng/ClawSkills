#!/usr/bin/env python3
"""
逐个重试失败设备
"""

import os
import sys
from dotenv import load_dotenv

# 添加当前目录到路径，直接导入
sys.path.insert(0, os.path.dirname(__file__))
from __init__ import get_task_info, AutoPlatformClient

# 加载环境变量
load_dotenv('../auto-platform-query/.env')

task_url = 'https://uauto2.testplus.cn/project/starsandisland/taskDetail?taskId=142612'
project_id = os.getenv('AUTOMATION_PROJECT_ID', 'starsandisland')
user_uid = 'AI-AUTO-RUN'
base_url = 'https://automation-api.testplus.cn'

print("=" * 60)
print("1. 获取任务信息...")
print("=" * 60)

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

if result['failed_devices_count'] <= 0:
    print("没有发现失败设备，不需要重试。")
    sys.exit(0)

print("失败设备列表:")
for i, device in enumerate(result['failed_devices'], 1):
    print(f"  {i}. deviceId={device['device_id']}, buildDeviceId={device['build_device_id']}, buildCaseId={device['build_case_id']}, 名称={device['device_name']}")
print()

build_id = result['failed_devices'][0]['build_id']

print("=" * 60)
print(f"2. 逐个重试 {result['failed_devices_count']} 个失败设备...")
print("=" * 60)

client = AutoPlatformClient(base_url=base_url, user_uid=user_uid)
results = []

for device in result['failed_devices']:
    build_case_id = device['build_case_id']
    build_device_id = device['build_device_id']

    print(f"\n正在重试: 设备={device['device_name']} (buildDeviceId={build_device_id})")

    try:
        resp = client.retry_device_case(
            user_id=user_uid,
            build_id=build_id,
            project_id=project_id,
            build_case_id=build_case_id,
            build_device_id=build_device_id
        )
        code = resp.get('code')
        msg = resp.get('msg')
        success = code == 0
        results.append({
            'device': device,
            'success': success,
            'code': code,
            'msg': msg
        })
        print(f"  结果: code={code}, msg={msg}")
    except Exception as e:
        results.append({
            'device': device,
            'success': False,
            'code': -1,
            'msg': str(e)
        })
        print(f"  异常: {e}")

print()
print("=" * 60)
print("重试完成汇总:")
print("=" * 60)

success_count = sum(1 for r in results if r['success'])
fail_count = len(results) - success_count

print(f"总计: {len(results)} 个设备, 成功: {success_count}, 失败: {fail_count}")
print()

for i, r in enumerate(results, 1):
    status = "✓ 成功" if r['success'] else "✗ 失败"
    print(f"  {i}. {r['device']['device_name']}: {status}, {r['msg']}")
