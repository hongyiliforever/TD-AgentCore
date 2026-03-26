import csv
import numpy as np
import os
import yaml
from src.utils.logger import agent_logger as logger
from datetime import datetime
import re
import importlib
from typing import Optional
import difflib
# from FlagEmbedding import FlagReranker
import glob
from dateutil import parser


def handle_check(question, target_type, content):
    logger.info(f"handle_check: {question} : {target_type} {content}")
    resp_cont = transform_resp(target_type, content)
    cellPositionAnanlysis = "小区定位分析功能链接： <a href='/#/home/iframe?hrefSrc=%2Fcemv5.html%23%2Fhome%2FcellPositionAnanlysis&routeTarget=_self&toRoute=[object,Object]&sfcName=感知分析中心/小区感知分析/小区定位分析'  style = 'color:#337DFF;'  >小区定位分析</a>"
    customerOfPortrait = "用户感知画像功能链接：<a href='/#/home/iframe?hrefSrc=%2Fcemv5.html%23%2Fhome%2FcustomerOfPortrait&routeTarget=_self&toRoute=[object,Object]&sfcName=感知分析中心%2F面向用户%2F用户感知画像'  style = 'color:#337DFF;'  " + target_type + "  >用户感知画像</a>"
    resp = resp_cont
    if question.find(('在用户感知画像功能中质差列表').strip()) != -1 and resp_cont.find(('小区定位分析</a>').strip()) == -1:
        resp = resp_cont + '\n' + cellPositionAnanlysis
    elif question.find(('用户投诉网速慢').strip()) != -1 and resp_cont.find(('用户感知画像</a>').strip()) == -1:
        resp = resp_cont + '\n' + customerOfPortrait
    return resp


def is_all_digits_letters(s):
    digits = r'^\d+$'
    letters = r'^[a-zA-Z]+$'
    pattern = r'^86\d{11}$'
    if bool(re.match(pattern, s)):
        return False
    return bool(re.match(digits, s)) or bool(re.match(letters, s)) or bool(re.match(pattern, s))


