#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建并执行星砂 PC 端稳定性任务
- 自动选择最新 release 版本安装包
- 项目ID: starsandisland
- 流水线ID: 946
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from __init__ import AutoPlatformClient
from dotenv import load_dotenv

# 配置
PROJECT_ID = 'starsandisland'
PIPELINE_ID = 946
USER_ID = 'AI-AUTO-RUN'
BASE_URL = 'https://automation-api.testplus.cn'

def main():
    load_dotenv('../auto-platform-query/.env')

    client = AutoPlatformClient(base_url=BASE_URL, user_uid=USER_ID)

    print("=" * 70)
    print("创建并执行: 星砂 PC 端稳定性任务 (pipelineId=946)")
    print("=" * 70)
    print()

    # 1. 获取包列表，找到最新 release 版本
    print("1. 获取包列表...")
    url = f"{BASE_URL}/api/package/list"
    params = {"projectId": PROJECT_ID}
    headers = {"K-USER-UID": USER_ID}
    response = client.session.get(url, params=params, headers=headers)
    response.raise_for_status()
    result = response.json()

    if result.get('code') != 0:
        print(f"获取包列表失败: {result.get('msg')}")
        sys.exit(1)

    packages = result.get('data', [])
    print(f"找到 {len(packages)} 个包")
    print()

    # 过滤 release 类型
    release_packages = []
    for pkg in packages:
        # 检查是否是 release 版本
        package_name = pkg.get('packageName', '').lower()
        if 'release' in package_name or 'Release' in package_name:
            # 解析版本信息，获取编译时间
            create_time = pkg.get('createTime', '')
            release_packages.append({
                'packageId': pkg.get('packageId'),
                'packageName': pkg.get('packageName'),
                'downloadUrl': pkg.get('downloadUrl'),
                'versionName': pkg.get('versionName', ''),
                'createTime': create_time,
                'size': pkg.get('packageSize', 0)
            })

    if not release_packages:
        print("未找到 release 类型包!")
        sys.exit(1)

    # 按创建时间排序，最新的排在前面
    release_packages.sort(key=lambda x: x.get('createTime', ''), reverse=True)
    latest_package = release_packages[0]

    print(f"找到 {len(release_packages)} 个 release 包")
    print(f"最新版本:")
    print(f"  包ID: {latest_package['packageId']}")
    print(f"  名称: {latest_package['packageName']}")
    print(f"  版本: {latest_package['versionName']}")
    print(f"  创建时间: {latest_package['createTime']}")
    print(f"  下载地址: {latest_package['downloadUrl']}")
    print()

    # 2. 获取流水线详情
    print("2. 获取流水线详情...")
    pipeline_result = client.get_pipeline_detail(PIPELINE_ID, PROJECT_ID)
    if pipeline_result.get('code') != 0:
        print(f"获取流水线详情失败: {pipeline_result.get('msg')}")
        sys.exit(1)

    pipeline_data = pipeline_result.get('data', {})
    model = pipeline_data.get('model', {})

    # model 可能是 JSON 字符串
    if isinstance(model, str):
        try:
            model = json.loads(model)
        except:
            print(f"解析 model JSON 失败: {model[:100]}")
            sys.exit(1)

    if not model:
        print("流水线 model 为空")
        sys.exit(1)

    print(f"流水线名称: {model.get('baseInfo', {}).get('name')}")
    print(f"平台: {model.get('baseInfo', {}).get('platform')}")
    print()

    # 3. 更新 appVersion 信息
    print("3. 更新安装包信息...")
    app_version = {
        "packageId": latest_package['packageId'],
        "downloadUrl": latest_package['downloadUrl']
    }
    # 转换为 JSON 字符串存储（遵循原有格式）
    model['baseInfo']['appVersion'] = json.dumps(app_version)

    print(f"已更新为最新 release 包: {latest_package['packageName']}")
    print()

    # 4. 执行流水线
    print("4. 执行流水线...")
    execute_result = client.execute_pipeline(
        pipeline_id=PIPELINE_ID,
        user_id=USER_ID,
        project_id=PROJECT_ID,
        model=model
    )

    if execute_result.get('code') != 0:
        print(f"执行失败: code={execute_result.get('code')}, msg={execute_result.get('msg')}")
        sys.exit(1)

    print("执行成功!")
    print(f"   消息: {execute_result.get('msg')}")
    print(f"   数据: {execute_result.get('data')}")
    print()
    print("=" * 70)
    print("总结:")
    print(f"  项目: {PROJECT_ID}")
    print(f"  流水线: {PIPELINE_ID}")
    print(f"  安装包: {latest_package['packageName']}")
    print(f"  版本: {latest_package['versionName']}")
    print("=" * 70)

if __name__ == '__main__':
    # Add session to client
    import requests
    AutoPlatformClient.session = requests.Session()
    main()
