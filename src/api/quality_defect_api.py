import datetime
import json
import uuid
import requests
from typing import Any, Optional

from an_copilot.framework.logging import an_logger
from fastapi import APIRouter
from pydantic import BaseModel, Field, Extra

from src.config import settings
from src.core.quality_defect.quality_defect_db import (
    save_quality_defect_output,
    append_quality_defect_output,
)

router = APIRouter()


class ResponseCommonEntity(BaseModel):
    status: bool
    message: Optional[str]
    output_data: Optional[dict[str, Any]]


class QualityDefectRequest(BaseModel):
    """
    质差定界派单请求模型

    支持接收框架从 BtreeContext 注入的动态字段
    """
    order_id: str = Field(default="", description="工单ID")
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    indicator_name: str = Field(default="", description="指标名称")
    threshold_type: str = Field(default="", description="阈值类型")
    threshold_rule: str = Field(default="", description="阈值规则")
    time_granularity: str = Field(default="", description="时间粒度")
    detection_period: str = Field(default="", description="检测周期")

    defect_count: int = Field(default=0, description="质差时段数")
    defect_periods_str: str = Field(default="", description="质差时段列表")
    has_defect: str = Field(default="", description="是否有质差时段")

    customer_level: str = Field(default="", description="客户等级")
    rule_name: str = Field(default="", description="预警规则名称")
    degradation_period: str = Field(default="", description="劣化监测周期")
    defect_threshold: int = Field(default=0, description="质差时段数阈值")
    alert_level_input: str = Field(default="", description="规则基础预警级别")

    is_alert_triggered: str = Field(default="", description="是否触发预警")
    alert_id: str = Field(default="", description="预警工单ID")
    alert_level: str = Field(default="", description="最终预警级别")
    alert_time: str = Field(default="", description="预警生成时间")
    trigger_condition: str = Field(default="", description="触发条件描述")
    alert_title: str = Field(default="", description="预警工单标题")

    defect_periods_overview: str = Field(default="", description="质差时段总览")
    customer_info: str = Field(default="", description="客户名称与等级")
    apn_name: str = Field(default="", description="APN名称")

    # --- 新增的流程控制与状态字段 ---
    has_error_code_mapping: str = Field(default="", description="是否配置错误码映射表 (是/否)")
    is_error_code_inconclusive: str = Field(default="", description="错误码定界无明确结论 (是/否)")

    error_code_conclusion: str = Field(default="", description="错误码定界结论")
    dimension_conclusion: str = Field(default="", description="维度定界结论")
    location_conclusion: str = Field(default="", description="定位结论")

    final_domain: str = Field(default="", description="最终定界专业")
    final_location: str = Field(default="", description="最终定位对象")

    agent_output: str = Field(default="", description="智能体输出文本")

    class Config:
        extra = Extra.allow


@router.post("/api/quality_defect/detect_anomaly", tags=["质差定界派单"])
async def quality_defect_detect_anomaly(req: QualityDefectRequest) -> ResponseCommonEntity:
    """
    节点①：质差识别检测
    """
    _begin_time = datetime.datetime.now()
    an_logger.info(f"[detect_anomaly] ========== 开始 ==========")
    an_logger.info(f"[detect_anomaly] 入口参数: order_id={req.order_id}, session_id={req.session_id}")

    try:
        data = _query_detect_anomaly_data(req.order_id)

        markdown_text = _build_detect_anomaly_markdown(data)
        an_logger.info(f"[detect_anomaly] 生成Markdown长度: {len(markdown_text)}")

        save_quality_defect_output(
            order_id=req.order_id,
            agent_output=markdown_text
        )

        has_defect = data.get('hasDefect', '否') == '是√'
        defect_count = data.get('defectCount', 0)

        _end_time = datetime.datetime.now()
        an_logger.info(f"[detect_anomaly] hasDefect={has_defect}, defectCount={defect_count}")
        an_logger.info(f"[detect_anomaly] 完成, 耗时: {(_end_time - _begin_time).total_seconds():.3f}s")
        an_logger.info(f"[detect_anomaly] ========== 结束 ==========")

        output_data = {
            "indicatorName": data.get('indicatorName', ''),
            "thresholdType": data.get('thresholdType', ''),
            "thresholdRule": data.get('thresholdRule', ''),
            "timeGranularity": data.get('timeGranularity', ''),
            "detectionPeriod": data.get('detectionPeriod', ''),
            "analysisList": data.get('analysisList', []),
            "hasDefect": data.get('hasDefect', '否'),
            "defectCount": defect_count,
            "defectPeriodsStr": data.get('defectPeriodsStr', ''),
            "agent_output": markdown_text,
        }

        return ResponseCommonEntity(
            status=has_defect,
            message="有质差时段" if has_defect else "无质差时段",
            output_data=output_data
        )
    except Exception as e:
        an_logger.error(f"[detect_anomaly] 异常: {e}", exc_info=True)
        return ResponseCommonEntity(
            status=False,
            message=f"检测失败: {str(e)}",
            output_data=None
        )


