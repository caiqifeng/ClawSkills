"""
自动化平台操作助手 (Automation Platform Controller)
本 Skill 用于连接内部自动化平台，实现任务监控、故障设备重试、以及根据项目名称快速拉起测试流水线的功能。
"""

import requests
from typing import Dict, List, Optional, Union
from urllib.parse import urlparse, parse_qs


class AutoPlatformClient:
    """自动化平台 API 客户端"""

    def __init__(self, base_url: str = "https://uauto2.testplus.cn", user_uid: Optional[str] = None):
        """
        初始化客户端

        Args:
            base_url: 平台基础 URL
            user_uid: 用户 ID (用于 K-USER-UID Header)
        """
        self.base_url = base_url.rstrip('/')
        self.user_uid = user_uid if user_uid else "AI_AUTO"
        self.headers = {}
        self.headers["K-USER-UID"] = self.user_uid

    def set_user_uid(self, user_uid: str) -> None:
        """设置用户 ID"""
        self.user_uid = user_uid
        self.headers["K-USER-UID"] = user_uid

    def extract_task_id(self, task_url: str) -> str:
        """从任务 URL 中提取 taskId"""
        parsed = urlparse(task_url)
        query = parse_qs(parsed.query)
        if 'taskId' in query:
            return query['taskId'][0]
        # 尝试从路径提取
        path_parts = parsed.path.split('/')
        for part in path_parts:
            if part.isdigit():
                return part
        raise ValueError("无法从 URL 中提取 taskId，请检查 URL 格式")

    def get_task_detail(self, task_id: Union[str, int], project_id: str) -> Dict:
        """
        获取任务详情

        Args:
            task_id: 任务 ID
            project_id: 项目 ID

        Returns:
            任务详情 JSON
        """
        url = f"{self.base_url}/api/tasks/detail/{task_id}"
        params = {"projectId": project_id}

        response = requests.get(url, params=params, headers=self.headers)
        response.raise_for_status()
        try:
            return response.json()
        except:
            return {
                "code": -1,
                "msg": f"JSON解析错误，响应内容: {response.text[:200]}",
                "data": None
            }

    def get_device_exec_info(self, project_id: str, build_id: int) -> Dict:
        """
        获取设备执行信息

        Args:
            project_id: 项目 ID
            build_id: 构建 ID

        Returns:
            设备执行信息
        """
        url = f"{self.base_url}/api/tasks/device/execute/info"
        params = {"projectId": project_id, "buildId": build_id}

        response = requests.get(url, params=params, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_device_build_detail(self, project_id: str, build_id: int) -> Dict:
        """
        获取设备构建详情

        Args:
            project_id: 项目 ID
            build_id: 构建 ID

        Returns:
            设备构建详情
        """
        url = f"{self.base_url}/api/tasks/device/build/detail"
        params = {"projectId": project_id, "buildId": build_id}

        response = requests.get(url, params=params, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def search_pipelines(self, project_id: str, name: str) -> Dict:
        """
        搜索流水线

        Args:
            project_id: 项目 ID
            name: 流水线名称

        Returns:
            流水线列表
        """
        url = f"{self.base_url}/api/pipeline/list"
        params = {"projectId": project_id}

        response = requests.get(url, params=params, headers=self.headers)
        response.raise_for_status()
        data = response.json()

        # 根据名称过滤
        if data.get("code") == 0 and "data" in data:
            pipelines = data["data"]
            matched = [p for p in pipelines if name.lower() in p.get("model", {}).get("baseInfo", {}).get("name", "").lower()]
            data["matched"] = matched
        return data

    def get_pipeline_detail(self, pipeline_id: int, project_id: str) -> Dict:
        """
        获取流水线详情

        Args:
            pipeline_id: 流水线 ID
            project_id: 项目 ID

        Returns:
            流水线详情
        """
        url = f"{self.base_url}/api/pipeline/detail/{pipeline_id}"
        params = {"projectId": project_id}

        response = requests.get(url, params=params, headers=self.headers)
        response.raise_for_status()
        try:
            return response.json()
        except:
            return {
                "code": -1,
                "msg": f"JSON解析错误: {response.text[:200]}",
                "data": None
            }

    def execute_pipeline(self, pipeline_id: int, user_id: str, project_id: str, model: Optional[Dict] = None) -> Dict:
        """
        执行流水线 (POST /api/build/execute)

        Args:
            pipeline_id: 流水线 ID
            user_id: 用户 ID
            project_id: 项目 ID
            model: 模型参数

        Returns:
            响应结果
        """
        url = f"{self.base_url}/api/build/execute"
        params = {"projectId": project_id}

        data = {
            "pipelineId": pipeline_id,
            "userId": user_id,
            "model": model or {}
        }

        response = requests.post(url, params=params, json=data, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def retry_build(self, user_id: str, build_id: int, project_id: str,
                   retry_type: str = "FAILED", build_case_id: Optional[int] = None,
                   model: Optional[Dict] = None) -> Dict:
        """
        重试构建 (POST /api/build/retry)

        Args:
            user_id: 用户 ID
            build_id: 构建 ID
            project_id: 项目 ID
            retry_type: 重试类型 (SINGLE_ALL | SINGLE | FAILED | ALL)，默认 FAILED 重试所有失败案例中的失败设备
            build_case_id: 构建用例 ID，可选
            model: 模型参数，可选

        Returns:
            响应结果
        """
        url = f"{self.base_url}/api/build/retry"
        params = {"projectId": project_id}

        data = {
            "userId": user_id,
            "buildId": build_id,
            "buildCaseId": build_case_id,
            "retryType": retry_type,
            "model": model or {}
        }

        response = requests.post(url, params=params, json=data, headers=self.headers)
        try:
            result = response.json()
        except:
            return {
                "code": -1,
                "msg": f"JSON解析错误: {response.text[:500]}",
                "data": None
            }
        return result

    def retry_device_case(self, user_id: str, build_id: int, project_id: str,
                         build_case_id: int, build_device_id: int) -> Dict:
        """
        重试设备用例 (POST /api/build/case/device/retry)

        Args:
            user_id: 用户 ID
            build_id: 构建 ID
            project_id: 项目 ID
            build_case_id: 构建用例 ID
            build_device_id: 构建设备 ID

        Returns:
            响应结果
        """
        url = f"{self.base_url}/api/build/case/device/retry"
        params = {"projectId": project_id}

        data = {
            "userId": user_id,
            "buildId": build_id,
            "buildCaseId": build_case_id,
            "buildDeviceId": build_device_id
        }

        response = requests.post(url, params=params, json=data, headers=self.headers)
        response.raise_for_status()
        return response.json()


def get_task_info(task_input: Union[str, int], project_id: str, user_uid: str,
                  base_url: str = "https://uauto2.testplus.cn") -> Dict:
    """
    获取任务信息，包含设备状态列表

    Args:
        task_input: 任务 URL 或 任务 ID
        project_id: 项目 ID
        user_uid: 用户 ID
        base_url: 平台基础 URL

    Returns:
        JSON 格式的任务摘要，包含设备状态列表
    """
    client = AutoPlatformClient(base_url=base_url, user_uid=user_uid)

    # 如果是 URL，提取 task_id
    if isinstance(task_input, str) and task_input.startswith('http'):
        task_id = client.extract_task_id(task_input)
    else:
        task_id = str(task_input)

    result = client.get_task_detail(task_id, project_id)

    if result.get("code") != 0:
        return {
            "success": False,
            "message": result.get("msg", "获取任务详情失败"),
            "data": None
        }

    task_data = result.get("data", {})

    # 统计各状态设备
    devices = []
    failed_devices = []
    success_devices = []
    running_devices = []

    # 从任务数据中提取设备信息
    # 任务数据中包含 caseDetails 列表，每个 case 包含 deviceDetail 设备列表
    cases = task_data.get("caseDetails", [])
    for case in cases:
        case_devices = case.get("deviceDetail", [])
        for device in case_devices:
            device_info = {
                "case_id": case.get("caseId"),
                "device_id": device.get("deviceId"),
                "build_case_id": case.get("buildCaseId"),
                "build_device_id": device.get("buildDeviceId"),
                "device_name": device.get("deviceName"),
                "status": device.get("status"),
                "device_status": device.get("deviceStatus"),
                "platform": device.get("platform"),
                "build_id": task_data.get("buildId")
            }
            devices.append(device_info)
            # 检查是否失败
            if device.get("status") == "FAILED":
                failed_devices.append(device_info)
            elif device.get("status") == "SUCCESS":
                success_devices.append(device_info)
            elif device.get("status") in ["RUNNING", "QUEUE"]:
                running_devices.append(device_info)

    # model 有时候是 JSON 字符串，需要解析
    model_data = task_data.get("model")
    if isinstance(model_data, str):
        import json
        try:
            model_data = json.loads(model_data)
        except:
            pass

    summary = {
        "success": True,
        "task_id": task_id,
        "task_status": task_data.get("status"),
        "build_id": task_data.get("buildId"),
        "model": model_data,
        "total_devices": len(devices),
        "failed_devices_count": len(failed_devices),
        "success_devices_count": len(success_devices),
        "running_devices_count": len(running_devices),
        "failed_devices": failed_devices,
        "all_devices": devices,
        "raw_data": task_data
    }

    return summary


def manage_device_retry(task_id: Union[str, int], project_id: str, user_id: str,
                        build_id: int, device_ids: Optional[List[int]] = None,
                        retry_type: str = "FAILED", model: Optional[Dict] = None,
                        base_url: str = "https://uauto2.testplus.cn") -> Dict:
    """
    对指定失败设备触发重试操作 (POST /api/build/retry)

    Args:
        task_id: 任务 ID
        project_id: 项目 ID
        user_id: 用户 ID
        build_id: 构建 ID
        device_ids: 需要重试的设备 ID 列表，如果为 None 则重试所有失败设备
        retry_type: 重试类型，默认 FAILED (重试所有失败案例中的失败设备)
        model: 构建模型参数（必须，从原任务获取）
        base_url: 平台基础 URL

    Returns:
        重试操作结果
    """
    client = AutoPlatformClient(base_url=base_url, user_uid=user_id)

    # 如果不指定 device_ids，使用 FAILED 重试类型自动重试所有失败设备
    if device_ids is None or len(device_ids) == 0:
        # 调用 /api/build/retry 整体重试
        result = client.retry_build(
            user_id=user_id,
            build_id=build_id,
            project_id=project_id,
            retry_type=retry_type,
            model=model
        )
        return {
            "success": result.get("code") == 0,
            "message": result.get("msg"),
            "retry_type": retry_type,
            "data": result.get("data")
        }
    else:
        # 针对特定设备，需要先获取 build_case_id 逐个重试
        # 先获取任务信息找到每个设备对应的 case_id
        task_info = get_task_info(task_id, project_id, user_id, base_url)
        if not task_info["success"]:
            return {
                "success": False,
                "message": f"获取任务信息失败: {task_info.get('message')}",
                "data": None
            }

        results = []
        failed_devices_info = [d for d in task_info["failed_devices"] if d["device_id"] in device_ids]

        for device_info in failed_devices_info:
            build_case_id = device_info["build_case_id"]
            build_device_id = device_info["build_device_id"]

            try:
                result = client.retry_device_case(
                    user_id=user_id,
                    build_id=build_id,
                    project_id=project_id,
                    build_case_id=build_case_id,
                    build_device_id=build_device_id
                )
                results.append({
                    "device_id": device_info["device_id"],
                    "device_name": device_info["device_name"],
                    "case_id": build_case_id,
                    "success": result.get("code") == 0,
                    "message": result.get("msg")
                })
            except Exception as e:
                results.append({
                    "device_id": device_info["device_id"],
                    "device_name": device_info["device_name"],
                    "case_id": build_case_id,
                    "success": False,
                    "message": str(e)
                })

        success_count = sum(1 for r in results if r["success"])

        return {
            "success": success_count > 0,
            "total_devices": len(results),
            "success_count": success_count,
            "failed_count": len(results) - success_count,
            "results": results
        }


def trigger_pipeline(pipeline_id: int, user_id: str, project_id: str,
                     params: Optional[Dict] = None,
                     base_url: str = "https://uauto2.testplus.cn") -> Dict:
    """
    启动指定流水线 (POST /api/build/execute)

    Args:
        pipeline_id: 流水线 ID
        user_id: 用户 ID
        project_id: 项目 ID
        params: 构建参数
        base_url: 平台基础 URL

    Returns:
        启动结果
    """
    client = AutoPlatformClient(base_url=base_url, user_uid=user_id)

    try:
        result = client.execute_pipeline(
            pipeline_id=pipeline_id,
            user_id=user_id,
            project_id=project_id,
            model=params
        )

        return {
            "success": result.get("code") == 0,
            "message": result.get("msg"),
            "pipeline_id": pipeline_id,
            "data": result.get("data")
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"请求异常: {str(e)}",
            "pipeline_id": pipeline_id,
            "data": None
        }


def search_pipeline_by_name(project_id: str, name: str, user_uid: str,
                            base_url: str = "https://uauto2.testplus.cn") -> Dict:
    """
    根据名称搜索流水线

    Args:
        project_id: 项目 ID
        name: 流水线名称关键词
        user_uid: 用户 ID
        base_url: 平台基础 URL

    Returns:
        匹配的流水线列表
    """
    client = AutoPlatformClient(base_url=base_url, user_uid=user_uid)

    try:
        result = client.search_pipelines(project_id, name)

        if result.get("code") != 0:
            return {
                "success": False,
                "message": result.get("msg", "获取流水线列表失败"),
                "data": []
            }

        return {
            "success": True,
            "total_found": len(result.get("matched", [])),
            "pipelines": result.get("matched", []),
            "message": f"找到 {len(result.get('matched', []))} 个匹配的流水线"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"搜索异常: {str(e)}",
            "data": []
        }
