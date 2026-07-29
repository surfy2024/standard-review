#!/usr/bin/env python3
"""
HTML 交互报告生成器

将 check_standard.py 的检查结果生成为自包含的 HTML 报告，
支持按严重等级/规则分类筛选、问题详情展开、统计概览。

使用方法：
    python generate_html_report.py result.json --output report.html
    python generate_html_report.py --issues-json '...' --output report.html
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional


# 规则分类映射
CATEGORY_MAP = {
    "F": {"name": "格式编排", "color": "#2563eb", "bg": "#dbeafe"},
    "S": {"name": "结构要素", "color": "#7c3aed", "bg": "#ede9fe"},
    "T": {"name": "规范性用词", "color": "#d97706", "bg": "#fef3c7"},
    "W": {"name": "文字表述", "color": "#059669", "bg": "#d1fae5"},
}

SEVERITY_CONFIG = {
    "ERROR": {
        "label": "错误",
        "color": "#dc2626",
        "bg": "#fee2e2",
        "border": "#fca5a5",
    },
    "WARNING": {
        "label": "警告",
        "color": "#d97706",
        "bg": "#fef3c7",
        "border": "#fcd34d",
    },
    "SUGGESTION": {
        "label": "建议",
        "color": "#059669",
        "bg": "#d1fae5",
        "border": "#6ee7b7",
    },
}

AUTOFIX_CODES = {"T001", "W001", "F002", "F003", "F011", "F001", "T006"}


def escape_html(text: str) -> str:
    """转义 HTML 特殊字符"""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def get_category(code: str) -> Dict[str, str]:
    """从问题编号获取分类信息"""
    prefix = code[0].upper() if code else "F"
    return CATEGORY_MAP.get(prefix, CATEGORY_MAP["F"])


def generate_stats(issues: List[Dict]) -> Dict[str, Any]:
    """生成统计数据"""
    severity_counts = {"ERROR": 0, "WARNING": 0, "SUGGESTION": 0}
    category_counts = {}
    code_counts = {}

    for issue in issues:
        sev = issue.get("severity", "WARNING")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

        code = issue.get("code", "")
        prefix = code[0].upper() if code else "F"
        category_counts[prefix] = category_counts.get(prefix, 0) + 1

        code_counts[code] = code_counts.get(code, 0) + 1

    top_codes = sorted(code_counts.items(), key=lambda x: -x[1])[:10]

    return {
        "total": len(issues),
        "severity": severity_counts,
        "category": category_counts,
        "top_codes": top_codes,
    }


def build_issue_rows(issues: List[Dict]) -> str:
    """构建问题表格行 HTML"""
    rows = []
    for i, issue in enumerate(issues):
        code = issue.get("code", "")
        severity = issue.get("severity", "WARNING")
        location = issue.get("location", "")
        description = issue.get("description", "")
        suggestion = issue.get("suggestion", "")
        context = issue.get("context", "")

        sev_cfg = SEVERITY_CONFIG.get(severity, SEVERITY_CONFIG["WARNING"])
        cat = get_category(code)

        # 上下文展开区域
        context_html = ""
        if context:
            context_html = (
                '<div class="issue-detail" id="detail-' + str(i) + '" style="display:none;">'
                '<div class="detail-label">上下文：</div>'
                '<pre class="detail-context">' + escape_html(context) + '</pre>'
                '</div>'
            )

        # 可自动修复标记
        autofix_badge = ""
        if code in AUTOFIX_CODES:
            autofix_badge = '<span class="badge-autofix" title="可自动修复">可修复</span>'

        # 展开按钮
        toggle_btn = ""
        if context:
            toggle_btn = '<button class="btn-toggle" onclick="toggleDetail(' + str(i) + ')" title="展开上下文">&#9654;</button>'

        row = (
            '<tr class="issue-row" data-severity="' + severity + '" '
            'data-category="' + (code[0].upper() if code else 'F') + '" '
            'data-code="' + escape_html(code) + '">'
            '<td class="col-num">' + str(i + 1) + '</td>'
            '<td class="col-code">'
            '<span class="badge-code" style="background:' + cat['bg'] + ';color:' + cat['color'] + ';">' + escape_html(code) + '</span>'
            + autofix_badge +
            '</td>'
            '<td class="col-severity">'
            '<span class="badge-severity" style="background:' + sev_cfg['bg'] + ';color:' + sev_cfg['color'] + ';border-color:' + sev_cfg['border'] + ';">'
            + sev_cfg['label'] +
            '</span>'
            '</td>'
            '<td class="col-location">' + escape_html(location) + '</td>'
            '<td class="col-desc">'
            + escape_html(description) + toggle_btn +
            '</td>'
            '<td class="col-suggestion">' + escape_html(suggestion) + '</td>'
            '</tr>'
            + context_html
        )

        rows.append(row)

    return "\n".join(rows)


def build_category_cards(stats: Dict) -> str:
    """构建分类统计卡片"""
    cards = []
    for prefix, cfg in CATEGORY_MAP.items():
        count = stats["category"].get(prefix, 0)
        card = (
            '<div class="cat-card" style="border-left:4px solid ' + cfg['color'] + ';">'
            '<div class="cat-name" style="color:' + cfg['color'] + ';">' + cfg['name'] + '</div>'
            '<div class="cat-count">' + str(count) + '</div>'
            '</div>'
        )
        cards.append(card)
    return "\n".join(cards)


def build_top_codes(stats: Dict) -> str:
    """构建高频问题类型"""
    if not stats["top_codes"]:
        return '<div class="no-issues">未发现任何问题</div>'

    items = []
    for code, count in stats["top_codes"]:
        cat = get_category(code)
        item = (
            '<div class="top-code-item">'
            '<span class="badge-code" style="background:' + cat['bg'] + ';color:' + cat['color'] + ';">' + escape_html(code) + '</span>'
            '<span class="top-code-count">' + str(count) + ' 次</span>'
            '</div>'
        )
        items.append(item)
    return "\n".join(items)


# CSS 样式（纯字符串，不含 f-string）
CSS_TEXT = """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans SC", sans-serif;
            background: #f8fafc;
            color: #1e293b;
            line-height: 1.6;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        .report-header {
            background: white;
            border-radius: 12px;
            padding: 24px 32px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }

        .report-header h1 {
            font-size: 24px;
            color: #0f172a;
            margin-bottom: 8px;
        }

        .report-meta {
            color: #64748b;
            font-size: 14px;
            display: flex;
            gap: 24px;
            flex-wrap: wrap;
        }

        .report-meta span {
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }

        .stats-overview {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 20px;
        }

        .stat-card {
            background: white;
            border-radius: 12px;
            padding: 20px 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .stat-icon {
            width: 48px;
            height: 48px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            font-weight: bold;
        }

        .stat-info {
            flex: 1;
        }

        .stat-number {
            font-size: 28px;
            font-weight: 700;
            line-height: 1.2;
        }

        .stat-label {
            font-size: 13px;
            color: #64748b;
        }

        .category-stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-bottom: 20px;
        }

        .cat-card {
            background: white;
            border-radius: 10px;
            padding: 16px 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        }

        .cat-name {
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 4px;
        }

        .cat-count {
            font-size: 24px;
            font-weight: 700;
            color: #0f172a;
        }

        .top-codes {
            background: white;
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }

        .top-codes h3 {
            font-size: 15px;
            color: #64748b;
            margin-bottom: 12px;
        }

        .top-code-list {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
        }

        .top-code-item {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .top-code-count {
            font-size: 13px;
            color: #64748b;
        }

        .no-issues {
            color: #059669;
            font-weight: 600;
            padding: 8px 0;
        }

        .filter-bar {
            background: white;
            border-radius: 12px;
            padding: 16px 24px;
            margin-bottom: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }

        .filter-bar label {
            font-size: 14px;
            font-weight: 600;
            color: #475569;
        }

        .filter-btn {
            padding: 6px 16px;
            border: 1.5px solid #e2e8f0;
            border-radius: 20px;
            background: white;
            cursor: pointer;
            font-size: 13px;
            color: #475569;
            transition: all 0.2s;
        }

        .filter-btn:hover {
            border-color: #94a3b8;
        }

        .filter-btn.active {
            background: #1e293b;
            color: white;
            border-color: #1e293b;
        }

        .filter-search {
            flex: 1;
            min-width: 200px;
            padding: 8px 16px;
            border: 1.5px solid #e2e8f0;
            border-radius: 8px;
            font-size: 14px;
            outline: none;
            transition: border-color 0.2s;
        }

        .filter-search:focus {
            border-color: #3b82f6;
        }

        .issues-table-container {
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }

        .issues-table {
            width: 100%;
            border-collapse: collapse;
        }

        .issues-table thead {
            background: #f1f5f9;
        }

        .issues-table th {
            padding: 12px 16px;
            text-align: left;
            font-size: 13px;
            font-weight: 600;
            color: #475569;
            border-bottom: 2px solid #e2e8f0;
            white-space: nowrap;
        }

        .issues-table td {
            padding: 12px 16px;
            font-size: 14px;
            border-bottom: 1px solid #f1f5f9;
            vertical-align: top;
        }

        .issues-table tr.issue-row:hover {
            background: #f8fafc;
        }

        .col-num { width: 40px; color: #94a3b8; text-align: center; }
        .col-code { width: 100px; white-space: nowrap; }
        .col-severity { width: 80px; white-space: nowrap; }
        .col-location { width: 120px; color: #64748b; font-size: 13px; }
        .col-desc { min-width: 200px; }
        .col-suggestion { min-width: 200px; color: #475569; }

        .badge-code {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            font-family: monospace;
        }

        .badge-severity {
            display: inline-block;
            padding: 2px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            border: 1px solid;
        }

        .badge-autofix {
            display: inline-block;
            padding: 1px 6px;
            border-radius: 3px;
            font-size: 11px;
            background: #d1fae5;
            color: #059669;
            margin-left: 4px;
        }

        .btn-toggle {
            background: none;
            border: none;
            cursor: pointer;
            color: #3b82f6;
            font-size: 12px;
            padding: 0 4px;
            transition: transform 0.2s;
        }

        .btn-toggle:hover {
            transform: scale(1.2);
        }

        .issue-detail {
            background: #f8fafc;
            padding: 12px 16px 12px 56px;
            border-bottom: 1px solid #f1f5f9;
        }

        .detail-label {
            font-size: 12px;
            color: #94a3b8;
            margin-bottom: 4px;
        }

        .detail-context {
            font-size: 13px;
            color: #475569;
            background: #fff;
            padding: 8px 12px;
            border-radius: 6px;
            border: 1px solid #e2e8f0;
            white-space: pre-wrap;
            word-break: break-all;
        }

        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #94a3b8;
        }

        .empty-state .icon {
            font-size: 48px;
            margin-bottom: 16px;
        }

        .report-footer {
            text-align: center;
            color: #94a3b8;
            font-size: 13px;
            padding: 20px;
        }

        @media (max-width: 768px) {
            .stats-overview { grid-template-columns: 1fr; }
            .category-stats { grid-template-columns: repeat(2, 1fr); }
            .issues-table { font-size: 13px; }
            .issues-table th, .issues-table td { padding: 8px 10px; }
        }
"""

# JavaScript 代码（纯字符串，不含 f-string）
JS_TEXT = """
        function toggleDetail(index) {
            var detail = document.getElementById('detail-' + index);
            var btn = event.target;
            if (detail.style.display === 'none') {
                detail.style.display = 'block';
                btn.innerHTML = '&#9660;';
            } else {
                detail.style.display = 'none';
                btn.innerHTML = '&#9654;';
            }
        }

        var currentSeverity = 'all';
        var currentCategory = 'all';
        var currentSearch = '';

        function filterIssues(severity, btn) {
            currentSeverity = severity;
            var btns = document.querySelectorAll('[data-filter="ERROR"], [data-filter="WARNING"], [data-filter="SUGGESTION"], [data-filter="all"]');
            btns.forEach(function(b) { b.classList.remove('active'); });
            btn.classList.add('active');
            applyFilters();
        }

        function filterCategory(cat, btn) {
            if (currentCategory === cat) {
                currentCategory = 'all';
                btn.classList.remove('active');
            } else {
                currentCategory = cat;
                var btns = document.querySelectorAll('[data-filter="F"], [data-filter="S"], [data-filter="T"], [data-filter="W"]');
                btns.forEach(function(b) { b.classList.remove('active'); });
                btn.classList.add('active');
            }
            applyFilters();
        }

        function searchIssues(query) {
            currentSearch = query.toLowerCase();
            applyFilters();
        }

        function applyFilters() {
            var rows = document.querySelectorAll('.issue-row');
            var visibleCount = 0;
            rows.forEach(function(row) {
                var severity = row.getAttribute('data-severity');
                var category = row.getAttribute('data-category');
                var text = row.textContent.toLowerCase();

                var severityMatch = (currentSeverity === 'all') || (severity === currentSeverity);
                var categoryMatch = (currentCategory === 'all') || (category === currentCategory);
                var searchMatch = (currentSearch === '') || text.includes(currentSearch);

                if (severityMatch && categoryMatch && searchMatch) {
                    row.style.display = '';
                    visibleCount++;
                } else {
                    row.style.display = 'none';
                    var detail = document.getElementById('detail-' + (row.rowIndex - 1));
                    if (detail) { detail.style.display = 'none'; }
                }
            });

            var allBtn = document.querySelector('[data-filter="all"]');
            if (allBtn) {
                allBtn.textContent = '全部 (' + visibleCount + ')';
            }
        }
"""


def build_html(data: Dict[str, Any]) -> str:
    """生成完整 HTML 报告"""
    issues = data.get("issues", [])
    file_name = data.get("file", "")
    stats = generate_stats(issues)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    display_name = Path(file_name).name if file_name else "未指定"

    sev_e = SEVERITY_CONFIG["ERROR"]
    sev_w = SEVERITY_CONFIG["WARNING"]
    sev_s = SEVERITY_CONFIG["SUGGESTION"]

    has_issues = len(issues) > 0

    # 统计卡片
    stat_cards = (
        '<div class="stat-card" style="border-left:4px solid ' + sev_e['color'] + ';">'
        '<div class="stat-icon" style="background:' + sev_e['bg'] + ';color:' + sev_e['color'] + ';">!</div>'
        '<div class="stat-info">'
        '<div class="stat-number" style="color:' + sev_e['color'] + ';">' + str(stats['severity']['ERROR']) + '</div>'
        '<div class="stat-label">错误 (ERROR) - 必须修改</div>'
        '</div></div>'
        '<div class="stat-card" style="border-left:4px solid ' + sev_w['color'] + ';">'
        '<div class="stat-icon" style="background:' + sev_w['bg'] + ';color:' + sev_w['color'] + ';">!</div>'
        '<div class="stat-info">'
        '<div class="stat-number" style="color:' + sev_w['color'] + ';">' + str(stats['severity']['WARNING']) + '</div>'
        '<div class="stat-label">警告 (WARNING) - 建议修改</div>'
        '</div></div>'
        '<div class="stat-card" style="border-left:4px solid ' + sev_s['color'] + ';">'
        '<div class="stat-icon" style="background:' + sev_s['bg'] + ';color:' + sev_s['color'] + ';">i</div>'
        '<div class="stat-info">'
        '<div class="stat-number" style="color:' + sev_s['color'] + ';">' + str(stats['severity']['SUGGESTION']) + '</div>'
        '<div class="stat-label">建议 (SUGGESTION) - 可选修改</div>'
        '</div></div>'
    )

    # 筛选栏 + 表格 或 空状态
    if has_issues:
        issue_rows = build_issue_rows(issues)
        body_section = (
            '<div class="filter-bar">'
            '<label>筛选：</label>'
            '<button class="filter-btn active" data-filter="all" onclick="filterIssues(\'all\', this)">全部</button>'
            '<button class="filter-btn" data-filter="ERROR" onclick="filterIssues(\'ERROR\', this)">错误</button>'
            '<button class="filter-btn" data-filter="WARNING" onclick="filterIssues(\'WARNING\', this)">警告</button>'
            '<button class="filter-btn" data-filter="SUGGESTION" onclick="filterIssues(\'SUGGESTION\', this)">建议</button>'
            '<span style="color:#cbd5e1;">|</span>'
            '<button class="filter-btn" data-filter="F" onclick="filterCategory(\'F\', this)">格式编排</button>'
            '<button class="filter-btn" data-filter="S" onclick="filterCategory(\'S\', this)">结构要素</button>'
            '<button class="filter-btn" data-filter="T" onclick="filterCategory(\'T\', this)">规范性用词</button>'
            '<button class="filter-btn" data-filter="W" onclick="filterCategory(\'W\', this)">文字表述</button>'
            '<input type="text" class="filter-search" placeholder="搜索问题描述、位置、建议..." oninput="searchIssues(this.value)">'
            '</div>'
            '<div class="issues-table-container">'
            '<table class="issues-table">'
            '<thead><tr>'
            '<th class="col-num">#</th>'
            '<th class="col-code">编号</th>'
            '<th class="col-severity">等级</th>'
            '<th class="col-location">位置</th>'
            '<th class="col-desc">问题描述</th>'
            '<th class="col-suggestion">修改建议</th>'
            '</tr></thead>'
            '<tbody id="issues-tbody">' + issue_rows + '</tbody>'
            '</table>'
            '</div>'
        )
    else:
        body_section = (
            '<div class="issues-table-container">'
            '<div class="empty-state">'
            '<div class="icon">&#10003;</div>'
            '<div>未发现任何问题，文档符合 GB/T 1.1-2020 要求</div>'
            '</div>'
            '</div>'
        )

    # 拼接完整 HTML
    html = (
        '<!DOCTYPE html>\n'
        '<html lang="zh-CN">\n<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<title>标准草稿审查报告 - ' + escape_html(display_name) + '</title>\n'
        '<style>\n' + CSS_TEXT + '\n</style>\n'
        '</head>\n<body>\n'
        '<div class="container">\n'
        # 报告头部
        '<div class="report-header">\n'
        '<h1>标准草稿审查报告</h1>\n'
        '<div class="report-meta">\n'
        '<span>📄 文件：' + escape_html(display_name) + '</span>\n'
        '<span>📅 日期：' + now + '</span>\n'
        '<span>📋 依据：GB/T 1.1-2020</span>\n'
        '<span>🔧 方法：脚本检查 + AI深度审查</span>\n'
        '</div>\n</div>\n'
        # 统计概览
        '<div class="stats-overview">\n' + stat_cards + '\n</div>\n'
        # 分类统计
        '<div class="category-stats">\n' + build_category_cards(stats) + '\n</div>\n'
        # Top 问题
        '<div class="top-codes">\n'
        '<h3>高频问题类型 TOP 10</h3>\n'
        '<div class="top-code-list">\n' + build_top_codes(stats) + '\n</div>\n'
        '</div>\n'
        # 主体内容
        + body_section + '\n'
        # 页脚
        '<div class="report-footer">\n'
        '<p>本报告由标准草稿校审 Skill 自动生成 | 基于 GB/T 1.1-2020</p>\n'
        '<p>审查结果仅供参考，最终以专业审查人员意见为准</p>\n'
        '</div>\n'
        '</div>\n'
        # JavaScript
        '<script>\n' + JS_TEXT + '\n</script>\n'
        '</body>\n</html>'
    )

    return html


def main():
    parser = argparse.ArgumentParser(
        description="生成 HTML 交互式审查报告"
    )
    parser.add_argument("input", nargs="?", help="输入的 JSON 结果文件路径（check_standard.py 的输出）")
    parser.add_argument("--output", "-o", help="输出 HTML 文件路径", required=True)
    parser.add_argument("--issues-json", help="直接传入 issues JSON 字符串")
    parser.add_argument("--file-name", help="原始文档文件名（用于报告头部显示）")

    args = parser.parse_args()

    # 获取数据
    if args.issues_json:
        issues = json.loads(args.issues_json)
        data = {
            "file": args.file_name or "",
            "issues": issues,
            "total_issues": len(issues),
        }
    elif args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"错误：文件不存在：{input_path}")
            sys.exit(1)
        data = json.loads(input_path.read_text(encoding="utf-8"))
    else:
        print("错误：需要提供输入文件或 --issues-json 参数")
        sys.exit(1)

    # 生成 HTML
    html = build_html(data)

    # 写入文件
    output_path = Path(args.output)
    output_path.write_text(html, encoding="utf-8")
    print(f"HTML 报告已生成：{output_path}")
    print(f"问题总数：{data.get('total_issues', len(data.get('issues', [])))}")


if __name__ == "__main__":
    main()