@router.post("/api/quality_defect/generate_anomaly_alert", tags=["质差定界派单"])
async def quality_defect_generate_anomaly_alert(req: QualityDefectRequest) -> ResponseCommonEntity:
    """
    节点②：质差预警与聚合
    """
    _begin_time = datetime.datetime.now()
    an_logger.info(f"[generate_anomaly_alert] ========== 开始 ==========")
    an_logger.info(f"[generate_anomaly_alert] 入口参数: order_id={req.order_id}, indicatorName={req.indicator_name}")

    try:
        data = _query_alert_data(req.order_id, req.indicator_name, req.defect_count, req.defect_periods_str)

        markdown_text = _build_alert_markdown(data)
        an_logger.info(f"[generate_anomaly_alert] 生成Markdown长度: {len(markdown_text)}")

        append_quality_defect_output(
            order_id=req.order_id,
            agent_output=markdown_text
        )

        is_alert_triggered = data.get('isAlertTriggered', '否') == '是√'

        _end_time = datetime.datetime.now()
        an_logger.info(f"[generate_anomaly_alert] isAlertTriggered={is_alert_triggered}")
        an_logger.info(f"[generate_anomaly_alert] 完成, 耗时: {(_end_time - _begin_time).total_seconds():.3f}s")
        an_logger.info(f"[generate_anomaly_alert] ========== 结束 ==========")

        output_data = {
            "indicatorName": data.get('indicatorName', ''),
            "defectCount": data.get('defectCount', 0),
            "customerLevel": data.get('customerLevel', ''),
            "ruleName": data.get('ruleName', ''),
            "degradationPeriod": data.get('degradationPeriod', ''),
            "defectThreshold": data.get('defectThreshold', 0),
            "alertLevelInput": data.get('alertLevelInput', ''),
            "isAlertTriggered": data.get('isAlertTriggered', '否'),
            "alertId": data.get('alertId', ''),
            "alertLevel": data.get('alertLevel', ''),
            "alertTime": data.get('alertTime', ''),
            "triggerCondition": data.get('triggerCondition', ''),
            "alertTitle": data.get('alertTitle', ''),
            "agent_output": markdown_text,
        }

        return ResponseCommonEntity(
            status=is_alert_triggered,
            message="触发预警" if is_alert_triggered else "不触发预警",
            output_data=output_data
        )
    except Exception as e:
        an_logger.error(f"[generate_anomaly_alert] 异常: {e}", exc_info=True)
        return ResponseCommonEntity(
            status=False,
            message=f"预警生成失败: {str(e)}",
            output_data=None
        )


