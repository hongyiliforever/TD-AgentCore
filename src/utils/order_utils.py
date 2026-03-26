from datetime import datetime
from json.decoder import JSONDecodeError
import uuid
import requests
from an_copilot.framework.logging import an_logger as logger
from dateutil import parser
from concurrent.futures import ThreadPoolExecutor
import threading

from src.config import settings


def normalize_time(time_value):
    """
    将时间值转换为统一的格式：YYYY-MM-DD HH:MM:SS
    支持以下格式：
    - 日期时间字符串：Wed Apr 02 08:56:49 CST 2025
    - 毫秒级时间戳：1744942688000
    - 秒级时间戳：1744942688
    - ISO 8601 格式：2025-04-02 08:56:48
    """
    if not time_value:
        return None

    try:
        # 尝试解析为毫秒级时间戳
        if isinstance(time_value, int) or (isinstance(time_value, str) and time_value.isdigit()):
            time_value = int(time_value)
            if time_value > 1e10:  # 毫秒级时间戳
                time_value /= 1000
            dt = datetime.utcfromtimestamp(time_value)
        else:
            # 尝试解析为日期时间字符串
            try:
                dt = parser.parse(time_value)
            except ValueError:
                try:
                    dt = datetime.strptime(time_value, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    logger.warning(f"无法解析时间值: {time_value}")
                    return None
    except (ValueError, TypeError):
        logger.warning(f"无法解析时间值: {time_value}")
        return None
    date_strftime = dt.strftime("%Y-%m-%d %H:%M:%S")
    return date_strftime


def convert_deal_result(deal_result_code):
    """
    将dealResult编码转换为中文描述
    处理结果   0已解决 1暂无法解决 2计划解决
    参数:
        deal_result_code: 原始dealResult编码（字符串或数字）

    返回:
        str: 对应的中文描述，若编码未匹配则返回原始值
    """
    # 定义编码与中文映射关系
    DEAL_RESULT_MAPPING = {
        "0": "已解决",
        "1": "暂无法解决",
        "2": "计划解决",
    }

    # 统一转换为字符串处理，兼容各种输入类型
    if deal_result_code is None:
        return deal_result_code

    code_str = str(deal_result_code).strip()

    # 查找映射，未匹配则返回原始值
    return DEAL_RESULT_MAPPING.get(code_str, code_str)


def get_work_order_types(is_important_str, complain_times_str):
    """
    判断工单性质并返回所有符合条件的类型，接收字符串类型输入

    参数:
    is_important_str: 字符串形式的"0"或"1"，表示工单是否重要
    complain_times_str: 字符串形式的整数，表示投诉次数

    返回:
    list: 工单性质列表，可能包含"普通工单"、"重要工单"、"重复投诉工单"
    """
    types = []

    try:
        # 将字符串转换为相应的数值类型
        is_important = int(is_important_str)
        complain_times = int(complain_times_str)

        # 判断是否为重复投诉工单
        if complain_times > 0:
            types.append("重复投诉工单")

        # 判断是重要工单还是普通工单
        if is_important == 1:
            types.append("重要工单")
        else:
            types.append("普通工单")

    except ValueError:
        # 处理转换失败的情况
        types.append("输入格式错误，请输入有效的数字字符串")

    return "、".join(types)

def get_order_alarm_info(cell_input):
    """
    获取投诉工单的根因分析中业务告警分析信息
    """
    try:
        # 构建请求URL
        base_url = settings.config.common_agent_config.complaint_order_url
        url = f"{base_url}/analysis/alarm"
        # 准备请求参数
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        logger.info(f"开始查询信息，工单ID: {cell_input}，请求URL: {url}")
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        verify_ssl = False if parsed_url.scheme == "https" else True
        # 发送请求，设置超时时间防止无限等待
        response = requests.post(
            url,
            headers=headers,
            json=cell_input,
            timeout=600,
            verify=verify_ssl
        )
        # 检查HTTP状态码
        response.raise_for_status()
        # 解析JSON响应
        try:
            response_json = response.json()
            logger.info(f"查询响应: {response_json}")
        except JSONDecodeError as e:
            logger.error(f"响应JSON解析失败: {str(e)}，响应内容: {response.text}")
            return None
        # 检查响应状态和数据结构
        if not response_json.get("status", False):
            error_msg = response_json.get("message", "未知错误")
            logger.error(f"查询失败: {error_msg} ")
            return None
        # 提取投诉描述
        output_data_list = response_json.get("output_data", {})
        return output_data_list
    except Exception as e:
        # 处理其他未预期异常
        logger.error(f"获取告警信息时发生未知错误错误: {str(e)}", exc_info=True)
        return None

def get_order_info(order_id)-> dict :
    """
    获取工单信息中的投诉描述

    :param order_id: 工单ID
    :return: 投诉描述字符串，如果获取失败返回None
    """
    if not order_id:
        logger.error("工单ID不能为空")
        return None

    try:
        # 构建请求URL
        base_url = settings.config.common_agent_config.complaint_order_url
        url = f"{base_url}/complaint/queryOrderByWoId"

        # 准备请求参数
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        data = {"woId": order_id}

        logger.info(f"get_order_info order_id: {order_id}，请求URL: {url}")

        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        verify_ssl = False if parsed_url.scheme == "https" else True
        # 发送请求，设置超时时间防止无限等待
        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=600,
            verify=verify_ssl
        )

        # 检查HTTP状态码
        response.raise_for_status()

        # 解析JSON响应
        try:
            response_json = response.json()
            logger.info(f"工单查询响应: {response_json}")
        except JSONDecodeError as e:
            logger.error(f"响应JSON解析失败: {str(e)}，响应内容: {response.text}")
            return  {}

        # 检查响应状态和数据结构
        if not response_json.get("success", False):
            error_msg = response_json.get("message", "未知错误")
            logger.error(f"工单查询失败: {error_msg}，工单ID: {order_id}")
            return  {}

        # 提取投诉描述
        data_list = response_json.get("data", [])
        if not data_list:
            logger.warning(f"get_order_info 工单ID {order_id} 未找到对应数据")
            return  {}

        if len(data_list) > 1:
            logger.warning(f"get_order_info 工单ID {order_id} 返回多条数据，仅使用第一条")

        return data_list[0]
    except Exception as e:
        # 处理其他未预期异常
        logger.error(f"get_order_info 获取工单信息时发生未知错误，工单ID: {order_id}，错误: {str(e)}", exc_info=True)
        return {}