def transform_resp(target_type, response):
    resp = response
    try:
        userMining = "<a href='/#/home/iframe?hrefSrc=%2Fcemv5.html%23%2Fhome%2FuserMining&routeTarget=_self&toRoute=%5Bobject,Object%5D&sfcName=感知分析中心%2F用户感知分析%2F潜在不满意用户挖掘'  style = 'color:#337DFF;' " + target_type + "  >潜在不满意用户挖掘</a>"
        customerOfPortrait = "<a href='/#/home/iframe?hrefSrc=%2Fcemv5.html%23%2Fhome%2FcustomerOfPortrait&routeTarget=_self&toRoute=[object,Object]&sfcName=感知分析中心%2F面向用户%2F用户感知画像'  style = 'color:#337DFF;'  " + target_type + "  >用户感知画像</a>"
        cellPositionAnanlysis = "<a href='/#/home/iframe?hrefSrc=%2Fcemv5.html%23%2Fhome%2FcellPositionAnanlysis&routeTarget=_self&toRoute=[object,Object]&sfcName=感知分析中心/小区感知分析/小区定位分析'  style = 'color:#337DFF;' " + target_type + "   >小区定位分析</a>"
        areaAnalysis = "<a href='/#/home/iframe?hrefSrc=%2Fneq.html%23%2Fcem_portal%2FareaAnalysis%2FareaAnalysis&routeTarget=_self&toRoute=[object,Object]&sfcName=移动网质量管理中心/4/5G数据质量分析/区域质差分析'  style = 'color:#337DFF;' " + target_type + "   >区域质差分析</a>"
        businessOverview = "<a href='/#/home/iframe?hrefSrc=http%3A%2F%2F10.21.13.165%3A8090%2Fneq.html%23%2Fcem_portal%2FbusinessOverview&routeTarget=_self&toRoute=%5Bobject%20Object%5D&sfcName=移动网质量管理中心%2F4%2F5G数据质量分析%2F业务质量概览'  style = 'color:#337DFF;' " + target_type + "   >业务质量概览</a>"
        resp = (response.replace("\n", '<br/>')
                .replace("<a>潜在不满意用户挖掘</a>", userMining)
                .replace("<a>用户感知画像</a>", customerOfPortrait)
                .replace("<a>小区定位分析</a>", cellPositionAnanlysis)
                .replace('<a href="小区定位分析">小区定位分析</a>', cellPositionAnanlysis)
                .replace("<a>区域质差分析</a>", areaAnalysis)
                .replace("<a>业务质量概览</a>", businessOverview)
                .replace('进入潜在不满意用户挖掘功能', '进入' + userMining + '功能')
                .replace('进入业务质量概览功能', '进入' + businessOverview + '功能')
                .replace('进入用户感知画像功能', '进入' + customerOfPortrait + '功能')
                .replace('进入到用户感知画像功能', '进入到' + customerOfPortrait + '功能')
                .replace('进入小区定位分析功能', '进入' + cellPositionAnanlysis + '功能')
                .replace('在小区定位分析功能中', '在' + cellPositionAnanlysis + '功能中')
                .replace('[小区定位分析](https://example.com)', cellPositionAnanlysis)
                .replace('链接（业务质量总览）', businessOverview)
                .replace('链接（业务大类指标）', businessOverview)
                .replace('链接（区域质差分析）', areaAnalysis)
                .replace('【功能链接：用户感知画像】', customerOfPortrait)
                .replace('【功能链接：小区定位分析】', cellPositionAnanlysis)
                .replace('+ 链接：[体验雷达图](https://example.com/experience-radar)', '')
                .replace('+ 链接：[质差清单](https://example.com/quality-problem-list)', '')
                .replace('+ 链接：[小区定位分析](https://example.com/cell-positioning-analysis)', cellPositionAnanlysis)
                .replace('注意：以上链接仅为示例，请替换为实际的系统链接。', '')
                .replace('请注意，回答中不应出现Markdown格式的字符，如需使用链接，请使用标签。', '')
                .replace('请注意，以上步骤仅供参考，具体分析方法和功能使用方法应根据实际情况进行调整。', '')
                .replace('*', '').replace('+', ''))

        pattern_userMining = r'\[(潜在不满意用户挖掘)\]\([^)]+\)'
        resp = re.sub(pattern_userMining,
                      lambda match: userMining if match.group(1) == '潜在不满意用户挖掘' else match.group(),
                      resp)
        pattern_customerOfPortrait = r'\[(用户感知画像)\]\([^)]+\)'
        resp = re.sub(pattern_customerOfPortrait,
                      lambda match: customerOfPortrait if match.group(1) == '用户感知画像' else match.group(),
                      resp)
        pattern_customerOfPortrait_1 = r'\[(体验雷达图)\]\([^)]+\)'
        resp = re.sub(pattern_customerOfPortrait_1,
                      lambda match: customerOfPortrait if match.group(1) == '体验雷达图' else match.group(),
                      resp)
        pattern_customerOfPortrait_1 = r'\[(体验仪表盘)\]\([^)]+\)'
        resp = re.sub(pattern_customerOfPortrait_1,
                      lambda match: customerOfPortrait if match.group(1) == '体验仪表盘' else match.group(),
                      resp)
        pattern_customerOfPortrait_2 = r'\[(质差清单)\]\([^)]+\)'
        resp = re.sub(pattern_customerOfPortrait_2,
                      lambda match: customerOfPortrait if match.group(1) == '质差清单' else match.group(),
                      resp)
        pattern_cellPositionAnanlysis = r'\[(小区定位分析)\]\([^)]+\)'
        resp = re.sub(pattern_cellPositionAnanlysis,
                      lambda match: cellPositionAnanlysis if match.group(1) == '小区定位分析' else match.group(),
                      resp)
        pattern_cellPositionAnanlysis_1 = r'\[(小区质差原因分析)\]\([^)]+\)'
        resp = re.sub(pattern_cellPositionAnanlysis_1,
                      lambda match: cellPositionAnanlysis if match.group(
                          1) == '小区质差原因分析' else match.group(),
                      resp)
        logger.info(f"transform_resp {resp}")
    except Exception as e:
        logger.error("error: %r", e)
    return resp