@router.post("/api/quality_defect/execute_fault_localization", tags=["质差定界派单"])
async def quality_defect_execute_fault_localization(req: QualityDefectRequest) -> ResponseCommonEntity:
    """
    节点③：智能定界定位分析
    """
    _begin_time = datetime.datetime.now()
    an_logger.info(f"[execute_fault_localization] ========== 开始 ==========")
    an_logger.info(f"[execute_fault_localization] 入口参数: order_id={req.order_id}, alertId={req.alert_id}")

    try:
        data = _query_localization_data(req.order_id, req.alert_id, req.indicator_name, req.defect_periods_str)

        markdown_text = _build_localization_markdown(data)
        an_logger.info(f"[execute_fault_localization] 生成Markdown长度: {len(markdown_text)}")

        append_quality_defect_output(
            order_id=req.order_id,
            agent_output=markdown_text
        )

        final_domain = data.get('finalDomain', '')
        is_success = bool(final_domain)

        _end_time = datetime.datetime.now()
        an_logger.info(f"[execute_fault_localization] finalDomain={final_domain}")
        an_logger.info(f"[execute_fault_localization] 完成, 耗时: {(_end_time - _begin_time).total_seconds():.3f}s")
        an_logger.info(f"[execute_fault_localization] ========== 结束 ==========")

        output_data = {
            "alertId": data.get('alertId', ''),
            "indicatorName": data.get('indicatorName', ''),
            "defectPeriodsStr": data.get('defectPeriodsStr', ''),
            "customerInfo": data.get('customerInfo', ''),
            "apnName": data.get('apnName', ''),
            "hasErrorCodeMapping": data.get('hasErrorCodeMapping', ''),  # 新增透传
            "isErrorCodeInconclusive": data.get('isErrorCodeInconclusive', ''),  # 新增透传
            "errorCodeConclusion": data.get('errorCodeConclusion', ''),
            "dimensionConclusion": data.get('dimensionConclusion', ''),
            "locationConclusion": data.get('locationConclusion', ''),
            "finalDomain": final_domain,
            "finalLocation": data.get('finalLocation', ''),
            "agent_output": markdown_text,
        }

        return ResponseCommonEntity(
            status=is_success,
            message="定界成功" if is_success else "定界失败",
            output_data=output_data
        )
    except Exception as e:
        an_logger.error(f"[execute_fault_localization] 异常: {e}", exc_info=True)
        return ResponseCommonEntity(
            status=False,
            message=f"定界定位失败: {str(e)}",
            output_data=None
        )


def _query_detect_anomaly_data(order_id: str) -> dict:
    an_logger.info(f"[query_detect_anomaly_data] 正在调用接口查询质差检测数据，order_id: {order_id}")
    detect_url = settings.config.quality_defect_config.quality_defect_detect_url
    if not detect_url:
        return _mock_detect_anomaly_data(order_id)
    # ... 省略中间的标准HTTP请求逻辑，保持原样 ...
    return _mock_detect_anomaly_data(order_id)  # 兜底


def _query_alert_data(order_id: str, indicator_name: str, defect_count: int, defect_periods_str: str) -> dict:
    an_logger.info(f"[query_alert_data] 正在调用接口查询预警数据，order_id: {order_id}")
    alert_url = settings.config.quality_defect_config.quality_defect_alert_url
    if not alert_url:
        return _mock_alert_data(order_id, indicator_name, defect_count, defect_periods_str)
    # ... 省略中间的标准HTTP请求逻辑，保持原样 ...
    return _mock_alert_data(order_id, indicator_name, defect_count, defect_periods_str)  # 兜底


def _query_localization_data(order_id: str, alert_id: str, indicator_name: str, defect_periods_str: str) -> dict:
    an_logger.info(f"[query_localization_data] 正在调用接口查询定界定位数据，order_id: {order_id}, alert_id: {alert_id}")
    localization_url = settings.config.quality_defect_config.quality_defect_localization_url
    if not localization_url:
        return _mock_localization_data(order_id, alert_id, indicator_name, defect_periods_str)

    payload = {
        "order_id": str(order_id),
        "alert_id": alert_id,
        "indicator_name": indicator_name,
        "defect_periods_str": defect_periods_str,
    }
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(localization_url, headers=headers, data=json.dumps(payload), timeout=30)
        if response.status_code == 200:
            return response.json().get('data', {})
    except Exception as e:
        an_logger.error(f"[query_localization_data] 接口调用异常: {e}")

    return _mock_localization_data(order_id, alert_id, indicator_name, defect_periods_str)