def get_total_cell( cell_input):
    """
    获取工单信息中的投诉描述

    :param order_id: 工单ID
    :return: 投诉描述字符串，如果获取失败返回None
    """

    try:
        # 构建请求URL
        base_url = settings.config.common_agent_config.complaint_order_url
        url = f"{base_url}/complaint/queryTotalCell"

        # 准备请求参数
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        logger.info(f"开始查询信息，工单ID: {cell_input}，请求URL: {url}")
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        verify_ssl = False if parsed_url.scheme == "https" else True
        # 发送请求，设置超时时间防止无限等待
        response = requests.post(
            url,
            headers=headers,
            json=cell_input,
            timeout=600,
            verify=verify_ssl
        )

        # 检查HTTP状态码
        response.raise_for_status()

        # 解析JSON响应
        try:
            response_json = response.json()
            logger.info(f"查询响应: {response_json}")
        except JSONDecodeError as e:
            logger.error(f"响应JSON解析失败: {str(e)}，响应内容: {response.text}")
            return None

        # 检查响应状态和数据结构
        if not response_json.get("success", False):
            error_msg = response_json.get("message", "未知错误")
            logger.error(f"查询失败: {error_msg} ")
            return None

        # 提取投诉描述
        data_list = response_json.get("data", {})

        return data_list
    except Exception as e:
        # 处理其他未预期异常
        logger.error(f"获取信息时发生未知错误错误: {str(e)}", exc_info=True)
        return None



