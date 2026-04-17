#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from __init__ import get_task_info, AutoPlatformClient
from dotenv import load_dotenv

load_dotenv('../auto-platform-query/.env')

task_url = 'https://uauto2.testplus.cn/project/starsandisland/taskDetail?taskId=142612'
project_id = os.getenv('AUTOMATION_PROJECT_ID', 'starsandisland')
user_uid = 'AI-AUTO-RUN'
base_url = 'https://automation-api.testplus.cn'

keyword = 'R5-3500'

result = get_task_info(task_url, project_id, user_uid, base_url)
client = AutoPlatformClient(base_url=base_url, user_uid=user_uid)
build_id = result['failed_devices'][0]['build_id']

found = False
for device in result['failed_devices']:
    if keyword in device['device_name']:
        found = True
        print('Found device: %s' % device['device_name'])
        print('  deviceId=%d, buildCaseId=%d, buildDeviceId=%d' % (
            device['device_id'], device['build_case_id'], device['build_device_id']))
        resp = client.retry_device_case(
            user_id=user_uid,
            build_id=build_id,
            project_id=project_id,
            build_case_id=device['build_case_id'],
            build_device_id=device['build_device_id']
        )
        print('  Result: code=%d, msg=%s' % (resp.get('code'), resp.get('msg')))
        break

if not found:
    for device in result['all_devices']:
        if keyword in device['device_name']:
            found = True
            print('Found (non-failed) device: %s' % device['device_name'])
            print('  status: %s' % device['status'])
            break

if not found:
    print('Device not found with keyword: %s' % keyword)
    print('\nAll failed devices:')
    for d in result['failed_devices']:
        print('  %s' % d['device_name'])
