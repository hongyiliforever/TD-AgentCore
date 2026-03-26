"""
测试 ResolveContentParser 解析器的 Demo
"""
import sys
sys.path.insert(0, 'src')

from utils.resolve_content_parser import ResolveContentParser


def main():
    test_content = """客户情况：【联系时间】2026-03-22 10:02:46;【投诉地点】苏州市-昆山市:心泊梅花苑-地下停车场【苏州市昆山市海虹路心泊梅花苑】;【修正网络类型】5G业务;【投诉点环境】地下室、地下停车场;【联系结果】其他（必须备注详细原因）;【联系结果备注】【工单定性】网络原因-电信共享【投诉地址】昆山市心泊梅花苑24、25栋地下停车场【现场测试情况】测试人员与用户地下车库陪同测试，现场联通4G弱覆盖，5G脱网，电信4G正常。【解决方案进度-最终回复】反映地点已现场测试，该点为共享站点，需同电信协商是否可共享解决，暂无最终解决方案，预计4月8日在“中途意见信息”中追加核实情况。【后续跟进人员】艾雨欣13004514480【备注】如用户再次来电反映此问题，请按照此处理结果与用户解释沟通，无需重复建单，此为我部最终处理结果。;【是否跟踪】是; 问题定位：【投诉原因】网络原因:弱覆盖需优化解决; 处理结果：【投诉原因】网络原因:弱覆盖需优化解决;【联系结果】其他（必须备注详细原因）; 【联系结果备注】【工单定性】网络原因-电信共享【投诉地址】昆山市心泊梅花苑24、25栋地下停车场【现场测试情况】测试人员与用户地下车库陪同测试，现场联通4G弱覆盖，5G脱网，电信4G正常。【解决方案进度-最终回复】反映地点已现场测试，该点为共享站点，需同电信协商是否可共享解决，暂无最终解决方案，预计4月8日在“中途意见信息”中追加核实情况。【后续跟进人员】艾雨欣13004514480【备注】如用户再次来电反映此问题，请按照此处理结果与用户解释沟通，无需重复建单，此为我部最终处理结果。;"""

    print("=" * 60)
    print("原始内容:")
    print("=" * 60)
    print(test_content)
    print()

    result = ResolveContentParser.parse(test_content)

    print("=" * 60)
    print("解析结果:")
    print("=" * 60)

    print("\n【客户情况】")
    print("-" * 40)
    for key, value in result.client_info.items():
        print(f"  {key}: {value if value else '(空)'}")

    print("\n【问题定位】")
    print("-" * 40)
    for key, value in result.problem_location.items():
        print(f"  {key}: {value if value else '(空)'}")

    print("\n【处理结果】")
    print("-" * 40)
    for key, value in result.process_result.items():
        print(f"  {key}: {value if value else '(空)'}")

    print("\n" + "=" * 60)
    print("to_dict() 输出:")
    print("=" * 60)
    import json
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    print("\n" + "=" * 60)
    print("get_field() 方法测试:")
    print("=" * 60)
    print(f"  客户情况.联系时间: {result.get_field('客户情况', '联系时间')}")
    print(f"  问题定位.投诉原因: {result.get_field('问题定位', '投诉原因')}")
    print(f"  处理结果.联系结果: {result.get_field('处理结果', '联系结果')}")


if __name__ == "__main__":
    main()
