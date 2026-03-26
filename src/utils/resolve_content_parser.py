"""
回单内容结构化解析器
将 resolve_content / examined_content 按一级、二级结构拆解为字典

解析逻辑：
1. 先按一级标题（客户情况：、问题定位：、处理结果：）切分内容
2. 在每个一级标题的内容范围内，用对应的二级标题匹配
"""
import re
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class ParsedResolveContent:
    raw_content: str = ""
    client_info: Dict[str, str] = field(default_factory=dict)
    problem_location: Dict[str, str] = field(default_factory=dict)
    process_result: Dict[str, str] = field(default_factory=dict)

    def get_field(self, section: str, field_name: str) -> str:
        section_map = {
            "客户情况": self.client_info,
            "问题定位": self.problem_location,
            "处理结果": self.process_result
        }
        section_dict = section_map.get(section, {})
        return section_dict.get(field_name, "")

    def to_dict(self) -> dict:
        return {
            "客户情况": self.client_info,
            "问题定位": self.problem_location,
            "处理结果": self.process_result
        }


class ResolveContentParser:
    FIRST_LEVEL_HEADERS = ["客户情况", "问题定位", "处理结果"]

    SECOND_LEVEL_FIELDS = {
        "客户情况": [
            "联系时间", "投诉地点", "修正网络类型", "投诉点环境",
            "联系结果", "联系结果备注", "现场测试时间"
        ],
        "问题定位": [
            "工单定性", "投诉原因", "修正故障现象", "网络使用",
            "网络内部问题定位", "是否覆盖问题", "现场测试情况",
            "问题定位分析", "解决程度", "预计解决时间"
        ],
        "处理结果": [
            "投诉原因", "联系结果", "现场测试情况", "问题定位分析",
            "解决程度", "预计解决时间", "后续跟进人员", "最终处理专业",
            "告警信息", "结论与解决方案", "备注"
        ]
    }

    @classmethod
    def parse(cls, content: str) -> ParsedResolveContent:
        if not content:
            return ParsedResolveContent(raw_content="")

        result = ParsedResolveContent(raw_content=content)
        sections = cls._split_by_first_level(content)

        result.client_info = cls._extract_fields(
            sections.get("客户情况", ""),
            cls.SECOND_LEVEL_FIELDS["客户情况"]
        )
        result.problem_location = cls._extract_fields(
            sections.get("问题定位", ""),
            cls.SECOND_LEVEL_FIELDS["问题定位"]
        )
        result.process_result = cls._extract_fields(
            sections.get("处理结果", ""),
            cls.SECOND_LEVEL_FIELDS["处理结果"]
        )

        return result

    @classmethod
    def _split_by_first_level(cls, content: str) -> Dict[str, str]:
        sections = {}
        pattern = r'(客户情况|问题定位|处理结果)[：:]'
        matches = list(re.finditer(pattern, content))

        for i, match in enumerate(matches):
            section_name = match.group(1)
            start_pos = match.end()

            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(content)

            section_content = content[start_pos:end_pos].strip()
            sections[section_name] = section_content

        return sections

    @classmethod
    def _extract_fields(cls, section_content: str, fields: List[str]) -> Dict[str, str]:
        result = {}

        valid_field_patterns = [rf'【{re.escape(f)}】' for f in fields]
        all_valid_fields_pattern = '|'.join(valid_field_patterns)

        for field_name in fields:
            pattern = rf'【{re.escape(field_name)}】'
            match = re.search(pattern, section_content)

            if not match:
                result[field_name] = ""
                continue

            field_start = match.end()
            remaining = section_content[field_start:]

            end_match = re.search(all_valid_fields_pattern, remaining)

            if end_match:
                field_value = remaining[:end_match.start()].strip()
            else:
                field_value = remaining.strip()

            field_value = field_value.rstrip(';').strip()
            result[field_name] = field_value

        return result