def _build_detect_anomaly_markdown(data: dict) -> str:
    # ... 保持原样 ...
    indicator_name = data.get('indicatorName', '')
    threshold_type = data.get('thresholdType', '')
    threshold_rule = data.get('thresholdRule', '')
    time_granularity = data.get('timeGranularity', '')
    detection_period = data.get('detectionPeriod', '')
    analysis_list = data.get('analysisList', [])
    has_defect = data.get('hasDefect', '否')
    defect_count = data.get('defectCount', 0)
    defect_periods_str = data.get('defectPeriodsStr', '')

    table_rows = ""
    for item in analysis_list:
        stat_time = item.get('stat_time', '')
        metric_value = item.get('metric_value', '')
        threshold_val = item.get('threshold_val', '')
        is_defect = item.get('is_defect', '否')
        is_defect_display = f'<font color="red">{is_defect}</font>' if is_defect == '是√' else is_defect
        table_rows += f"| {stat_time} | {metric_value} | {threshold_val} | {is_defect_display} |\n"

    return f"""### ① 质差识别

— 输入数据 —
* 指标名称：{indicator_name}
* 阈值类型：{threshold_type}
* 阈值规则：{threshold_rule}
* 时间粒度：{time_granularity}
* 检测周期：{detection_period}

— 分析过程 —
| 时段 | 指标值 | 阈值 | 是否质差 |
| :--- | :--- | :--- | :--- |
{table_rows}
— 输出结果 —
* 是否有质差时段：{has_defect}
* 质差时段数：{defect_count}个
* 质差时段列表：{defect_periods_str}
"""


def _build_alert_markdown(data: dict) -> str:
    # ... 保持原样 ...
    return f"""
### ② 质差预警

— 输入数据 —
* 指标名称：{data.get('indicatorName', '')}
* 质差时段数：{data.get('defectCount', 0)}个
* 预警规则名称：{data.get('ruleName', '')}
* 劣化监测周期：{data.get('degradationPeriod', '')}
* 质差时段数阈值：{data.get('defectThreshold', 0)}
* 预警级别：{data.get('alertLevelInput', '')}
* 客户级别：{data.get('customerLevel', '')}

— 输出结果 —
* 是否触发预警：{data.get('isAlertTriggered', '否')}
* 预警ID：{data.get('alertId', '')}
* 预警级别：{data.get('alertLevel', '')}
* 预警时间：{data.get('alertTime', '')}
* 触发条件：{data.get('triggerCondition', '')}
* 预警标题：{data.get('alertTitle', '')}
"""


def _build_localization_markdown(data: dict) -> str:
    """
    根据后端直接返回的判定字段，动态构建符合流程图逻辑的 Markdown 文本
    """
    alert_id = data.get('alertId', '')
    indicator_name = data.get('indicatorName', '')
    defect_periods_str = data.get('defectPeriodsStr', '')
    customer_info = data.get('customerInfo', '')
    apn_name = data.get('apnName', '')

    # 获取后端穿透回来的控制字段
    has_mapping = data.get('hasErrorCodeMapping', '否')
    is_inconclusive = data.get('isErrorCodeInconclusive', '是')

    error_code_conclusion = data.get('errorCodeConclusion', '')
    dimension_conclusion = data.get('dimensionConclusion', '')
    location_conclusion = data.get('locationConclusion', '')
    final_domain = data.get('finalDomain', '')
    final_location = data.get('finalLocation', '')

    # 动态组装阶段1文本 (对应菱形判断：指标是否配置错误码映射表？)
    if has_mapping == '否':
        stage1_text = f"⊙ **错误码定界** ➝ 未配置错误码映射表，跳过此阶段。"
        stage2_prefix = ""
    else:
        stage1_text = f"⊙ **错误码定界** ➝ {error_code_conclusion}"
        # 对应菱形判断：错误码无明确结论？
        if is_inconclusive == '是':
            stage1_text += "\n  ↳ *注：错误码无明确结论，继续执行聚类定界分析。*"
            stage2_prefix = ""
        else:
            stage1_text += "\n  ↳ *注：某专业维度占比 ≥ 40%，直接定界到该专业！*"
            stage2_prefix = "*(基于阶段1结论，跳过聚类)* "  # 如果阶段1已经有明确结论，通常跳过聚类

    markdown_text = f"""
### ③ 定界定位

— 输入数据 —
* 预警详情：
  * 预警ID：{alert_id}
  * 指标：{indicator_name}
  * 质差时段：{defect_periods_str}
  * 客户：{customer_info}
  * APN：{apn_name}

— 分析过程 —
<font color="#4a90e2">**阶段1：错误码定界**</font>
{stage1_text}

<font color="#4a90e2">**阶段2：聚类及关联分析**</font>
⊙ **维度定界** ➝ {stage2_prefix}{dimension_conclusion}

<font color="#4a90e2">**阶段3：定位对象**</font>
⊙ **具体定位** ➝ {location_conclusion}

— 输出结果 —
* 定界专业：{final_domain}
* 定位：{final_location}
"""
    return markdown_text


