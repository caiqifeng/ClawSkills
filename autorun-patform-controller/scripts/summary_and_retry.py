#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
汇总任务状态并重试失败设备
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from __init__ import get_task_info, AutoPlatformClient
from dotenv import load_dotenv

# 配置
task_url = 'https://uauto2.testplus.cn/project/mecha/taskDetail?taskId=142662'
project_id = 'mecha'
user_uid = 'AI-AUTO-RUN'
base_url = 'https://automation-api.testplus.cn'

# 加载环境变量
load_dotenv('../auto-platform-query/.env')

print("=" * 70)
print("任务汇总: https://uauto2.testplus.cn/project/mecha/taskDetail?taskId=142662")
print("=" * 70)

result = get_task_info(task_url, project_id, user_uid, base_url)

if not result['success']:
    print(f"获取任务失败: {result.get('message', '未知错误')}")
    sys.exit(1)

print(f"任务 ID: {result['task_id']}")
print(f"任务状态: {result['task_status']}")
print(f"构建 ID: {result['build_id']}")
print()
print(f"总设备数: {result['total_devices']}")
print(f"失败设备: {result['failed_devices_count']}")
print(f"成功设备: {result['success_devices_count']}")
print(f"运行/排队: {result['running_devices_count']}")
print()

if result['failed_devices_count'] > 0:
    print("失败设备列表:")
    for i, device in enumerate(result['failed_devices'], 1):
        print(f"  {i:2d}. {device['device_name']} (deviceId={device['device_id']}, buildDeviceId={device['build_device_id']})")
    print()

    print("=" * 70)
    print(f"开始重试 {result['failed_devices_count']} 个失败设备...")
    print("=" * 70)

    client = AutoPlatformClient(base_url=base_url, user_uid=user_uid)
    build_id = result['build_id']
    results = []

    for device in result['failed_devices']:
        build_case_id = device['build_case_id']
        build_device_id = device['build_device_id']

        print(f"\n[{len(results) + 1}/{result['failed_devices_count']}] "
              f"重试: {device['device_name']}")

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
            status = "成功" if success else "失败"
            print(f"  结果: {status}, code={code}, msg={msg}")
        except Exception as e:
            results.append({
                'device': device,
                'success': False,
                'code': -1,
                'msg': str(e)
            })
            print(f"  异常: {e}")

    print()
    print("=" * 70)
    print("重试完成汇总:")
    print("=" * 70)

    success_count = sum(1 for r in results if r['success'])
    fail_count = len(results) - success_count

    print(f"总计: {len(results)} 个失败设备")
    print(f"重试成功: {success_count}")
    print(f"重试失败: {fail_count}")
    print()

    if fail_count > 0:
        print("失败设备:")
        for r in results:
            if not r['success']:
                print(f"  - {r['device']['device_name']}: {r['msg']}")

else:
    print("没有失败设备，不需要重试。")