def get_complaint_category(order_id,cpl_info):
    """
    获取工单分类

    :param order_id: 工单ID
    :return: 投诉描述字符串，如果获取失败返回None
    """
    defult_category = {'complaint_category': '网速慢卡顿断线'}
    if not order_id:
        logger.error("工单ID不能为空")
        return defult_category

    try:
        # 构建请求URL
        base_url = settings.config.common_agent_config.order_category_url
        url = f"{base_url}/api/get-complaint-category"

        # 准备请求参数
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        data = {
            "order_id": order_id,
            "cpl_info": cpl_info
        }

        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        verify_ssl = False if parsed_url.scheme == "https" else True
        # 发送请求，设置超时时间防止无限等待
        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=600,
            verify=verify_ssl
        )

        response.raise_for_status()
        # 解析JSON响应
        try:
            response_json = response.json()
            logger.info(f"get_complaint_category查询响应: {response_json}")
        except JSONDecodeError as e:
            logger.error(f"响应JSON解析失败: {str(e)}，响应内容: {response.text}")
            return defult_category
        if not response_json.get("status", False):
            error_msg = response_json.get("message", "未知错误")
            logger.error(f"查询失败: {error_msg}，工单ID: {order_id}")
            return defult_category
        output_data = response_json.get("output_data", {})

        return output_data
    except Exception as e:
        # 处理其他未预期异常
        logger.error(f"获取工单分类: {order_id}，错误: {str(e)}", exc_info=True)
        return defult_category



# 创建线程池用于异步执行
_thread_pool = ThreadPoolExecutor(max_workers=5, thread_name_prefix="dialog_history")

def _save_dialog_history_sync(__begin_time, req_info, session_id, request_id, res_out):
    """
    同步保存对话历史数据的内部方法
    """
    try:
        agent_output = {
            "skill_param_ready": False,
            "skill_param": {},
            "data_list": [{
                "ui_type": "Text",
                "columns": [
                    {
                        "indicator_name": "提示说明",
                        "indicator_id": "text",
                        "indicator_code": "text",
                        "value_type": "string"
                    }
                ],
                "records": [{
                    "text": res_out
                }]
            }],
        }
        url = settings.config.common_agent_config.complaint_history_url + "/dialog/save/history"
        logger.info(f"Dialog history start {url}, session_id: {session_id}, request_id: {request_id}")
        
        # 准备发送给Java服务的参数
        __end_time = datetime.now()
        total_ms = (__end_time - __begin_time).total_seconds() * 1000
        total_seconds = round(total_ms, 3)
        dialog_history_data = {
            "http_type": "websocket",
            "answer": agent_output,
            "answer_time": __end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "business_name": "copilot",
            "question": req_info['query'],
            "question_time": __begin_time.strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_time": int(total_seconds),
            "session_id": session_id,
            "request_id": request_id,
            "user": req_info['user']
        }
      
        headers = {'Content-Type': 'application/json; charset=utf-8', 'Token': 'ccbcc0e8c81c48ecb8577f53cd0a5ba2'}

        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        verify_ssl = False if parsed_url.scheme == "https" else True
        # 发送请求，设置超时时间防止无限等待
        response = requests.post(
            url,
            headers=headers,
            json=dialog_history_data,
            timeout=600,
            verify=verify_ssl
        )

        response.raise_for_status()
        response_json = response.json()
        logger.info(f"Dialog history saved successfully: {response_json}")
        
    except Exception as e:
        logger.error(f"Failed to save dialog history for session {session_id}, request {request_id}: {str(e)}")


def dialog_history_data(__begin_time, req_info, session_id, request_id, res_out):
    """
    异步保存对话历史数据
    
    Args:
        __begin_time: 开始时间
        req_info: 请求信息字典
        session_id: 会话ID
        request_id: 请求ID
        res_out: 响应输出内容
    
    Returns:
        Future: 异步执行的Future对象，可用于获取执行结果或取消执行
    """
    try:
        # 提交到线程池异步执行
        future = _thread_pool.submit(
            _save_dialog_history_sync,
            __begin_time,
            req_info,
            session_id,
            request_id,
            res_out
        )
        logger.info(f"Dialog history save task submitted asynchronously for session: {session_id}, request: {request_id}")
        return future
        
    except Exception as e:
        logger.error(f"Failed to submit dialog history save task: {str(e)}")
        return None





