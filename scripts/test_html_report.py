#!/usr/bin/env python3
"""
HTML 报告生成器测试脚本

验证 generate_html_report.py 的功能：
1. 从模拟 issues 数据生成 HTML 报告
2. 验证 HTML 结构完整性
3. 验证统计数字正确
4. 验证筛选/搜索功能元素存在
5. 验证空 issues 场景
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# 添加脚本目录到 path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from generate_html_report import build_html, generate_stats, escape_html


def test_basic_generation():
    """测试基本 HTML 生成"""
    print("1. 测试基本 HTML 生成...")

    issues = [
        {"code": "S001", "severity": "ERROR", "location": "整体",
         "description": "缺少必备要素\"前言\"", "suggestion": "补充\"前言\"要素", "context": ""},
        {"code": "T001", "severity": "ERROR", "location": "段落 5",
         "description": "使用禁用能愿动词\"必须\"", "suggestion": "改为\"应\"", "context": "本标准必须按照..."},
        {"code": "F002", "severity": "WARNING", "location": "段落 12",
         "description": "数字与单位\"mm\"之间缺少空格", "suggestion": "在数字与单位间添加空格", "context": "长度为80mm"},
        {"code": "W001", "severity": "WARNING", "location": "段落 8",
         "description": "中文正文使用半角标点\",\"", "suggestion": "改为全角标点\"，\"", "context": "本文件规定了,要求"},
        {"code": "W003", "severity": "SUGGESTION", "location": "段落 20",
         "description": "术语\"测试\"首次出现未加粗", "suggestion": "加粗术语\"测试\"", "context": "测试是指..."},
    ]

    data = {"file": "test_standard.docx", "issues": issues, "total_issues": 5}
    html = build_html(data)

    # 验证基本结构
    assert "<!DOCTYPE html>" in html, "缺少 DOCTYPE"
    assert "<html lang=\"zh-CN\">" in html, "缺少 html 标签"
    assert "</html>" in html, "缺少闭合 html 标签"
    assert "<style>" in html and "</style>" in html, "缺少 style 标签"
    assert "<script>" in html and "</script>" in html, "缺少 script 标签"

    # 验证标题
    assert "标准草稿审查报告" in html, "缺少报告标题"
    assert "test_standard.docx" in html, "缺少文件名"

    # 验证统计数字
    assert ">2<" in html or ">2 " in html, "ERROR 计数应为 2"  # 可能在各种位置
    assert "错误 (ERROR) - 必须修改" in html, "缺少 ERROR 标签"
    assert "警告 (WARNING) - 建议修改" in html, "缺少 WARNING 标签"
    assert "建议 (SUGGESTION) - 可选修改" in html, "缺少 SUGGESTION 标签"

    # 验证问题行
    assert "S001" in html, "缺少 S001 问题"
    assert "T001" in html, "缺少 T001 问题"
    assert "F002" in html, "缺少 F002 问题"
    assert "W001" in html, "缺少 W001 问题"
    assert "W003" in html, "缺少 W003 问题"

    # 验证可修复标记
    assert "可修复" in html, "缺少可修复标记"

    # 验证筛选栏
    assert "filterIssues" in html, "缺少筛选函数调用"
    assert "filterCategory" in html, "缺少分类筛选函数调用"
    assert "searchIssues" in html, "缺少搜索函数调用"

    # 验证上下文展开
    assert "toggleDetail" in html, "缺少展开函数"
    assert "detail-1" in html, "缺少 detail-1 (T001 有 context)"

    # 验证分类统计卡片
    assert "格式编排" in html, "缺少格式编排分类"
    assert "结构要素" in html, "缺少结构要素分类"
    assert "规范性用词" in html, "缺少规范性用词分类"
    assert "文字表述" in html, "缺少文字表述分类"

    print("   PASS - 基本 HTML 生成正确")
    return html


def test_stats():
    """测试统计功能"""
    print("\n2. 测试统计功能...")

    issues = [
        {"code": "F001", "severity": "ERROR", "location": "", "description": "", "suggestion": ""},
        {"code": "F002", "severity": "WARNING", "location": "", "description": "", "suggestion": ""},
        {"code": "S001", "severity": "ERROR", "location": "", "description": "", "suggestion": ""},
        {"code": "T001", "severity": "ERROR", "location": "", "description": "", "suggestion": ""},
        {"code": "W001", "severity": "WARNING", "location": "", "description": "", "suggestion": ""},
        {"code": "W002", "severity": "SUGGESTION", "location": "", "description": "", "suggestion": ""},
    ]

    stats = generate_stats(issues)

    assert stats["total"] == 6, f"总数应为 6，实际 {stats['total']}"
    assert stats["severity"]["ERROR"] == 3, f"ERROR 应为 3，实际 {stats['severity']['ERROR']}"
    assert stats["severity"]["WARNING"] == 2, f"WARNING 应为 2，实际 {stats['severity']['WARNING']}"
    assert stats["severity"]["SUGGESTION"] == 1, f"SUGGESTION 应为 1，实际 {stats['severity']['SUGGESTION']}"
    assert stats["category"]["F"] == 2, f"F 类应为 2，实际 {stats['category']['F']}"
    assert stats["category"]["S"] == 1, f"S 类应为 1，实际 {stats['category']['S']}"
    assert stats["category"]["T"] == 1, f"T 类应为 1，实际 {stats['category']['T']}"
    assert stats["category"]["W"] == 2, f"W 类应为 2，实际 {stats['category']['W']}"

    # 验证 top_codes 排序
    assert stats["top_codes"][0][0] in ("F001", "F002", "S001", "T001", "W001", "W002")
    assert len(stats["top_codes"]) <= 10

    print("   PASS - 统计功能正确")


def test_empty_issues():
    """测试空 issues 场景"""
    print("\n3. 测试空 issues 场景...")

    data = {"file": "clean_standard.docx", "issues": [], "total_issues": 0}
    html = build_html(data)

    assert "未发现任何问题" in html, "空状态应显示未发现问题"
    assert "clean_standard.docx" in html, "应显示文件名"
    assert ">0<" in html or ">0 " in html, "所有统计应为 0"
    assert "filter-bar\">" not in html, "无问题时不应显示筛选栏（CSS 类定义除外）"

    print("   PASS - 空场景处理正确")


def test_escape_html():
    """测试 HTML 转义"""
    print("\n4. 测试 HTML 转义...")

    assert escape_html("<script>") == "&lt;script&gt;", "尖括号转义失败"
    assert escape_html("\"quote\"") == "&quot;quote&quot;", "引号转义失败"
    assert escape_html("normal text") == "normal text", "普通文本不应被修改"
    assert escape_html("") == "", "空字符串应返回空"
    assert escape_html("a&b") == "a&amp;b", "& 转义失败"

    print("   PASS - HTML 转义正确")


def test_file_output():
    """测试文件输出"""
    print("\n5. 测试文件输出...")

    issues = [
        {"code": "T001", "severity": "ERROR", "location": "段落 1",
         "description": "测试问题", "suggestion": "测试建议", "context": "上下文"},
    ]

    data = {"file": "output_test.docx", "issues": issues, "total_issues": 1}

    # 生成 HTML 并写入临时文件
    html = build_html(data)
    tmp_path = os.path.join(tempfile.gettempdir(), "test_report.html")
    Path(tmp_path).write_text(html, encoding="utf-8")

    # 验证文件存在且可读
    assert os.path.exists(tmp_path), "文件未创建"
    content = Path(tmp_path).read_text(encoding="utf-8")
    assert content == html, "文件内容与生成内容不一致"
    assert len(content) > 1000, f"HTML 内容过短：{len(content)} 字符"

    # 清理
    os.remove(tmp_path)

    print(f"   PASS - 文件输出正确（{len(html)} 字符）")


def test_large_dataset():
    """测试大数据量"""
    print("\n6. 测试大数据量...")

    issues = []
    for i in range(100):
        severities = ["ERROR", "WARNING", "SUGGESTION"]
        codes = ["F001", "S002", "T003", "W004", "F005", "S006"]
        issues.append({
            "code": codes[i % len(codes)],
            "severity": severities[i % len(severities)],
            "location": f"段落 {i}",
            "description": f"测试问题 #{i} 的描述文本",
            "suggestion": f"对应的修改建议 #{i}",
            "context": f"上下文信息 {i}" if i % 3 == 0 else "",
        })

    data = {"file": "large_test.docx", "issues": issues, "total_issues": 100}
    html = build_html(data)

    assert "100" in html, "应显示总数 100"
    assert html.count("issue-row") >= 100, "应包含 100 个问题行"

    stats = generate_stats(issues)
    assert stats["total"] == 100
    assert stats["severity"]["ERROR"] > 0
    assert stats["severity"]["WARNING"] > 0
    assert stats["severity"]["SUGGESTION"] > 0

    print(f"   PASS - 大数据量处理正确（{len(html)} 字符，{len(issues)} 条问题）")


def test_cli_interface():
    """测试命令行接口"""
    print("\n7. 测试命令行接口...")

    import subprocess

    # 创建测试 JSON
    test_json = {
        "file": "cli_test.docx",
        "total_issues": 2,
        "summary": {"ERROR": 1, "WARNING": 1, "SUGGESTION": 0},
        "issues": [
            {"code": "S001", "severity": "ERROR", "location": "整体",
             "description": "缺少\"前言\"", "suggestion": "补充\"前言\"", "context": ""},
            {"code": "F002", "severity": "WARNING", "location": "段落 3",
             "description": "数字与单位缺空格", "suggestion": "补空格", "context": "80mm"},
        ]
    }

    json_path = os.path.join(tempfile.gettempdir(), "test_result.json")
    html_path = os.path.join(tempfile.gettempdir(), "test_cli_report.html")

    Path(json_path).write_text(json.dumps(test_json, ensure_ascii=False), encoding="utf-8")

    # 运行脚本
    result = subprocess.run(
        [sys.executable, os.path.join(script_dir, "generate_html_report.py"),
         json_path, "--output", html_path],
        capture_output=True, text=True, encoding="utf-8"
    )

    assert result.returncode == 0, f"脚本退出码非 0：{result.returncode}\n{result.stderr}"
    assert os.path.exists(html_path), "HTML 文件未生成"
    assert "HTML 报告已生成" in result.stdout, "缺少成功提示"

    content = Path(html_path).read_text(encoding="utf-8")
    assert "S001" in content, "HTML 中缺少 S001"
    assert "F002" in content, "HTML 中缺少 F002"
    assert "cli_test.docx" in content, "HTML 中缺少文件名"

    # 清理
    os.remove(json_path)
    os.remove(html_path)

    print("   PASS - 命令行接口正确")


def main():
    print("=" * 60)
    print("HTML 报告生成器测试")
    print("=" * 60)

    tests = [
        test_basic_generation,
        test_stats,
        test_empty_issues,
        test_escape_html,
        test_file_output,
        test_large_dataset,
        test_cli_interface,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"   FAIL - {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"总计：{passed + failed} 项，通过 {passed}，失败 {failed}")
    if failed == 0:
        print("全部通过！")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
