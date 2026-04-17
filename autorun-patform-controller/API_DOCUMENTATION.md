# Auto Server 接口文档

> 自动化测试平台 API 文档  
> 基于 FastAPI 构建  
> 基础地址: `http://{host}:{port}`

---

## 目录

- [通用说明](#通用说明)
- [用户模块 (User)](#用户模块-user)
  - [包管理 /api/package](#包管理-apipackage)
  - [用例管理 /api/case](#用例管理-apicase)
  - [设备管理 /api/device](#设备管理-apidevice)
  - [控制器管理 /api/controller](#控制器管理-apicontroller)
  - [流水线管理 /api/pipeline](#流水线管理-apipipeline)
  - [任务管理 /api/tasks](#任务管理-apitasks)
  - [账号管理 /api/account](#账号管理-apiaccount)
  - [项目管理 /api/project](#项目管理-apiproject)
  - [构建执行 /api/build](#构建执行-apibuild)
  - [日志查询 /api/log](#日志查询-apilog)
  - [AppKey管理 /api/appkey](#appkey管理-apiappkey)
  - [远程控制 /api/mobile_control](#远程控制-apimobile_control)
  - [分组管理 /api/group](#分组管理-apigroup)
  - [后台管理 /api/admin](#后台管理-apiadmin)
- [控制器模块 (Build)](#控制器模块-build)
  - [构建控制器 /build/controller](#构建控制器-buildcontroller)
  - [日志上传 /build/logs](#日志上传-buildlogs)
  - [对比分析 /build/compare](#对比分析-buildcompare)
  - [构建项目 /build/project](#构建项目-buildproject)
  - [DevOps /build/devops](#devops-builddevops)

---

## 通用说明

### 认证方式

所有 `/api/` 前缀的请求需在 Header 中携带：

| Header | 说明 |
|--------|------|
| `K-USER-UID` | 用户ID（必须） |

同时请求中需要 `projectId` 查询参数用于项目权限校验。

### 通用响应格式

```json
{
  "code": 0,
  "msg": "success",
  "data": {}
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，0 表示成功 |
| msg | string | 提示信息 |
| data | object | 响应数据 |

### 通用枚举值

**构建状态 (BuildStatus)**

| 值 | 说明 |
|----|------|
| QUEUE | 排队中 |
| RUNNING | 运行中 |
| SUCCESS | 成功 |
| FAILED | 失败 |
| CANCEL | 已取消 |

**触发类型 (TriggerType)**

| 值 | 说明 |
|----|------|
| 0 | 手动触发 |
| 1 | 定时触发 |
| 2 | 远程服务触发 |

**机器分配方式 (MachineType)**

| 值 | 说明 |
|----|------|
| auto | 自动派发 |
| appoint | 手动指定 |

**设备状态 (DeviceStatus)**

| 值 | 说明 |
|----|------|
| 0 | 离线 |
| 1 | 在线 |

**设备忙碌状态 (DeviceBusyStatus)**

| 值 | 说明 |
|----|------|
| 0 | 空闲 |
| 1 | 忙碌 |
| 2 | 冻结 |

**平台类型 (PlatformType)**

| 值 | 说明 |
|----|------|
| xbox | Xbox |
| ios | IOS |
| android | Android |
| pc | PC |
| windows | Windows |
| ps5 | PS5 |
| steamdeck | SteamDeck |
| harmonyos | HarmonyOS |
| switch | Switch |

**重试类型 (RetryType)**

| 值 | 说明 |
|----|------|
| SINGLE_ALL | 单个案例重跑所有设备任务 |
| SINGLE | 单个案例重试失败设备任务 |
| FAILED | 重试所有失败案例中的失败设备 |
| ALL | 全部案例重跑 |

**通知类型 (NotifyType)**

| 值 | 说明 |
|----|------|
| email | 邮件通知 |
| wps | 协作通知 |

**日志级别 (LogLevel)**

| 值 | 说明 |
|----|------|
| INFO | 信息 |
| DEBUG | 调试 |
| WARNING | 警告 |
| ERROR | 错误 |
| CRITICAL | 严重 |
| EXCEPTION | 异常 |

---

## 用户模块 (User)

---

### 包管理 `/api/package`

#### GET `/api/package/list` — 获取包列表

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |

**响应**: 包列表数据

---

#### GET `/api/package/detail` — 获取包详情

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |
| packageId | int | 是 | 包ID |

---

#### POST `/api/package/management` — 添加应用管理

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |

---

### 用例管理 `/api/case`

#### GET `/api/case/list` — 获取用例列表

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |

---

#### POST `/api/case/save` — 创建用例

**请求体 (JSON)**

```json
{
  "userId": "string (必填, 用户ID)",
  "projectId": "string (必填, 项目ID)",
  "caseName": "string (必填, 用例名称)",
  "caseDesc": "string (必填, 用例描述)",
  "scriptPath": "string (必填, 脚本路径)",
  "runningTimes": 1,
  "retryTimes": 1,
  "machineCount": 1,
  "timeOut": 60,
  "caseTag": "string (可选, 用例标签)",
  "accountPoolName": "string (可选, 账号池名称)",
  "caseParam": "string (可选, 用例参数)"
}
```

---

#### PUT `/api/case/save` — 更新用例

**请求体 (JSON)**

```json
{
  "id": 1,
  "userId": "string (必填, 用户ID)",
  "caseName": "string (必填, 用例名称)",
  "caseDesc": "string (必填, 用例描述)",
  "scriptPath": "string (必填, 脚本路径)",
  "runningTimes": 1,
  "retryTimes": 1,
  "machineCount": 1,
  "timeOut": 60,
  "accountPoolName": "string (可选)",
  "caseTag": "string (可选)",
  "caseParam": "string (可选)"
}
```

---

#### GET `/api/case/linked/pipeline` — 获取用例关联的流水线

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |
| caseId | int | 是 | 用例ID |

---

#### DELETE `/api/case/delete` — 删除用例

**请求体 (JSON)**

```json
{
  "userId": "string (必填)",
  "caseId": 1,
  "pipelineIds": [1, 2, 3]
}
```

---

#### GET `/api/case/deleted/list` — 获取已删除用例列表

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |

---

#### PUT `/api/case/batch/update/config` — 批量更新用例机器配置

**请求体 (JSON)**

```json
{
  "caseIdList": [1, 2, 3],
  "machineCount": 2
}
```

---

### 设备管理 `/api/device`

#### GET `/api/device/list` — 获取设备列表

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |

---

#### GET `/api/device/all` — 获取所有设备

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |

---

#### POST `/api/device/save` — 添加设备

**请求体 (JSON)**

```json
{
  "deviceName": "string (必填, 设备名称)",
  "deviceModel": "string (必填, 设备型号)",
  "runNo": "string (必填, 运行设备号 USB)",
  "runningNo": "string (必填, 运行时设备号 USB|WiFi)",
  "deviceIp": "string (必填, 设备IP)",
  "groupId": 1,
  "platform": "string (必填, 平台: android/ios/pc/...)",
  "systemVersion": "string (必填, 系统版本)",
  "operator": "string (必填, 操作人)",
  "pictureQuality": "0",
  "controllerId": null,
  "belong": "all",
  "parameters": "string (可选)",
  "asset": "string (可选, 资产编号)"
}
```

---

#### GET `/api/device/{deviceId}/listAgentBuilds` — 获取设备构建列表

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| deviceId | int | 设备ID |

---

#### PUT `/api/device/update/{deviceId}` — 更新设备

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| deviceId | int | 设备ID |

---

#### GET `/api/device/screenshots` — 获取设备截图

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |
| deviceId | int | 是 | 设备ID |

---

#### POST `/api/device/device/cancel` — 取消设备任务

---

#### PUT `/api/device/free` — 释放设备

**请求体 (JSON)**

```json
{
  "deviceId": 1,
  "userId": "string (必填)"
}
```

---

#### GET `/api/device/{deviceId}/build/history/detail` — 获取设备构建历史详情

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| deviceId | int | 设备ID |

---

#### GET `/api/device/{deviceId}/pipeline/relation` — 获取设备流水线关联

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| deviceId | int | 设备ID |

---

#### DELETE `/api/device/{deviceId}` — 删除设备

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| deviceId | int | 设备ID |

---

### 控制器管理 `/api/controller`

#### GET `/api/controller/list` — 获取控制器列表

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |

---

#### POST `/api/controller/save` — 添加控制器

**请求体 (JSON)**

```json
{
  "controllerName": "string (必填)",
  "macAddress": "string (可选)",
  "groupId": 1,
  "controllerIp": "string (必填)",
  "operator": "string (必填)",
  "deviceList": []
}
```

---

#### PUT `/api/controller/update` — 更新控制器

**请求体 (JSON)**

```json
{
  "controllerId": 1,
  "macAddress": "string (可选)",
  "groupId": 1,
  "controllerName": "string (必填)",
  "controllerIp": "string (必填)",
  "operator": "string (必填)",
  "deviceList": []
}
```

---

### 流水线管理 `/api/pipeline`

#### POST `/api/pipeline/add` — 创建流水线

**请求体 (JSON)**

```json
{
  "user": "string (必填, 用户)",
  "pipelineId": null,
  "model": {
    "baseInfo": {
      "platform": "android",
      "branch": "string (分支)",
      "buildType": "string (构建类型)",
      "buildKeywords": "string (构建关键字)",
      "appKey": "string",
      "packageId": 1,
      "name": "string (流水线名称)",
      "crontab": "string (cron表达式, 可选)",
      "parameters": "{}",
      "parametersKey": "[]"
    },
    "machine": {
      "type": "auto | appoint",
      "machineNum": 2,
      "modelList": [],
      "machineList": []
    },
    "cases": [
      {
        "caseId": 1,
        "runningTimes": 1,
        "retryTimes": 1
      }
    ],
    "notify": {
      "controller": {
        "token": "string (飞书/协作机器人token)"
      },
      "server": {
        "type": "email | feishu | wps",
        "trigger": "auto | manual",
        "users": ["user1@example.com"]
      }
    }
  }
}
```

---

#### PUT `/api/pipeline/update` — 更新流水线

请求体同创建流水线，`pipelineId` 为必填。

---

#### GET `/api/pipeline/list` — 获取流水线列表

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |

---

#### DELETE `/api/pipeline/delete/{pipelineId}` — 删除流水线

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| pipelineId | int | 流水线ID |

---

#### GET `/api/pipeline/detail/{pipelineId}` — 获取流水线详情

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| pipelineId | int | 流水线ID |

---

#### GET `/api/pipeline/pipelineName/check` — 检查流水线名称是否重复

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |
| pipelineName | string | 是 | 流水线名称 |

---

#### POST `/api/pipeline/collect/add` — 收藏流水线

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |
| pipelineId | int | 是 | 流水线ID |

---

#### DELETE `/api/pipeline/collect/delete` — 取消收藏

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |
| pipelineId | int | 是 | 流水线ID |

---

#### GET `/api/pipeline/{pipelineId}/performance/trend` — 获取性能趋势

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| pipelineId | int | 流水线ID |

---

#### POST `/api/pipeline/{pipelineId}/power` — 添加流水线能力

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| pipelineId | int | 流水线ID |

**请求体 (JSON)**

```json
{
  "projectId": "string (必填)",
  "pipelineId": 1,
  "caseId": 1,
  "deviceId": 1,
  "userId": "string (必填)",
  "url": "string (图片地址)"
}
```

---

#### GET `/api/pipeline/power/list` — 获取能力列表

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |

---

### 任务管理 `/api/tasks`

#### POST `/api/tasks/list` — 获取任务列表

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |

---

#### GET `/api/tasks/detail/{taskId}` — 获取任务详情

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| taskId | int | 任务ID |

---

#### POST `/api/tasks/delete` — 删除任务

---

#### POST `/api/tasks/export` — 导出任务

---

#### POST `/api/tasks/task/change/weight` — 调整任务优先级

**请求体 (JSON)**

```json
{
  "taskId": 1,
  "userId": "string (必填)"
}
```

---

#### POST `/api/tasks/send/email` — 发送邮件报告

---

#### GET `/api/tasks/device/execute/info` — 获取设备执行信息

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |
| buildId | int | 是 | 构建ID |

---

#### GET `/api/tasks/device/build/detail` — 获取设备构建详情

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |
| buildId | int | 是 | 构建ID |

---

#### GET `/api/tasks/debug` — 调试端点

---

### 账号管理 `/api/account`

#### GET `/api/account/list` — 获取账号列表

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |

---

#### POST `/api/account/add/account/pool` — 创建账号池

**请求体 (JSON)**

```json
{
  "userId": "string (必填)",
  "name": "string (必填, 账号池名称)",
  "desc": "string (可选, 描述)",
  "account_list": [
    {
      "user": "string (必填, 账号名)",
      "server": "string (必填, 服务器信息)",
      "password": "string (可选)"
    }
  ]
}
```

---

#### PUT `/api/account/update/account/pool` — 更新账号池

请求体同创建账号池。

---

#### GET `/api/account/account/pool/list` — 获取账号池列表

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |

---

#### GET `/api/account/pool/accounts` — 获取池中账号

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |
| poolName | string | 是 | 账号池名称 |

---

#### GET `/api/account/pool/case/list` — 获取账号池关联用例

---

#### PUT `/api/account/update/account/pool/case/correlation` — 更新账号池用例关联

**请求体 (JSON)**

```json
{
  "userId": "string (必填)",
  "poolName": "string (必填)",
  "caseList": [1, 2, 3]
}
```

---

### 项目管理 `/api/project`

#### GET `/api/project/config` — 获取项目配置

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |

---

#### POST `/api/project/config/add` — 添加项目配置

**请求体 (JSON)**

```json
{
  "projectId": "string (必填)",
  "projectName": "string (必填)",
  "config": "string (可选, 动态表单配置JSON)",
  "modifyUser": "string (必填)"
}
```

---

#### POST `/api/project/config/update` — 更新项目配置

**请求体 (JSON)**

```json
{
  "id": "string (必填, 记录ID)",
  "config": "string (可选, 动态表单配置JSON)",
  "modifyUser": "string (必填)"
}
```

---

#### PUT `/api/project/email/template` — 编辑邮件模板

**请求体 (JSON)**

```json
{
  "email_head": "string (必填)",
  "table_head": "string (必填)",
  "table_row": "string (必填)",
  "table_footer": "string (必填)",
  "email_footer": "string (必填)"
}
```

---

#### GET `/api/project/email/template` — 获取邮件模板

---

#### PUT `/api/project/email/config` — 编辑邮件配置

**请求体 (JSON)**

```json
{
  "email_config": {},
  "userId": "string (必填)"
}
```

---

#### GET `/api/project/email/config` — 获取邮件配置

---

#### GET `/api/project/xiezuo/token` — 获取协作Token

---

#### PUT `/api/project/xiezuo/token` — 编辑协作Token

**请求体 (JSON)**

```json
{
  "xiezuoToken": "string (可选)",
  "userId": "string (必填)"
}
```

---

#### GET `/api/project/trend/pipelines` — 获取趋势流水线列表

---

#### PUT `/api/project/trend/pipelines` — 编辑趋势流水线

**请求体 (JSON)**

```json
{
  "trendPipelines": [1, 2, 3],
  "userId": "string (必填)"
}
```

---

#### POST `/api/project/ks_test` — KS 测试

---

### 构建执行 `/api/build`

#### POST `/api/build/execute` — 执行流水线

**请求体 (Form)**

```json
{
  "pipelineId": 1,
  "userId": "string (必填)",
  "model": { "... (ModelParams 结构)" }
}
```

---

#### POST `/api/build/retry` — 重试构建

**请求体 (JSON)**

```json
{
  "userId": "string (必填)",
  "buildId": 1,
  "buildCaseId": null,
  "retryType": "SINGLE_ALL | SINGLE | FAILED | ALL",
  "model": { "... (ModelParams 结构)" }
}
```

---

#### POST `/api/build/case/device/retry` — 重试设备用例

**请求体 (JSON)**

```json
{
  "userId": "string (必填)",
  "buildId": 1,
  "buildCaseId": 1,
  "buildDeviceId": 1
}
```

---

#### POST `/api/build/cancel` — 取消构建

**请求体 (JSON)**

```json
{
  "userId": "string (必填)",
  "buildId": 1,
  "pipelineId": 1,
  "reportUpload": 0
}
```

---

#### POST `/api/build/case/cancel` — 取消用例

**请求体 (JSON)**

```json
{
  "userId": "string (必填)",
  "buildId": 1,
  "buildCaseId": 1,
  "reportUpload": 0
}
```

---

#### POST `/api/build/single/device/cancel` — 取消单设备

**请求体 (JSON)**

```json
{
  "userId": "string (必填)",
  "buildId": 1,
  "buildCaseId": 1,
  "deviceId": 1,
  "buildDeviceId": 1,
  "reportUpload": 0
}
```

---

### 日志查询 `/api/log`

#### GET `/api/log/query` — 查询日志

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |
| buildId | int | 是 | 构建ID |

---

### AppKey管理 `/api/appkey`

#### POST `/api/appkey/create` — 创建AppKey

**请求体 (JSON)**

```json
{
  "projectId": "string (可选)",
  "packageName": "string (必填, 包名)",
  "packageActivity": "string (可选)",
  "projectName": "string (可选, 游戏项目名称)",
  "appkey": "string (必填)"
}
```

---

#### PUT `/api/appkey/update` — 更新AppKey

**请求体 (JSON)**

```json
{
  "id": "string (必填, 记录ID)",
  "projectId": "string (可选)",
  "packageName": "string (必填)",
  "packageActivity": "string (可选)",
  "projectName": "string (可选)",
  "appkey": "string (必填)"
}
```

---

#### GET `/api/appkey/list` — 获取AppKey列表

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |

---

### 远程控制 `/api/mobile_control`

#### GET `/api/mobile_control/open_stream` — 开启控制流

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |
| deviceId | int | 是 | 设备ID |

---

#### GET `/api/mobile_control/close_stream` — 关闭控制流

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |
| deviceId | int | 是 | 设备ID |

---

### 分组管理 `/api/group`

#### GET `/api/group/project/group` — 获取项目分组关系

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |

---

### 后台管理 `/api/admin`

#### POST `/api/admin/load_user_from_iam` — 从IAM同步用户

---

## 控制器模块 (Build)

> 此模块供控制器（Agent）调用，无需用户认证

---

### 构建控制器 `/build/controller`

#### POST `/build/controller/controller/heartbeat` — 控制器心跳

**请求体 (JSON)**

```json
{
  "macAddress": "string (可选, MAC地址)",
  "devices": ["device_sn_1", "device_sn_2"]
}
```

---

#### GET `/build/controller/startup` — 获取可执行设备

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| macAddress | string | 是 | 控制器MAC地址 |

---

#### GET `/build/controller/get/case` — 获取待执行用例

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| buildId | int | 是 | 构建ID |
| deviceId | int | 是 | 设备ID |

---

#### POST `/build/controller/complete/case` — 上报用例完成

**请求体 (JSON)**

```json
{
  "buildId": 1,
  "buildCaseId": 1,
  "caseId": 1,
  "deviceId": 1,
  "reportData": "string (可选, 报告数据JSON)",
  "status": "SUCCESS | FAILED | CANCEL",
  "errorMsg": "string (可选)"
}
```

---

#### PUT `/build/controller/build/report/data` — 同步用例执行信息

**请求体 (JSON)**

```json
{
  "buildId": 1,
  "buildCaseId": 1,
  "deviceId": 1,
  "timestamp": 1234567890,
  "message": "string (执行消息)",
  "imageObjectName": "string (可选, 截图对象名)",
  "logObjectName": "string (可选, 日志对象名)"
}
```

---

#### POST `/build/controller/build/end` — 构建结束上报

**请求体 (JSON)**

```json
{
  "buildId": 1,
  "deviceId": 1,
  "status": "SUCCESS | FAILED | CANCEL"
}
```

---

#### GET `/build/controller/check/cancel/case` — 检查用例是否取消

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| buildCaseId | int | 是 | 构建用例ID |

---

#### GET `/build/controller/check/cancel/devices` — 检查设备是否取消

---

#### POST `/build/controller/upload/screenshot` — 上传截图

---

#### GET `/build/controller/offline/devices` — 获取离线设备

---

#### GET `/build/controller/sync` — 同步

---

#### GET `/build/controller/sync/fail` — 同步失败记录

---

#### GET `/build/controller/sync/check` — 同步检查

---

#### GET `/build/controller/sync/reset` — 同步重置

---

#### GET `/build/controller/case/running/status` — 获取用例运行状态

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| buildId | int | 是 | 构建ID |
| deviceId | int | 是 | 设备ID |

---

#### GET `/build/controller/case/device/running/detail` — 获取设备运行详情

---

#### GET `/build/controller/build/info` — 获取构建信息

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| buildId | int | 是 | 构建ID |

---

#### GET `/build/controller/reset/device/by/controller` — 按控制器重置设备

---

#### POST `/build/controller/device/free` — 释放设备

**请求体 (JSON)**

```json
{
  "deviceId": 1,
  "device_identifier": "string (可选)"
}
```

---

#### GET `/build/controller/devices/by/controller` — 获取控制器下设备

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| macAddress | string | 是 | 控制器MAC地址 |

---

#### POST `/build/controller/device/running/heartbeat` — 设备运行心跳

**请求体 (JSON)**

```json
{
  "buildId": 1,
  "deviceId": 1
}
```

---

#### POST `/build/controller/cancel/device/build` — 取消设备构建

**请求体 (JSON)**

```json
{
  "buildId": 1,
  "macAddress": "string (可选)",
  "deviceId": 1
}
```

---

#### GET `/build/controller/device/detail` — 获取设备详情

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| deviceId | int | 是 | 设备ID |

---

#### GET `/build/controller/case/detail` — 获取项目用例详情

---

#### POST `/build/controller/sync/build/info` — 同步构建信息

**请求体 (JSON)**

```json
{
  "buildId": 1,
  "packageInfo": "string (包信息JSON)"
}
```

---

#### PUT `/build/controller/device/baseinfo` — 更新设备基础信息

**请求体 (JSON)**

```json
{
  "macAddress": "string (可选)",
  "deviceIp": "string (必填)",
  "baseinfo": "string (必填, 设备基础信息JSON)"
}
```

---

#### POST `/build/controller/reset/dispatch` — 重置调度

**请求体 (JSON)**

```json
{
  "buildId": 1,
  "deviceId": 1
}
```

---

#### PUT `/build/controller/device/pictureQuality` — 更新设备画质

**请求体 (JSON)**

```json
{
  "deviceId": 1,
  "pictureQuality": "string"
}
```

---

### 日志上传 `/build/logs`

#### POST `/build/logs/upload` — 上传日志

**请求体 (JSON)**

```json
{
  "projectId": "string (必填)",
  "caseId": "string (必填)",
  "buildId": "string (必填)",
  "deviceId": "string (可选)",
  "retryCount": "0",
  "loglevel": "INFO | DEBUG | WARNING | ERROR | CRITICAL | EXCEPTION",
  "log": "string (日志内容)"
}
```

---

#### POST `/build/logs/upload/logfile` — 上传日志文件

---

#### POST `/build/logs/upload/log/presigned` — 获取日志上传预签名URL

---

#### POST `/build/logs/upload/file` — 获取文件上传预签名URL

---

#### GET `/build/logs/download/presigned/urls` — 获取下载预签名URL

---

#### GET `/build/logs/v2/download/presigned/urls` — 获取下载预签名URL (v2)

---

### 对比分析 `/build/compare`

#### POST `/build/compare/tag/add` — 添加标签对比

**请求体 (JSON)**

```json
{
  "tagname": "string (必填)",
  "case_id": 1,
  "project_id": "string (必填)",
  "result": "string (可选, 描述)",
  "compareway": "string (必填, 对比方法)"
}
```

---

#### DELETE `/build/compare/tag/delete` — 删除标签对比

**请求体 (JSON)**

```json
{
  "project_id": "string (必填)",
  "tagname": "string (必填)"
}
```

---

#### POST `/build/compare/perfeye/add` — 添加Perfeye对比

**请求体 (JSON)**

```json
{
  "case_id": 1,
  "cookie": "string (必填)",
  "token": "string (必填, 飞书机器人地址)",
  "url": "string (必填)",
  "device_iden": "string (可选, 设备标识)"
}
```

---

#### POST `/build/compare/upload/image` — 上传对比图片

**请求体 (JSON)**

```json
{
  "url": "string (必填, 图片URL)",
  "project_id": "string (必填)",
  "tag_name": "string (必填)"
}
```

---

#### GET `/build/compare/tag_name/list` — 获取标签名列表

---

### 构建项目 `/build/project`

#### GET `/build/project/get/appkey/list` — 获取所有AppKey

---

### DevOps `/build/devops`

#### GET `/build/devops/pipeline/list` — 获取流水线列表

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |

---

#### GET `/build/devops/pipeline/execute/check` — 检查流水线运行状态

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| pipelineId | int | 是 | 流水线ID |

---

#### POST `/build/devops/package/management` — 添加应用管理

---

#### POST `/build/devops/remote/execute` — 远程执行流水线

---

#### GET `/build/devops/package/branches` — 获取分支列表

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| appKey | string | 是 | AppKey |

---

#### GET `/build/devops/package/buildType` — 获取构建类型

---

#### GET `/build/devops/package/appkey` — 获取AppKey列表

**请求参数 (Query)**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| projectId | string | 是 | 项目ID |
