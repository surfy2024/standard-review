#!/usr/bin/env python3
"""
多标准支持测试脚本

测试内容：
1. 标准类型自动检测（5 种类型）
2. profile 配置完整性
3. 规则启用/禁用逻辑
4. CLI --standard 参数
5. CLI --list-standards
6. 专属检查规则（MS001-MS005）
7. 结果输出包含标准类型信息
8. diff_checker 多标准支持
"""

import sys
import os
import json
import subprocess
import tempfile
from pathlib import Path

# 确保能导入模块
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from standard_profiles import (
    PROFILES, get_profile, list_profiles, auto_detect,
    is_rule_enabled, StandardProfile
)

PASS = 0
FAIL = 0


def test_result(name, passed, detail=""):
    global PASS, FAIL
    if passed:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  {detail}")


# ===== 测试 1: profile 配置完整性 =====
def test_profiles_integrity():
    print("\n=== 测试 1: Profile 配置完整性 ===")

    expected_ids = {"gb-national", "gb-industry", "gb-local", "gb-enterprise", "gb-group"}
    actual_ids = set(PROFILES.keys())
    test_result("5 种标准类型已定义", actual_ids == expected_ids,
                f"实际: {actual_ids}")

    for pid, profile in PROFILES.items():
        test_result(f"{pid}.id == '{pid}'", profile.id == pid)
        test_result(f"{pid}.name 非空", bool(profile.name))
        test_result(f"{pid}.drafting_standard 非空", bool(profile.drafting_standard))
        test_result(f"{pid}.prefix_patterns 非空", len(profile.prefix_patterns) > 0)
        test_result(f"{pid}.required_elements 非空", len(profile.required_elements) > 0)
        test_result(f"{pid}.number_example 非空", bool(profile.number_example))
        test_result(f"{pid}.specific_checks 是列表", isinstance(profile.specific_checks, list))
        test_result(f"{pid}.disabled_rules 是集合", isinstance(profile.disabled_rules, set))


# ===== 测试 2: get_profile 和 list_profiles =====
def test_get_and_list():
    print("\n=== 测试 2: get_profile / list_profiles ===")

    p = get_profile("gb-national")
    test_result("get_profile('gb-national') 返回正确对象", p.id == "gb-national")

    p = get_profile("gb-group")
    test_result("get_profile('gb-group') 返回正确对象", p.id == "gb-group")

    try:
        get_profile("nonexistent")
        test_result("get_profile 无效 ID 抛异常", False)
    except ValueError:
        test_result("get_profile 无效 ID 抛异常", True)

    profiles = list_profiles()
    test_result("list_profiles 返回 5 条", len(profiles) == 5)
    test_result("list_profiles 每条含 id/name/description",
                all("id" in p and "name" in p and "description" in p for p in profiles))


# ===== 测试 3: 自动检测 =====
def test_auto_detect():
    print("\n=== 测试 3: 标准类型自动检测 ===")

    # 国家标准
    paras = [{"text": "本标准按照 GB/T 1.1-2020 给出的规则起草。"}, {"text": "GB/T 12345-2020"}]
    test_result("检测国家标准 GB/T", auto_detect(paras) == "gb-national")

    paras = [{"text": "GB 50016-2014 建筑设计防火规范"}]
    test_result("检测国家标准 GB（强制性）", auto_detect(paras) == "gb-national")

    # 行业标准
    paras = [{"text": "YY 0123-2020 医疗器械标准"}]
    test_result("检测行业标准 YY", auto_detect(paras) == "gb-industry")

    paras = [{"text": "JB/T 5001-2019 机械标准"}]
    test_result("检测行业标准 JB/T", auto_detect(paras) == "gb-industry")

    # 地方标准
    paras = [{"text": "DB11/T 1322-2023 北京市地方标准"}]
    test_result("检测地方标准 DB11/T", auto_detect(paras) == "gb-local")

    paras = [{"text": "DB44/T 500-2020 广东省地方标准"}]
    test_result("检测地方标准 DB44/T", auto_detect(paras) == "gb-local")

    # 企业标准
    paras = [{"text": "Q/ABC 001-2023 企业标准"}]
    test_result("检测企业标准 Q/ABC", auto_detect(paras) == "gb-enterprise")

    # 团体标准
    paras = [{"text": "T/CAS 001-2023 团体标准"}]
    test_result("检测团体标准 T/CAS", auto_detect(paras) == "gb-group")

    paras = [{"text": "T/ZSA 114-2020 中关村标准"}]
    test_result("检测团体标准 T/ZSA", auto_detect(paras) == "gb-group")

    # 混合场景：文档同时引用 GB 和自身是团体标准
    paras = [{"text": "本标准按照 GB/T 1.1-2020 起草"}, {"text": "T/CAS 001-2023"}]
    test_result("混合场景优先检测团体标准", auto_detect(paras) == "gb-group")

    # 空文档默认为国家标准
    paras = [{"text": "这是一段普通文本，没有标准编号"}]
    test_result("无标准编号默认国家标准", auto_detect(paras) == "gb-national")

    # 空列表
    test_result("空段落列表默认国家标准", auto_detect([]) == "gb-national")


