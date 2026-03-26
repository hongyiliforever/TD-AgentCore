import csv
import os
from pathlib import Path


class JudgmentTool:
    def __init__(self,  ):
        """
        初始化判断工具

        参数:
            rule_file: 存储判断规则的CSV文件路径
        """
        file = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.rule_file = file + "/config/judgment_rules.csv"
        self.rules = self.load_rules()

    def load_rules(self):
        """从CSV文件加载判断规则"""
        rules = {}
        # 读取规则文件
        with open(self.rule_file, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            # 验证CSV文件是否包含必要的列
            required_columns = {'判断项名称', '判断结果'}
            if not required_columns.issubset(reader.fieldnames):
                missing = required_columns - set(reader.fieldnames)
                raise ValueError(f"规则文件缺少必要的列: {missing}")

            for row in reader:
                judgment_item = row['判断项名称'].strip()
                judgment_result = row['判断结果'].strip()
                rules[judgment_item] = judgment_result

        return rules

    def get_judgment_result(self, judgment_item):
        """
        根据判断项名称获取判断结果

        参数:
            judgment_item: 判断项名称

        返回:
            对应的判断结果，如果未找到则返回None
        """
        return self.rules.get(judgment_item.strip())

    def get_all_judgment_items(self):
        """返回所有判断项名称列表"""
        return list(self.rules.keys())

def get_judgment(item_name:str):
    tool = JudgmentTool()
    result = tool.get_judgment_result(item_name)
    if result is None:
        return item_name
    return  result



if __name__ == "__main__":
    # 创建工具实例，会自动加载或创建规则文件
    tool = JudgmentTool()
    test_items = "testsetwe"
    result = tool.get_judgment_result(test_items)

    print(f"result: {result}")

    # 示例3: 添加新规则（取消注释即可测试）
    # tool.add_rule("新判断项=测试", "这是一个测试判断结果")
    # print("\n添加新规则后，查询结果:")
    # print(tool.get_judgment_result("新判断项=测试"))
