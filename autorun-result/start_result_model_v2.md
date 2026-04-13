# {YYYY.MM.DD}《星砂岛物语》稳定性汇总

## 一、PC（共{N}台设备，其中{M}台执行超过4小时）
{for each version in pc_versions}
- （版本：{version_number}）
{for each task in version.tasks}
  - {task_index}.[{task_name}]({task_url}) 任务执行汇总：**共{task_device_count}台** 设备，其中 **{task_over_4h_count}台** 设备执行超过4小时，{abnormal_info}
{end}
{end}

## 二、Xbox（共{N}台设备，其中{M}台执行超过4小时）
{for each version in xbox_versions}
- （版本：{version_number}）
{for each task in version.tasks}
  - {task_index}.[{task_name}]({task_url}) 任务执行汇总： **共{task_device_count}台** 设备，其中 **{task_over_4h_count}台** 设备执行超过4小时，{abnormal_info}
{end}
{end}

## 三、PS5（共{N}台设备，其中{M}台执行超过4小时）
{for each version in ps5_versions}
- （版本：{version_number}）
{for each task in version.tasks}
  - {task_index}.[{task_name}]({task_url}) 任务执行汇总：**共{task_device_count}台** 设备，其中 **{task_over_4h_count}台** 设备执行超过4小时，{abnormal_info}
{end}
{end}

## 四、Switch（共{N}台设备，其中{M}台执行超过4小时）
{for each version in switch_versions}
- （版本：{version_number}）
{for each task in version.tasks}
  - {task_index}.[{task_name}]({task_url}) 任务执行汇总：**共{task_device_count}台** 设备，其中 **{task_over_4h_count}台** 设备执行超过4小时，{abnormal_info}
{end}
{end}

---

**📊 总体统计**：
- **平台覆盖**：{covered_platforms}/{total_platforms}（全部平台有测试）
- **总设备数**：{total_devices}台
- **执行超过4小时设备**：{over_4h_devices}台（{percentage}%）
- **异常设备**：{abnormal_devices}台

**📈 今日亮点**：
- {highlight_1}
- {highlight_2}
- {highlight_3}

**🔍 注意事项**：
- {note_1}
- {note_2}
- {note_3}

---

*报告生成时间：{generation_time}*

**使用说明**：
1. 将占位符 {xxx} 替换为实际数据
2. 平台顺序固定为：PC → Xbox → PS5 → Switch
3. 异常信息格式：`未发现异常` 或 `以下{X}台出现异常` + 异常详情
4. 链接格式：[任务名称](URL)
5. 百分比计算：(超4小时设备数 ÷ 总设备数) × 100%

**数据源**：自动化测试平台 (uauto2.testplus.cn)
**统计标准**：执行时长 ≥ 4小时（14400秒）为达标