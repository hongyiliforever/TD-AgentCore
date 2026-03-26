"""
质检项输入构建器
根据质检项类型，从解析后的回单内容中提取所需字段，构建精简输入
"""
from typing import Dict, Any, List, Optional, Tuple
from src.utils.resolve_content_parser import ResolveContentParser, ParsedResolveContent


class CheckItemInputBuilder:

    FIELD_MAPPING = {
        "未联系用户说明": {
            "fields": [
                ("客户情况", "联系结果"),
                ("问题定位", "投诉原因"),
                ("处理结果", "备注"),
                ("客户情况", "联系结果备注"),
                ("问题定位", "现场测试情况"),
                ("处理结果", "现场测试情况"),
                ("问题定位", "问题定位分析"),
                ("处理结果", "问题定位分析"),
            ],
            "needs_wav": False,
            "use_examined": False
        },
        "联系用户说明": {
            "fields": [
                ("客户情况", "联系结果"),
                ("客户情况", "联系结果备注"),
            ],
            "needs_wav": False,
            "use_examined": False
        },
        "礼貌用语": {
            "fields": [],
            "needs_wav": True,
            "use_examined": False
        },
        "问题恢复检测": {
            "fields": [
                ("处理结果", "备注"),
                ("客户情况", "联系结果备注"),
            ],
            "needs_wav": True,
            "use_examined": False
        },
        "未上门测试": {
            "fields": [
                ("客户情况", "联系结果"),
                ("问题定位", "投诉原因"),
                ("处理结果", "备注"),
                ("客户情况", "联系结果备注"),
            ],
            "needs_wav": True,
            "use_examined": False
        },
        "现场测试情况": {
            "fields": [
                ("问题定位", "现场测试情况"),
                ("处理结果", "现场测试情况"),
                ("问题定位", "问题定位分析"),
                ("处理结果", "问题定位分析"),
            ],
            "needs_wav": False,
            "use_examined": False
        },
        "是否有解决方案": {
            "fields": [
                ("处理结果", "结论与解决方案"),
                ("问题定位", "问题定位分析"),
                ("处理结果", "问题定位分析"),
                ("处理结果", "备注"),
                ("客户情况", "联系结果备注"),
            ],
            "needs_wav": False,
            "use_examined": True
        },
        "解决方案": {
            "fields": [
                ("问题定位", "问题定位分析"),
                ("处理结果", "问题定位分析"),
                ("处理结果", "结论与解决方案"),
            ],
            "needs_wav": False,
            "use_examined": False
        },
        "跟进人员": {
            "fields": [
                ("处理结果", "后续跟进人员"),
            ],
            "needs_wav": False,
            "use_examined": False
        },
        "是否有效电话录音": {
            "fields": [],
            "needs_wav": True,
            "use_examined": False
        },
        "是否2G问题": {
            "fields": [
                ("处理结果", "问题定位分析"),
                ("处理结果", "结论与解决方案"),
                ("处理结果", "备注"),
            ],
            "needs_wav": False,
            "use_examined": False
        },
        "是否回单已恢复": {
            "fields": [
                ("客户情况", "联系结果"),
                ("问题定位", "投诉原因"),
            ],
            "needs_wav": False,
            "use_examined": False
        },
        "语音文本格式转换": {
            "fields": [],
            "needs_wav": True,
            "use_examined": False,
            "needs_full_wav": True
        },
    }

    @classmethod
    def build_input(
        cls,
        check_item: str,
        order_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        mapping = cls.FIELD_MAPPING.get(check_item)

        if not mapping:
            return {"raw_order_info": order_info, "check_item": check_item}

        result = {
            "check_item": check_item,
        }

        content_key = "examined_content" if mapping.get("use_examined") else "resolve_content"
        raw_content = order_info.get(content_key, "")

        structured_data = {}
        if raw_content:
            parsed = ResolveContentParser.parse(raw_content)
            for section, field_name in mapping["fields"]:
                value = parsed.get_field(section, field_name)
                key = f"{section}【{field_name}】"
                structured_data[key] = value if value else ""
        else:
            for section, field_name in mapping["fields"]:
                key = f"{section}【{field_name}】"
                structured_data[key] = ""

        if mapping["fields"]:
            result["structured_content"] = structured_data

        if mapping["needs_wav"]:
            if mapping.get("needs_full_wav"):
                wav_data = order_info.get("wav_data", "")
                wav_time = order_info.get("wav_time", "")
                wav_duration = order_info.get("wav_duration", "")
                if wav_data:
                    result["wav_data"] = wav_data
                if wav_time:
                    result["wav_time"] = wav_time
                if wav_duration:
                    result["wav_duration"] = wav_duration
            else:
                wav_data = order_info.get("wav_data", "")
                if wav_data:
                    result["wav_data"] = wav_data

        return result

    @classmethod
    def get_required_fields(cls, check_item: str) -> List[Tuple[str, str]]:
        mapping = cls.FIELD_MAPPING.get(check_item, {})
        return mapping.get("fields", [])

    @classmethod
    def needs_wav_data(cls, check_item: str) -> bool:
        mapping = cls.FIELD_MAPPING.get(check_item, {})
        return mapping.get("needs_wav", False)

    @classmethod
    def get_all_check_items(cls) -> List[str]:
        return list(cls.FIELD_MAPPING.keys())