def extract_ques(type, ques):
    logger.info(f"extract_ques {type} :{ques}")
    time_pattern = r"时间:(.*)"
    location_pattern = type + r":(.*)"
    question_pattern = r"指标名称:(.*)"

    # 使用re.search来查找匹配项
    time_match = re.search(time_pattern, ques)
    location_match = re.search(location_pattern, ques)
    question_match = re.search(question_pattern, ques)

    # 提取匹配到的值
    time_value = time_match.group(0).split(type)[0].strip().replace('时间', '').replace(':', '').replace('：',
                                                                                                         '').replace(
        '呢', '').replace('为', '').replace('呢', '').replace(',', '').replace('。', '').replace('.', '').replace('到',
                                                                                                                 ' ').replace(
        '"', '').replace('”', '') if time_match else ''
    location_value = (location_match.group(0).split('时间')[0].replace(type, '').strip().replace(':', '')
                      .replace('：', '').replace('呢', '').replace('省', '').replace('市', '').replace(',', '').replace(
        '，', '').replace('为', '').replace('、', '')) if location_match else ''
    question_value = \
        question_match.group(0).split(type)[0].replace('指标名称', '').replace('问题', '').replace('呢', '').replace(
            '我想查询下',
            '').replace('为', '').replace('查下',
                                          '').replace(
            ':', '').replace('：', '').replace(',', '').replace('，', '') if question_match else ''

    if (len(ques.split('时间')) > 3):
        time_match, location_match, question_match = find_last(type, ques)
        time_value = time_match.strip().replace(':', '').replace('：', '').replace('呢', '').replace(',', '').replace(
            '。', '').replace('为', '').replace('.', '').replace('"', '').replace('”', '') if time_match else ''
        location_value = location_match.strip().replace(':', '').replace(
            '：', '').replace('为', '').replace('呢', '').replace('省', '').replace('市', '').replace(',', '').replace(
            '，', '').replace(
            '、', '') if location_match else ''
        question_value = \
            question_match.strip().replace('指标名称', '').replace('为', '').replace('问题', '').replace('呢',
                                                                                                         '').replace(
                '我想查询下',
                '').replace(
                '查下',
                '').replace(
                ':', '').replace('：', '').split('|')[0].replace(',', '').replace('，', '') if question_match else ''

    query = f"{time_value}"
    parts = query.split()
    if len(parts) == 0:
        date_str = ''
        datetime_end = ''
    if len(parts) == 1:
        date_str = transform_date(parts[0])
        datetime_end = transform_date(parts[0])
    if len(parts) == 2:
        date_str = transform_date(parts[0])
        datetime_end = transform_date(parts[1])
    if len(parts) >= 3:
        date_str = transform_date(parts[0])
        datetime_end = transform_date(parts[0])
    return date_str, datetime_end, location_value.strip(), question_value.strip()