# ===== 测试 4: 规则启用/禁用 =====
def test_rule_enabling():
    print("\n=== 测试 4: 规则启用/禁用逻辑 ===")

    national = get_profile("gb-national")
    enterprise = get_profile("gb-enterprise")
    group = get_profile("gb-group")

    # 国家标准：所有规则启用
    test_result("国家标准 S007 启用", is_rule_enabled(national, "S007"))
    test_result("国家标准 F001 启用", is_rule_enabled(national, "F001"))
    test_result("国家标准 T001 启用", is_rule_enabled(national, "T001"))

    # 企业标准：S007 禁用
    test_result("企业标准 S007 禁用", not is_rule_enabled(enterprise, "S007"))
    test_result("企业标准 F001 仍启用", is_rule_enabled(enterprise, "F001"))
    test_result("企业标准 T001 仍启用", is_rule_enabled(enterprise, "T001"))

    # 团体标准：S007 禁用
    test_result("团体标准 S007 禁用", not is_rule_enabled(group, "S007"))
    test_result("团体标准 F001 仍启用", is_rule_enabled(group, "F001"))


# ===== 测试 5: StandardChecker 集成 =====
def test_checker_integration():
    print("\n=== 测试 5: StandardChecker 多标准集成 ===")

    from check_standard import StandardChecker

    # 测试手动指定标准类型
    checker = StandardChecker(standard="gb-enterprise")
    test_result("StandardChecker(standard='gb-enterprise') 不立即解析 profile",
                checker.profile is None)
    test_result("pending_standard 已存储", checker._pending_standard == "gb-enterprise")

    # 测试无效标准类型
    try:
        from standard_profiles import get_profile
        get_profile("invalid-type")
        test_result("无效标准类型抛异常", False)
    except ValueError:
        test_result("无效标准类型抛异常", True)


# ===== 测试 6: CLI --list-standards =====
def test_cli_list_standards():
    print("\n=== 测试 6: CLI --list-standards ===")

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "check_standard.py"), "--list-standards"],
        capture_output=True, text=True, cwd=str(SCRIPTS_DIR)
    )
    output = result.stdout + result.stderr

    test_result("--list-standards 退出码 0", result.returncode == 0)
    test_result("输出含'国家标准'", "国家标准" in output)
    test_result("输出含'团体标准'", "团体标准" in output)
    test_result("输出含'企业标准'", "企业标准" in output)
    test_result("输出含'地方标准'", "地方标准" in output)
    test_result("输出含'行业标准'", "行业标准" in output)
    test_result("输出含 gb-national", "gb-national" in output)


# ===== 测试 7: CLI --standard 参数 =====
def test_cli_standard_param():
    print("\n=== 测试 7: CLI --standard 参数 ===")

    # 使用已有测试文件
    test_file = SCRIPTS_DIR / "test_autofix_input.docx"
    if not test_file.exists():
        test_result("测试文件不存在，跳过 CLI 测试", False, str(test_file))
        return

    # 指定企业标准
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "check_standard.py"), str(test_file),
         "--standard", "gb-enterprise", "-o", os.devnull],
        capture_output=True, text=True, cwd=str(SCRIPTS_DIR)
    )
    output = result.stdout + result.stderr
    test_result("--standard gb-enterprise 输出含'企业标准'", "企业标准" in output)
    test_result("--standard gb-enterprise 输出含 profile ID", "gb-enterprise" in output)

    # 指定团体标准
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "check_standard.py"), str(test_file),
         "--standard", "gb-group", "-o", os.devnull],
        capture_output=True, text=True, cwd=str(SCRIPTS_DIR)
    )
    output = result.stdout + result.stderr
    test_result("--standard gb-group 输出含'团体标准'", "团体标准" in output)

    # 无效标准类型
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "check_standard.py"), str(test_file),
         "--standard", "invalid"],
        capture_output=True, text=True, cwd=str(SCRIPTS_DIR)
    )
    test_result("无效 --standard 退出码非 0", result.returncode != 0)

    # 不指定标准（自动检测）
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "check_standard.py"), str(test_file),
         "-o", os.devnull],
        capture_output=True, text=True, cwd=str(SCRIPTS_DIR)
    )
    output = result.stdout + result.stderr
    test_result("自动检测输出含'标准类型'", "标准类型" in output)