#
if __name__ == '__main__':
    # desc = "13789019886问题号码使用手机上网（4G），出现问题的时间2024-07-03 21:28:25，故障表现有信号全部网站、游戏、视频、APP等软件无法使用，出现问题的地点长沙市望城区铜官镇，换机换卡测试情况，周围用户上网情况，客户要求联系电话 剩余流量:62GB930.57MB 可用余额:59.27元 套餐列表:套餐名称:30GB移动云盘定向流量免费服务,总流量:30720.00MB,剩余流量:30720.00MB 套餐名称:全家享套餐99元档（家庭共享）,总流量:20480.00MB,剩余流量:20101.59MB 套餐名称:全家享套餐99元档(6月结转),总流量:13596.99MB,剩余流量:13596.98MB 状态正常  ———>请问您是使用WIFI上网还是流量上网? : 数据流量上网 ———> 请问您上网出现了什么问题? : 无法上网 ———> 客户状态:正常 ———> 4G开通状态:已开通(网络侧:已开通|BOSS:未获取) ———> 4G注册状态:注册成功 ———> 是否限速:未限速(网络侧未限速、BOSS侧未限速) ———> 是否低流量低话费:话费流量正常 ———> 请问您上网开关是否打开? : 已打开 ———> 请问您是所有地方还是某个地方出现上网慢的问题? : 所有地点 ———> 查询否为4G终端:支持 ———> 询问客户是否换机换卡? : 换过未恢复 ———> 原因场景:终端-疑似终端问题 ———> 是否重复来电:是 重复来电次数:1 本次位置清除:否 网格:丁字网格%% 客户方便联系时间:2024-07-03 21:28:46 无线感知平台信息: 弱覆盖小区 否 高负荷预警小区 否 高干扰小区 是 低接通小区 是 高掉线小区 否 低切换成功率小区 是 语音低接通小区 否 语音高掉话小区 否 严重故障小区 否 严重故障告警 无 质差事件信息：质差地市: 质差时间: 质差事件: 质差原因:"
    # get_complaint_category('111',desc)

    # str = '地市 :AI: 指标名称: 差感小区清单, 地市: , 时间: 2023年6月30号。'
    # cell_info = {
    #     "msisdn": "15873128229",
    #     "cityName": "长沙",
    #     "lon": "113.030920",
    #     "lat": "28.153090"
    # }
    # print(get_total_cell(cell_info))
    # print(get_config_value('aap_check_result_key'))
    # da = get_use_cache()
    # print(bool(da)==da)

    # 测试异步调用
    # future = dialog_history_data(
    #     datetime.now(),
    #     req,
    #     str(uuid.uuid4()),
    #     str(uuid.uuid4()),
    #     out
    # )
    # print(f"异步任务已提交: {future}")

    out = """
    ### 意图识别
投诉工单编号 HN-1-240523-0002，识别工单信息如下：
 投诉时间：2024-07-03 21:28:25
投诉用户：13789019886
投诉地点：长沙市望城区铜官镇
投诉问题分类：区域无信号
### 任务规划
针对用户投诉问题，归类为区域无信号。
基于此问题的处理目标，调用知识库，经大模型推理输出问题处理流程如下：
1、获取周边小区：查询投诉点周边小区及常驻小区；
2、业务告警分析：查询小区告警数据，识别是否存在影响业务的告警名称；
3、小区覆盖分析：查询小区覆盖指标，识别是否存在弱覆盖、重叠覆盖、SINR质差等问题；
4、栅格覆盖分析：根据投诉点的经纬度，获取投诉点周边50米栅格、50米栅格（3*3）、50米栅格（5*5）的覆盖指标，并判断是否存在弱覆盖、竞对分析结果；
5、小区干扰分析：查询小区干扰指标，识别是否存在高干扰问题；
6、分析报告输出：基于用户投诉内容，及指标分析结果，输出当前投诉工单的分析报告。

### 任务执行
#### 问题分析
1. 业务告警分析
投诉位置周边共1个小区出现告警，分析影响业务告警名称，共2条，涉及1个小区
```json
{
    "business_name": "complaint_intelligent",
    "module_name": "alarm_history",
    "period_type": "day",
    "region_type": "cell",
    "start_time": "2024-07-03 21:28:25",
    "end_time": "2024-07-03 23:59:59",
    "alarmtitles": [
        "射频单元时钟异常告警"
    ]
}
```

2. 覆盖问题分析
分析投诉位置周边小区的覆盖指标，发现共有1个小区出现覆盖问题；
当前位置所在栅格未发现覆盖问题：
```json
{
    "business_name": "complaint_intelligent",
    "module_name": "load_kpi_detail",
    "period_type": "hour",
    "region_type": "cell",
    "indicator_network_types": [
        "4G"
    ],
    "start_time": "2024-07-03 21:28:25",
    "end_time": "2024-07-03 23:59:59",
    "encis": [
        "10387734550",
        "10387734551",
        "10387734559",
        "10387804187",
        "10387804188",
        "10387804189",
        "118066195",
        "118066203",
        "118066204",
        "118078993",
        "118078994",
        "118078995",
        "118078978",
        "13795972",
        "13795973",
        "13795975",
        "13795982",
        "13795983",
        "13795987",
        "13795988",
        "13795989",
        "13795992",
        "10387931163",
        "118066195"
    ]
}
```

3. 负荷问题分析
分析投诉位置周边小区的负荷指标，发现共有1个小区出现高负荷问题，其中上高1个，下高0个，双高0个。
```json
{
    "business_name": "complaint_intelligent",
    "module_name": "load_kpi_detail",
    "period_type": "hour",
    "region_type": "cell",
    "indicator_network_types": [
        "4G"
    ],
    "start_time": "2024-07-03 21:28:25",
    "end_time": "2024-07-03 23:59:59",
    "encis": [
        "10387734550",
        "10387734551",
        "10387734559",
        "10387804187",
        "10387804188",
        "10387804189",
        "118066195",
        "118066203",
        "118066204",
        "118078993",
        "118078994",
        "118078995",
        "118078978",
        "13795972",
        "13795973",
        "13795975",
        "13795982",
        "13795983",
        "13795987",
        "13795988",
        "13795989",
        "13795992",
        "10387931163",
        "118066195"
    ]
}
```

4. 干扰问题分析
分析投诉位置周边小区的干扰指标，发现共有1个小区出现高干扰问题。
```json
{
    "business_name": "complaint_intelligent",
    "module_name": "interference_kpi",
    "period_type": "hour",
    "region_type": "cell",
    "indicator_network_types": [
        "4G"
    ],
    "start_time": "2024-07-03 21:28:25",
    "end_time": "2024-07-03 23:59:59",
    "encis": [
        "10387734550",
        "10387734551",
        "10387734559",
        "10387804187",
        "10387804188",
        "10387804189",
        "118066195",
        "118066203",
        "118066204",
        "118078993",
        "118078994",
        "118078995",
        "118078978",
        "13795972",
        "13795973",
        "13795975",
        "13795982",
        "13795983",
        "13795987",
        "13795988",
        "13795989",
        "13795992",
        "10387931163",
        "118066195"
    ]
}
```

#### 优化建议
1. 业务告警方案
长沙榔梨镇土岭社区土岭一队HF-D3900461802PT-13存在2个影响业务的告警，需要优先处理。

2. 覆盖问题方案
【弱覆盖】：长沙榔梨镇土岭社区土岭一队HF-D3900461802PT-13存在弱覆盖问题，建议优先调整小区功率参数，提升信号强度，其次可核查方位角、下倾角等参数，增强目标区域覆盖；

3. 负荷问题方案
长沙榔梨镇土岭社区土岭一队HF-D3900461802PT-13高负荷为上高 ，LTE共站小区长沙天心中南林科大综合实验楼、国际学院HL-D3900394567TF-92

4. 干扰问题方案
长沙榔梨镇土岭社区土岭一队HF-D3900461802PT-13存在高干扰，需尽快排查干扰源。
### 报告输出
**智能报告输出**
####  基本信息
投诉时间：2024-07-03 21:28:25
投诉用户：13789019886
投诉地点：长沙市望城区铜官镇
投诉问题分类：区域无信号

#### 问题分析
1. 业务告警分析
投诉位置周边共1个小区出现告警，分析影响业务告警名称，共2条，涉及1个小区
```json
{
    "business_name": "complaint_intelligent",
    "module_name": "alarm_history",
    "period_type": "day",
    "region_type": "cell",
    "start_time": "2024-07-03 21:28:25",
    "end_time": "2024-07-03 23:59:59",
    "alarmtitles": [
        "射频单元时钟异常告警"
    ]
}
```

2. 覆盖问题分析
分析投诉位置周边小区的覆盖指标，发现共有1个小区出现覆盖问题；
当前位置所在栅格未发现覆盖问题：
```json
{
    "business_name": "complaint_intelligent",
    "module_name": "load_kpi_detail",
    "period_type": "hour",
    "region_type": "cell",
    "indicator_network_types": [
        "4G"
    ],
    "start_time": "2024-07-03 21:28:25",
    "end_time": "2024-07-03 23:59:59",
    "encis": [
        "10387734550",
        "10387734551",
        "10387734559",
        "10387804187",
        "10387804188",
        "10387804189",
        "118066195",
        "118066203",
        "118066204",
        "118078993",
        "118078994",
        "118078995",
        "118078978",
        "13795972",
        "13795973",
        "13795975",
        "13795982",
        "13795983",
        "13795987",
        "13795988",
        "13795989",
        "13795992",
        "10387931163",
        "118066195"
    ]
}
```

3. 负荷问题分析
分析投诉位置周边小区的负荷指标，发现共有1个小区出现高负荷问题，其中上高1个，下高0个，双高0个。
```json
{
    "business_name": "complaint_intelligent",
    "module_name": "load_kpi_detail",
    "period_type": "hour",
    "region_type": "cell",
    "indicator_network_types": [
        "4G"
    ],
    "start_time": "2024-07-03 21:28:25",
    "end_time": "2024-07-03 23:59:59",
    "encis": [
        "10387734550",
        "10387734551",
        "10387734559",
        "10387804187",
        "10387804188",
        "10387804189",
        "118066195",
        "118066203",
        "118066204",
        "118078993",
        "118078994",
        "118078995",
        "118078978",
        "13795972",
        "13795973",
        "13795975",
        "13795982",
        "13795983",
        "13795987",
        "13795988",
        "13795989",
        "13795992",
        "10387931163",
        "118066195"
    ]
}
```

4. 干扰问题分析
分析投诉位置周边小区的干扰指标，发现共有1个小区出现高干扰问题。
```json
{
    "business_name": "complaint_intelligent",
    "module_name": "interference_kpi",
    "period_type": "hour",
    "region_type": "cell",
    "indicator_network_types": [
        "4G"
    ],
    "start_time": "2024-07-03 21:28:25",
    "end_time": "2024-07-03 23:59:59",
    "encis": [
        "10387734550",
        "10387734551",
        "10387734559",
        "10387804187",
        "10387804188",
        "10387804189",
        "118066195",
        "118066203",
        "118066204",
        "118078993",
        "118078994",
        "118078995",
        "118078978",
        "13795972",
        "13795973",
        "13795975",
        "13795982",
        "13795983",
        "13795987",
        "13795988",
        "13795989",
        "13795992",
        "10387931163",
        "118066195"
    ]
}
```

#### 优化建议
1. 业务告警方案
长沙榔梨镇土岭社区土岭一队HF-D3900461802PT-13存在2个影响业务的告警，需要优先处理。

2. 覆盖问题方案
【弱覆盖】：长沙榔梨镇土岭社区土岭一队HF-D3900461802PT-13存在弱覆盖问题，建议优先调整小区功率参数，提升信号强度，其次可核查方位角、下倾角等参数，增强目标区域覆盖；

3. 负荷问题方案
长沙榔梨镇土岭社区土岭一队HF-D3900461802PT-13高负荷为上高 ，LTE共站小区长沙天心中南林科大综合实验楼、国际学院HL-D3900394567TF-92

4. 干扰问题方案
长沙榔梨镇土岭社区土岭一队HF-D3900461802PT-13存在高干扰，需尽快排查干扰源。
    """
    req = { "query": "对HN-1-240523-0002进行根因分析",
            "response_mode": "blocking",
            "request_id": "31b8b822646e9af543ae826c03e837cb",
            "session_id": "51198bdbc21fdd611ec910fcccc669a6",
            "user": "retina_test",
            "latitude": 28.190929225813772,
            "longitude": 112.97868526823432 }
    dialog_history_data( datetime.now(),req,str(uuid.uuid4()),str(uuid.uuid4()),out)