def transform_date(date_str):
    logger.info("transform_date: %r", date_str)
    try:
        trans_date = datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        try:
            trans_date = datetime.strptime(date_str, '%Y/%m/%d').strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                trans_date = datetime.strptime(date_str, '%Y年%m月%d日').strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    trans_date = datetime.strptime(date_str, '%Y年%m月%d号').strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        trans_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        try:
                            trans_date = datetime.strptime(date_str, '%Y.%m.%d').strftime('%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            return date_str

    return trans_date

def convert_numpy_to_python(data):
    if isinstance(data, list):
        return [convert_numpy_to_python(item) for item in data]
    elif isinstance(data, dict):
        return {key: convert_numpy_to_python(value) for key, value in data.items()}
    elif isinstance(data, np.integer):
        return int(data)
    elif isinstance(data, np.floating):
        return float(data)
    else:
        return data


def find_rank_by_value(d, key):
    # 首先，根据值对字典的项进行降序排序
    sorted_items = sorted(d.items(), key=lambda x: x[1], reverse=True)

    # 然后，遍历排序后的列表来找到指定键的排名
    for rank, (k, _) in enumerate(sorted_items, start=1):
        if k == key:
            return rank
def transform_date2(date_str):
    try:
        trans_date = datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
    except ValueError:
        try:
            trans_date = datetime.strptime(date_str, '%Y/%m/%d').strftime('%Y-%m-%d')
        except ValueError:
            try:
                trans_date = datetime.strptime(date_str, '%Y年%m月%d日').strftime('%Y-%m-%d')
            except ValueError:
                try:
                    trans_date = datetime.strptime(date_str, '%Y年%m月%d号').strftime('%Y-%m-%d')
                except ValueError:
                    try:
                        trans_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y-%m-%d')
                    except ValueError:
                        try:
                            trans_date = datetime.strptime(date_str, '%Y.%m.%d').strftime('%Y-%m-%d')
                        except ValueError:
                            try:
                                trans_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f').strftime('%Y-%m-%d')
                            except ValueError:
                                return date_str


    return trans_date

def find_last(type, ques):
    lines = ques.strip().split('\n')
    # 遍历每一行
    try:
        for line in lines:
            if line.strip() == '':
                break
            time = re.search(r"时间(.*)", line).group(0).split('时间')[1]
            city = re.search(type + r":(.*)", line).group(0).split(type)[1].split('时间')[0]
            indicator = re.search(r"指标名称(.*)", line).group(0).split('指标名称')[1].split(type)[0]

            return time, city, indicator
    except Exception as e:
        logger.info(f"find_last 发生异常: {e}")
        line = ques.strip()
        time = re.search(r"时间:(.*)", line).group(0).split('时间')[1]
        city = re.search(type + r":(.*)", line).group(0).split(type)[1].split('时间')[0]
        indicator = re.search(r"指标名称:(.*)", line).group(0).split('指标名称')[1].split(type)[0]
        return time, city, indicator

def find_tools() -> dict:
    # CSV文件路径
    csv_file_path = '../resource/diagnose_tools.csv'  # 替换为你的CSV文件路径
    # 读取CSV文件并创建id到names的映射字典
    id_to_names_map = {}
    path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 获取当前文件所在的上一级目录
    with open(path + '/resource/' + csv_file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # 跳过标题行（如果有的话）
        for row in reader:
            id_value, name_value = row  # 假设CSV有两列，id和names
            id_to_names_map[name_value] = int(id_value)
    return id_to_names_map

def convert_zh_date(time_str):
    dt_obj = datetime.strptime(time_str, "%Y.%m.%d")
    year = dt_obj.year
    month = dt_obj.month
    day = dt_obj.day
    time = f"{year}年{month}月{day}日"
    return time


def get_yaml_data():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    configs_dir = os.path.join(root_dir, 'configs')
    all_yaml_data = {}
    for yaml_file in glob.glob(os.path.join(configs_dir, '*.yaml')):
        with open(yaml_file, encoding="utf-8") as f:
            data = yaml.full_load(f.read())
            all_yaml_data.update(data)
    return all_yaml_data

config_data = get_yaml_data()

def get_neq_url():
    neq_url = config_data['NEQ_URL']
    return neq_url

def get_esurl():
    es = config_data['ELASTICSEARCH_URL']
    return es

def get_nl2sql_url():
    url = config_data['NL2SQL_URL']
    return url

def get_dh_neq_url():
    url = config_data['DH_NEQ_URL']
    return url

def get_use_cache():
    use_cache = config_data['USE_CACHE']
    return use_cache

def get_config_value(key )  -> str:
    value = config_data[key]
    return value



def trans_ec_list_to_dict(page_data):
    """

    Args:
        page_data: 节能的查询结果

    Returns:节能查询结果转为table类型数据

    """
    data = []
    # 遍历列表中的每个字典
    for item in page_data:
        array_keys = [key for key, value in item.items() if isinstance(value, list)]
        non_array_keys = [key for key in item.keys() if key not in array_keys]

        if array_keys:
            # 使用 zip 函数将数组中的元素一一对应起来
            for values in zip(*[item[key] for key in array_keys]):
                new_item = dict(zip(array_keys, values))
                # 将非数组类型的键值对添加到新的字典中
                new_item.update({key: item[key] for key in non_array_keys})
                # 将新的字典添加到 d 列表中
                data.append(new_item)
        else:
            # 如果没有数组类型的键，则直接将字典添加到列表中
            data.append(item)
    return data



def find_max_index(list_of_floats):
    # 使用内置的index()方法找到最大值的索引
    max_value = max(list_of_floats)
    max_index = list_of_floats.index(max_value)
    return max_index

def score_similarity_process(query, docs, isRank=True):
    if len(docs) == 1:
        return docs[0]
    if isRank:
        # search_path = os.path.dirname(
        #     os.path.dirname(os.path.abspath(__file__))) + '/resource/bge-reranker-base'
        # reranker = FlagReranker(
        #     search_path,
        #     use_fp16=False)
        # new_rerank_pairs = [[query, doc[0].metadata["function_name"]] for doc in docs]
        # scores = reranker.compute_score(new_rerank_pairs, normalize=True)
        # max_index = find_max_index(scores)
        # return docs[max_index]
        return docs[0]
    else:
        functions = [doc[0].metadata["function_name"] for doc in docs]
        matches = difflib.get_close_matches(query, functions, cutoff=0.1)
        if matches:
            # # 假设最相似的问题就是最佳匹配
            best_match = matches[0]
            # 查找最佳匹配问题的答案
            for doc in docs:
                if doc[0].metadata["function_name"] == best_match:
                    return doc
        else:
            return docs[0]

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


if __name__ == '__main__':
    # str = '地市 :AI: 指标名称: 差感小区清单, 地市: , 时间: 2023年6月30号。'
    print(normalize_time('2025-04-18 01:52:58' ))
    print(normalize_time('Thu Apr 10 14:41:01 CST 2025'))
    # print(get_config_value('aap_check_result_key'))
    # da = get_use_cache()
    # print(bool(da)==da)