# ===== 测试 8: 结果 JSON 包含标准类型 =====
def test_result_json():
    print("\n=== 测试 8: 结果 JSON 包含标准类型信息 ===")

    test_file = SCRIPTS_DIR / "test_autofix_input.docx"
    if not test_file.exists():
        test_result("测试文件不存在，跳过", False)
        return

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        tmp_json = f.name

    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "check_standard.py"), str(test_file),
             "--standard", "gb-group", "--pretty", "-o", tmp_json],
            capture_output=True, text=True, cwd=str(SCRIPTS_DIR)
        )

        with open(tmp_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        test_result("JSON 含 standard_type 字段", "standard_type" in data)
        test_result("JSON standard_type == 'gb-group'", data.get("standard_type") == "gb-group")
        test_result("JSON 含 standard_name 字段", "standard_name" in data)
        test_result("JSON standard_name == '团体标准'", data.get("standard_name") == "团体标准")
        test_result("JSON 含 drafting_standard 字段", "drafting_standard" in data)
        test_result("JSON drafting_standard == 'GB/T 1.1-2020'",
                    data.get("drafting_standard") == "GB/T 1.1-2020")
    finally:
        os.unlink(tmp_json)


# ===== 测试 9: 专属检查规则 MS001-MS005 =====
def test_specific_checks():
    print("\n=== 测试 9: 专属检查规则 MS001-MS005 ===")

    from check_standard import StandardChecker, Severity

    # 创建模拟段落数据
    def make_checker(paras_text, standard):
        checker = StandardChecker(standard=standard)
        checker.profile = get_profile(standard)
        checker.paragraphs = [
            {"index": i, "text": t, "style": "", "is_heading": False, "section": ""}
            for i, t in enumerate(paras_text)
        ]
        return checker

    # MS001: 国家标准编号冒号
    checker = make_checker(["GB/T 12345:2020 有误"], "gb-national")
    checker._check_national_standard_number()
    ms001_issues = [i for i in checker.issues if i.code == "MS001"]
    test_result("MS001 检测国家标准编号冒号", len(ms001_issues) == 1)

    checker = make_checker(["GB/T 12345-2020 正确"], "gb-national")
    checker._check_national_standard_number()
    ms001_issues = [i for i in checker.issues if i.code == "MS001"]
    test_result("MS001 正确格式不报错", len(ms001_issues) == 0)

    # MS002: 行业标准未知前缀
    checker = make_checker(["ZZ/T 9999-2020 未知行业"], "gb-industry")
    checker._check_industry_standard_number()
    ms002_issues = [i for i in checker.issues if i.code == "MS002"]
    test_result("MS002 检测未知行业前缀", len(ms002_issues) == 1)

    checker = make_checker(["YY 0123-2020 医疗器械"], "gb-industry")
    checker._check_industry_standard_number()
    ms002_issues = [i for i in checker.issues if i.code == "MS002"]
    test_result("MS002 已知行业前缀不报错", len(ms002_issues) == 0)

    # MS003: 地方标准无效区域代码
    checker = make_checker(["DB99/T 100-2020 无效代码"], "gb-local")
    checker._check_local_standard_number()
    ms003_issues = [i for i in checker.issues if i.code == "MS003"]
    test_result("MS003 检测无效区域代码", len(ms003_issues) == 1)

    checker = make_checker(["DB11/T 1322-2023 北京"], "gb-local")
    checker._check_local_standard_number()
    ms003_issues = [i for i in checker.issues if i.code == "MS003"]
    test_result("MS003 有效区域代码不报错", len(ms003_issues) == 0)

    # MS004: 企业标准缺年份
    checker = make_checker(["Q/ABC 001 企业标准无年份"], "gb-enterprise")
    checker._check_enterprise_standard_number()
    ms004_issues = [i for i in checker.issues if i.code == "MS004"]
    test_result("MS004 检测企业标准缺年份", len(ms004_issues) == 1)

    checker = make_checker(["Q/ABC 001-2023 有年份"], "gb-enterprise")
    checker._check_enterprise_standard_number()
    ms004_issues = [i for i in checker.issues if i.code == "MS004"]
    test_result("MS004 有年份不报错", len(ms004_issues) == 0)

    # MS005: 团体标准缺年份
    checker = make_checker(["T/CAS 001 团体标准无年份"], "gb-group")
    checker._check_group_standard_number()
    ms005_issues = [i for i in checker.issues if i.code == "MS005"]
    test_result("MS005 检测团体标准缺年份", len(ms005_issues) == 1)

    checker = make_checker(["T/CAS 001-2023 有年份"], "gb-group")
    checker._check_group_standard_number()
    ms005_issues = [i for i in checker.issues if i.code == "MS005"]
    test_result("MS005 有年份不报错", len(ms005_issues) == 0)


# ===== 测试 10: 企业标准禁用 S007 =====
def test_enterprise_disables_s007():
    print("\n=== 测试 10: 企业标准禁用 S007 ===")

    from check_standard import StandardChecker, Severity

    # 创建模拟检查器，模拟缺少规范性引用文件的场景
    checker = StandardChecker(standard="gb-enterprise")
    checker.profile = get_profile("gb-enterprise")
    checker.paragraphs = [
        {"index": 0, "text": "1 范围", "style": "", "is_heading": True, "section": "范围"},
        {"index": 1, "text": "本文件规定了某些内容。", "style": "", "is_heading": False, "section": "范围"},
    ]
    checker.headings = [checker.paragraphs[0]]

    # 企业标准：S007 禁用，不应报告
    checker._check_empty_sections()
    s007_issues = [i for i in checker.issues if i.code == "S007"]
    test_result("企业标准不报告 S007", len(s007_issues) == 0)

    # 国家标准：S007 启用，应报告
    checker2 = StandardChecker(standard="gb-national")
    checker2.profile = get_profile("gb-national")
    checker2.paragraphs = checker.paragraphs
    checker2.headings = checker.headings
    checker2._check_empty_sections()
    s007_issues2 = [i for i in checker2.issues if i.code == "S007"]
    test_result("国家标准报告 S007", len(s007_issues2) > 0)


# ===== 测试 11: profile required_elements 差异 =====
def test_required_elements_diff():
    print("\n=== 测试 11: 不同标准类型必备要素差异 ===")

    national = get_profile("gb-national")
    enterprise = get_profile("gb-enterprise")

    test_result("国家标准必备要素含'前言'", "前言" in national.required_elements)
    test_result("国家标准必备要素含'范围'", "范围" in national.required_elements)
    test_result("企业标准必备要素不含'前言'", "前言" not in enterprise.required_elements)
    test_result("企业标准必备要素含'范围'", "范围" in enterprise.required_elements)
    test_result("企业标准'前言'为可选", "前言" in enterprise.optional_elements)


# ===== 测试 12: diff_checker 多标准支持 =====
def test_diff_checker_standard():
    print("\n=== 测试 12: diff_checker 多标准支持 ===")

    from diff_checker import DiffChecker

    dc = DiffChecker(standard="gb-enterprise")
    test_result("DiffChecker 接受 standard 参数", dc._pending_standard == "gb-enterprise")

    dc2 = DiffChecker()
    test_result("DiffChecker 默认 standard=None", dc2._pending_standard is None)


# ===== 主函数 =====
def main():
    print("=" * 60)
    print("多标准支持测试 (v2.5)")
    print("=" * 60)

    test_profiles_integrity()
    test_get_and_list()
    test_auto_detect()
    test_rule_enabling()
    test_checker_integration()
    test_cli_list_standards()
    test_cli_standard_param()
    test_result_json()
    test_specific_checks()
    test_enterprise_disables_s007()
    test_required_elements_diff()
    test_diff_checker_standard()

    print("\n" + "=" * 60)
    print(f"测试结果: {PASS} 通过, {FAIL} 失败")
    print("=" * 60)

    if FAIL > 0:
        sys.exit(1)
    else:
        print("全部通过！")


if __name__ == "__main__":
    main()
