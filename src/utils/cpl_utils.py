import re
import uuid

import requests
import json
import os
from an_copilot.framework.logging import an_logger

from src.config import settings


def process_order_request_task(order_id: str, req_info: dict, order_info: dict | None = None):
    """
    单独处理工单请求的任务
    :param order_id: 工单ID
    :param req_info: 请求信息
    :param order_info: 已查询到的工单详情
    """
    try:
        # 经纬度优先使用 order_info 的字段，其次回落到前端透传的 req_info
        def _pick_coord(val):
            if val is None:
                return None
            try:
                v = float(val)
                return v if v != 0 else None
            except Exception:
                return None

        lon = _pick_coord(order_info.get("eoms_longitude") if order_info else None) or _pick_coord(req_info.get("longitude"))
        lat = _pick_coord(order_info.get("eoms_latitude") if order_info else None) or _pick_coord(req_info.get("latitude"))

        if lon is None or lat is None:
            # 没有有效经纬度就不发起无效请求，便于定位问题
            an_logger.warning(f"process_order_request_task skip: missing lon/lat for order {order_id}, req_info: {req_info}, order_info: {order_info}")
            return

        message_request = {
            "query": f"查询{order_id}工单",
            "longitude": lon,
            "latitude": lat,
            "response_mode": "blocking",
            "session_id": req_info.get('session_id'),
            "request_id": str(uuid.uuid4()),
            "user": req_info.get('user'),
            "is_history": '1',
            # 附带已有工单信息，方便下游直接复用
            "order_info": order_info or {},
        }

        url = f"{settings.config.common_agent_config.net_opt_url}/v4/api/compthdlchats"
        response = requests.post(url, json=message_request, timeout=600,verify=False)
        an_logger.info(f"process_order_request_task req： {order_id}, res: {response.json()}")
    except Exception as e:
        an_logger.error(f"Exception in _process_order_request_task for order {order_id}: {str(e)}")



def remove_thinking_tags(content: str) -> str:
    return re.sub(r"<think>[\s\S]*?</think>", "", content)


def send_complaint_result_to_wireless(kf_work_order_id: str, process_content: str,
                                       complaint_type: str = "2", status: bool = True):
    """
    发送投诉处理结果到现场
    Args:
        kf_work_order_id: 省客服流水号
        process_content: 处理结果内容
        complaint_type: 类型，1-投诉处理
        status: 状态，True/False
    """
    try:
        # 现场接口地址
        api_url = os.getenv('WIRELESS_API_URL') or settings.config.complaint_agent_config.srd_received_api_url
        # 构建请求报文
        request_data = {
            "kfWorkOrderId": kf_work_order_id,
            "type": complaint_type,
            "status": status,
            "processContent": process_content
        }

        an_logger.info(f"准备发送投诉处理结果到无线网优: {json.dumps(request_data, ensure_ascii=False)}")

        # 发送请求
        response = requests.post(
            api_url,
            json=request_data,
            headers={'Content-Type': 'application/json'},
            timeout=30,
            verify=False
        )

        if response.status_code == 200:
            resp_data = response.json()
            an_logger.info(f"无线网优接口响应: {json.dumps(resp_data, ensure_ascii=False)}")
            if resp_data.get('code') == 0:
                an_logger.info(f"投诉处理结果发送成功: {kf_work_order_id}")
                return True
            else:
                an_logger.error(f"投诉处理结果发送失败: {resp_data.get('msg')}")
                return False
        else:
            an_logger.error(f"无线网优接口请求失败: HTTP {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        an_logger.error(f"无线网优接口请求异常: {str(e)}")
        return False
    except Exception as e:
        an_logger.error(f"发送投诉处理结果异常: {str(e)}")
        return False