def _mock_detect_anomaly_data(order_id: str) -> dict:
    return {
        "indicatorName": "寻呼成功率",
        "thresholdType": "静态阈值",
        "thresholdRule": "93%",
        "timeGranularity": "小时",
        "detectionPeriod": "6小时",
        "analysisList": [
            {"stat_time": "2026-01-28 10:00", "metric_value": "94.50%", "threshold_val": "93%", "is_defect": "否"},
            {"stat_time": "2026-01-28 11:00", "metric_value": "89.50%", "threshold_val": "93%", "is_defect": "是√"},
            {"stat_time": "2026-01-28 12:00", "metric_value": "92.80%", "threshold_val": "93%", "is_defect": "否"},
            {"stat_time": "2026-01-28 13:00", "metric_value": "88.20%", "threshold_val": "93%", "is_defect": "是√"},
        ],
        "hasDefect": "是√",
        "defectCount": 2,
        "defectPeriodsStr": "2026-01-28 11:00、2026-01-28 13:00"
    }


def _mock_alert_data(order_id: str, indicator_name: str, defect_count: int, defect_periods_str: str) -> dict:
    return {
        "indicatorName": indicator_name or "寻呼成功率",
        "defectCount": defect_count or 2,
        "customerLevel": "金牌",
        "ruleName": "连续质差触发预警规则",
        "degradationPeriod": "6小时",
        "defectThreshold": 2,
        "alertLevelInput": "重要",
        "isAlertTriggered": "是√",
        "alertId": "WARN-2026012804",
        "alertLevel": "重要",
        "alertTime": "2026-01-28 16:30:00",
        "triggerCondition": "连续3个周期质差",
        "alertTitle": "寻呼成功率质差触发预警"
    }


def _mock_localization_data(order_id: str, alert_id: str, indicator_name: str, defect_periods_str: str) -> dict:
    """返回模拟的定界定位数据"""
    return {
        "alertId": alert_id or "WARN-2026012804",
        "indicatorName": indicator_name or "寻呼成功率",
        "defectPeriodsStr": defect_periods_str or "2个 (11:00/13:00)",
        "customerInfo": "广汽汽车集团（金牌）",
        "apnName": "SCCAR.GD",

        # 新增模拟的控制字段，模拟“配了映射表，但错误码分布较散”的情况
        "hasErrorCodeMapping": "是",
        "isErrorCodeInconclusive": "是",

        "errorCodeConclusion": "核心网占比15%，无线网占比25%，错误原因分布较散",
        "dimensionConclusion": "执行聚类及横向比对分析后，定界到无线网",
        "locationConclusion": "定位疑似 小区ID 68272912 存在拥塞问题",
        "finalDomain": "无线网",
        "finalLocation": "疑似 小区ID 68272912 存在问题"
    }