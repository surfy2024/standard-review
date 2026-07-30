#!/usr/bin/env python3
"""
版本对比 Diff 检查器

比较两个版本的标准草稿（.docx/.pdf），只对变更部分运行检查规则，
输出结构化对比报告。

使用方法：
    python diff_checker.py <old_file> <new_file> [--output diff_result.json] [--pretty]
"""

import re
import sys
import json
import argparse
import difflib
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum


# 段落级检查规则（逐段检查，可按段落过滤）
PARAGRAPH_LEVEL_RULES: Set[str] = {
    "T001", "T002", "T003",   # 能愿动词
    "T004", "T005", "T006",   # 用词搭配/引用
    "T007", "T008", "T009",   # 脚注/概述/术语要求条款
    "F001", "F002", "F003",   # 标题标点/单位间距/尺寸
    "F004", "F010", "F011", "F012",  # 公差/目次/公式/脚注
    "W001", "W003",           # 标点/术语加粗
    "S005", "S006",           # 款项归属/附录编号
    "S009",                   # 引言规范
}

# 全局级检查规则（检查整体结构）
GLOBAL_LEVEL_RULES: Set[str] = {
    "S001", "S002", "S003", "S004",  # 结构要素
    "S007",                           # 无内容声明
    "F005", "F006", "F007",          # 图表编号
    "F008", "F009",                   # 标题空格/连字符
}


@dataclass
class ParagraphChange:
    """段落变更记录"""
    change_type: str       # "added" | "deleted" | "modified" | "unchanged"
    old_index: int         # 旧版段落索引（-1 表示新增）
    new_index: int         # 新版段落索引（-1 表示删除）
    old_text: str          # 旧版文本
    new_text: str          # 新版文本
    old_section: str       # 旧版所属章节
    new_section: str       # 新版所属章节
    is_heading: bool       # 是否标题
    similarity: float      # 相似度（修改时的比值）


@dataclass
class DiffIssue:
    """对比检查问题"""
    code: str
    severity: str
    location: str
    description: str
    suggestion: str
    context: str
    diff_type: str         # "new"（新增问题）| "resolved"（已修复）| "persistent"（变更中仍存在）


@dataclass
class StructuralChange:
    """结构变更"""
    change_type: str       # "heading_added" | "heading_deleted" | "heading_modified" | "section_added" | "section_deleted"
    old_text: str
    new_text: str
    section: str
    description: str


class DiffChecker:
    """版本对比检查器"""

    def __init__(self, standard: str = None):
        self.old_checker = None
        self._pending_standard = standard
        self.new_checker = None
        self.old_paragraphs: List[Dict] = []
        self.new_paragraphs: List[Dict] = []
        self.changes: List[ParagraphChange] = []
        self.structural_changes: List[StructuralChange] = []
        self.new_issues: List[DiffIssue] = []
        self.resolved_issues: List[DiffIssue] = []
        self.persistent_issues: List[DiffIssue] = []

    def check(self, old_path: str, new_path: str) -> Dict[str, Any]:
        """执行版本对比检查"""
        from check_standard import StandardChecker

        # 1. 分别检查两个版本
        print(f"正在检查旧版本：{old_path}")
        self.old_checker = StandardChecker(standard=self._pending_standard)
        old_issues = self.old_checker.check(old_path, auto_ref=False)
        self.old_paragraphs = list(self.old_checker.paragraphs)

        print(f"正在检查新版本：{new_path}")
        self.new_checker = StandardChecker(standard=self._pending_standard)
        new_issues = self.new_checker.check(new_path, auto_ref=False)
        self.new_paragraphs = list(self.new_checker.paragraphs)

        # 2. 计算段落级 diff
        print("正在计算段落变更...")
        self._compute_diff()

        # 3. 检测结构变更
        self._detect_structural_changes()

        # 4. 分类问题
        self._classify_issues(old_issues, new_issues)

        # 5. 生成报告
        return self._generate_report(old_path, new_path)

    def _compute_diff(self) -> None:
        """使用 difflib 对齐段落，分类变更"""
        old_texts = [p["text"] for p in self.old_paragraphs]
        new_texts = [p["text"] for p in self.new_paragraphs]

        matcher = difflib.SequenceMatcher(None, old_texts, new_texts, autojunk=False)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                for i, j in zip(range(i1, i2), range(j1, j2)):
                    self.changes.append(ParagraphChange(
                        change_type="unchanged",
                        old_index=i, new_index=j,
                        old_text=old_texts[i], new_text=new_texts[j],
                        old_section=self.old_paragraphs[i].get("section", ""),
                        new_section=self.new_paragraphs[j].get("section", ""),
                        is_heading=self.old_paragraphs[i].get("is_heading", False),
                        similarity=1.0
                    ))
            elif tag == "replace":
                # 尝试配对：可能有不同数量的段落被替换
                old_slice = old_texts[i1:i2]
                new_slice = new_texts[j1:j2]

                # 逐对配对
                max_len = max(len(old_slice), len(new_slice))
                for k in range(max_len):
                    old_idx = i1 + k if k < len(old_slice) else -1
                    new_idx = j1 + k if k < len(new_slice) else -1
                    old_t = old_slice[k] if k < len(old_slice) else ""
                    new_t = new_slice[k] if k < len(new_slice) else ""

                    if old_idx >= 0 and new_idx >= 0:
                        sim = difflib.SequenceMatcher(None, old_t, new_t).ratio()
                        self.changes.append(ParagraphChange(
                            change_type="modified",
                            old_index=old_idx, new_index=new_idx,
                            old_text=old_t, new_text=new_t,
                            old_section=self.old_paragraphs[old_idx].get("section", ""),
                            new_section=self.new_paragraphs[new_idx].get("section", ""),
                            is_heading=self.new_paragraphs[new_idx].get("is_heading", False),
                            similarity=sim
                        ))
                    elif old_idx >= 0:
                        self.changes.append(ParagraphChange(
                            change_type="deleted",
                            old_index=old_idx, new_index=-1,
                            old_text=old_t, new_text="",
                            old_section=self.old_paragraphs[old_idx].get("section", ""),
                            new_section="",
                            is_heading=self.old_paragraphs[old_idx].get("is_heading", False),
                            similarity=0.0
                        ))
                    elif new_idx >= 0:
                        self.changes.append(ParagraphChange(
                            change_type="added",
                            old_index=-1, new_index=new_idx,
                            old_text="", new_text=new_t,
                            old_section="",
                            new_section=self.new_paragraphs[new_idx].get("section", ""),
                            is_heading=self.new_paragraphs[new_idx].get("is_heading", False),
                            similarity=0.0
                        ))
            elif tag == "delete":
                for i in range(i1, i2):
                    self.changes.append(ParagraphChange(
                        change_type="deleted",
                        old_index=i, new_index=-1,
                        old_text=old_texts[i], new_text="",
                        old_section=self.old_paragraphs[i].get("section", ""),
                        new_section="",
                        is_heading=self.old_paragraphs[i].get("is_heading", False),
                        similarity=0.0
                    ))
            elif tag == "insert":
                for j in range(j1, j2):
                    self.changes.append(ParagraphChange(
                        change_type="added",
                        old_index=-1, new_index=j,
                        old_text="", new_text=new_texts[j],
                        old_section="",
                        new_section=self.new_paragraphs[j].get("section", ""),
                        is_heading=self.new_paragraphs[j].get("is_heading", False),
                        similarity=0.0
                    ))

    def _detect_structural_changes(self) -> None:
        """检测结构变更（标题增删改、章节变化）"""
        old_headings = {h["text"]: h for h in self.old_checker.headings}
        new_headings = {h["text"]: h for h in self.new_checker.headings}

        old_set = set(old_headings.keys())
        new_set = set(new_headings.keys())

        # 新增标题
        for text in new_set - old_set:
            h = new_headings[text]
            section = h.get("section", "")
            self.structural_changes.append(StructuralChange(
                change_type="heading_added",
                old_text="", new_text=text,
                section=section,
                description=f"新增标题：\"{text}\""
            ))

        # 删除标题
        for text in old_set - new_set:
            h = old_headings[text]
            section = h.get("section", "")
            self.structural_changes.append(StructuralChange(
                change_type="heading_deleted",
                old_text=text, new_text="",
                section=section,
                description=f"删除标题：\"{text}\""
            ))

        # 修改的标题（通过 diff 中的 modified 标题检测）
        for change in self.changes:
            if change.change_type == "modified" and change.is_heading:
                if change.old_text != change.new_text:
                    self.structural_changes.append(StructuralChange(
                        change_type="heading_modified",
                        old_text=change.old_text,
                        new_text=change.new_text,
                        section=change.new_section,
                        description=f"标题修改：\"{change.old_text}\" -> \"{change.new_text}\""
                    ))

    def _classify_issues(self, old_issues: List, new_issues: List) -> None:
        """分类问题：新增、已修复、持续存在"""

        # 获取变更段落的新版索引集合
        changed_new_indices: Set[int] = set()
        for change in self.changes:
            if change.change_type in ("added", "modified"):
                if change.new_index >= 0:
                    changed_new_indices.add(change.new_index)

        # 获取变更段落的旧版索引集合
        changed_old_indices: Set[int] = set()
        for change in self.changes:
            if change.change_type in ("deleted", "modified"):
                if change.old_index >= 0:
                    changed_old_indices.add(change.old_index)

        # 从 location 字段提取段落索引
        def extract_index(location: str) -> int:
            match = re.search(r'段落\s*(\d+)', location)
            return int(match.group(1)) if match else -1

        def extract_position(location: str) -> int:
            match = re.search(r'位置\s*(\d+)', location)
            return int(match.group(1)) if match else -1

        # 构建问题指纹（code + description 去重）
        def issue_fingerprint(issue) -> str:
            return f"{issue.code}:{issue.description}"

        old_fingerprints = {issue_fingerprint(i) for i in old_issues}
        new_fingerprints = {issue_fingerprint(i) for i in new_issues}

        # 分类新版本的问题
        for issue in new_issues:
            fp = issue_fingerprint(issue)
            para_idx = extract_index(issue.location)
            pos_idx = extract_position(issue.location)
            target_idx = para_idx if para_idx >= 0 else pos_idx

            is_paragraph_level = issue.code in PARAGRAPH_LEVEL_RULES
            is_global = issue.code in GLOBAL_LEVEL_RULES

            if is_paragraph_level:
                if target_idx >= 0 and target_idx in changed_new_indices:
                    # 段落级问题在变更段落中：新增或持续存在
                    if fp not in old_fingerprints:
                        self.new_issues.append(DiffIssue(
                            code=issue.code, severity=issue.severity,
                            location=issue.location, description=issue.description,
                            suggestion=issue.suggestion, context=issue.context,
                            diff_type="new"
                        ))
                    else:
                        self.persistent_issues.append(DiffIssue(
                            code=issue.code, severity=issue.severity,
                            location=issue.location, description=issue.description,
                            suggestion=issue.suggestion, context=issue.context,
                            diff_type="persistent"
                        ))
                elif target_idx < 0:
                    # 无法定位段落（如脚注），按指纹判断
                    if fp in old_fingerprints:
                        self.persistent_issues.append(DiffIssue(
                            code=issue.code, severity=issue.severity,
                            location=issue.location, description=issue.description,
                            suggestion=issue.suggestion, context=issue.context,
                            diff_type="persistent"
                        ))
                    else:
                        self.new_issues.append(DiffIssue(
                            code=issue.code, severity=issue.severity,
                            location=issue.location, description=issue.description,
                            suggestion=issue.suggestion, context=issue.context,
                            diff_type="new"
                        ))
                else:
                    # 段落级问题在未修改段落中：持续存在
                    self.persistent_issues.append(DiffIssue(
                        code=issue.code, severity=issue.severity,
                        location=issue.location, description=issue.description,
                        suggestion=issue.suggestion, context=issue.context,
                        diff_type="persistent"
                    ))
            elif is_global:
                # 全局级问题：对比新旧指纹
                if fp not in old_fingerprints:
                    self.new_issues.append(DiffIssue(
                        code=issue.code, severity=issue.severity,
                        location=issue.location, description=issue.description,
                        suggestion=issue.suggestion, context=issue.context,
                        diff_type="new"
                    ))
                else:
                    self.persistent_issues.append(DiffIssue(
                        code=issue.code, severity=issue.severity,
                        location=issue.location, description=issue.description,
                        suggestion=issue.suggestion, context=issue.context,
                        diff_type="persistent"
                    ))

        # 已修复的问题：旧版有、新版没有
        for issue in old_issues:
            fp = issue_fingerprint(issue)
            if fp not in new_fingerprints:
                self.resolved_issues.append(DiffIssue(
                    code=issue.code, severity=issue.severity,
                    location=issue.location, description=issue.description,
                    suggestion=issue.suggestion, context=issue.context,
                    diff_type="resolved"
                ))

    def _generate_report(self, old_path: str, new_path: str) -> Dict[str, Any]:
        """生成对比报告"""
        # 统计变更
        added = sum(1 for c in self.changes if c.change_type == "added")
        deleted = sum(1 for c in self.changes if c.change_type == "deleted")
        modified = sum(1 for c in self.changes if c.change_type == "modified")
        unchanged = sum(1 for c in self.changes if c.change_type == "unchanged")

        return {
            "old_file": old_path,
            "new_file": new_path,
            "summary": {
                "paragraph_changes": {
                    "added": added,
                    "deleted": deleted,
                    "modified": modified,
                    "unchanged": unchanged,
                    "total_changed": added + deleted + modified
                },
                "structural_changes": len(self.structural_changes),
                "new_issues": len(self.new_issues),
                "resolved_issues": len(self.resolved_issues),
                "persistent_issues": len(self.persistent_issues),
            },
            "structural_changes": [asdict(s) for s in self.structural_changes],
            "paragraph_changes": [
                asdict(c) for c in self.changes if c.change_type != "unchanged"
            ],
            "new_issues": [asdict(i) for i in self.new_issues],
            "resolved_issues": [asdict(i) for i in self.resolved_issues],
            "persistent_issues": [asdict(i) for i in self.persistent_issues],
        }


def generate_diff_markdown_report(report: Dict[str, Any]) -> str:
    """生成 Markdown 格式的对比报告"""
    lines = []
    s = report["summary"]

    lines.append("# 标准草稿版本对比审查报告\n")
    lines.append(f"- **旧版本**：{report['old_file']}")
    lines.append(f"- **新版本**：{report['new_file']}\n")

    # 变更概览
    lines.append("## 变更概览\n")
    pc = s["paragraph_changes"]
    lines.append("| 变更类型 | 数量 |")
    lines.append("|---------|------|")
    lines.append(f"| 新增段落 | {pc['added']} |")
    lines.append(f"| 删除段落 | {pc['deleted']} |")
    lines.append(f"| 修改段落 | {pc['modified']} |")
    lines.append(f"| 未变段落 | {pc['unchanged']} |")
    lines.append(f"| **变更总计** | **{pc['total_changed']}** |\n")

    lines.append(f"- 结构变更：{s['structural_changes']} 处")
    lines.append(f"- 新增问题：{s['new_issues']} 个")
    lines.append(f"- 已修复问题：{s['resolved_issues']} 个")
    lines.append(f"- 持续存在问题：{s['persistent_issues']} 个\n")

    # 结构变更
    if report["structural_changes"]:
        lines.append("## 结构变更\n")
        for sc in report["structural_changes"]:
            icon = {"heading_added": "[+]", "heading_deleted": "[-]",
                    "heading_modified": "[~]"}.get(sc["change_type"], "[?]")
            lines.append(f"- {icon} {sc['description']}")
        lines.append("")

    # 新增问题
    if report["new_issues"]:
        lines.append("## 新增问题（变更引入）\n")
        lines.append("| 编号 | 严重等级 | 位置 | 问题描述 | 修改建议 |")
        lines.append("|------|---------|------|---------|---------|")
        for issue in report["new_issues"]:
            lines.append(
                f"| {issue['code']} | {issue['severity']} | {issue['location']} "
                f"| {issue['description']} | {issue['suggestion']} |"
            )
        lines.append("")

    # 已修复问题
    if report["resolved_issues"]:
        lines.append("## 已修复问题\n")
        lines.append("| 编号 | 严重等级 | 位置 | 问题描述 |")
        lines.append("|------|---------|------|---------|")
        for issue in report["resolved_issues"]:
            lines.append(
                f"| {issue['code']} | {issue['severity']} | {issue['location']} "
                f"| {issue['description']} |"
            )
        lines.append("")

    # 持续存在问题
    if report["persistent_issues"]:
        lines.append("## 持续存在问题（变更未涉及）\n")
        lines.append("| 编号 | 严重等级 | 位置 | 问题描述 | 修改建议 |")
        lines.append("|------|---------|------|---------|---------|")
        for issue in report["persistent_issues"]:
            lines.append(
                f"| {issue['code']} | {issue['severity']} | {issue['location']} "
                f"| {issue['description']} | {issue['suggestion']} |"
            )
        lines.append("")

    # 段落变更详情
    if report["paragraph_changes"]:
        lines.append("## 段落变更详情\n")
        for pc in report["paragraph_changes"]:
            icon = {"added": "[+]", "deleted": "[-]", "modified": "[~]"}.get(
                pc["change_type"], "[?]")
            if pc["change_type"] == "added":
                lines.append(f"### {icon} 新增段落（位置：{pc['new_index']}）\n")
                lines.append(f"> {pc['new_text'][:200]}\n")
            elif pc["change_type"] == "deleted":
                lines.append(f"### {icon} 删除段落（原位置：{pc['old_index']}）\n")
                lines.append(f"> {pc['old_text'][:200]}\n")
            elif pc["change_type"] == "modified":
                sim_pct = int(pc["similarity"] * 100)
                lines.append(f"### {icon} 修改段落（相似度：{sim_pct}%）\n")
                lines.append(f"**旧版**（位置 {pc['old_index']}）：")
                lines.append(f"> {pc['old_text'][:200]}\n")
                lines.append(f"**新版**（位置 {pc['new_index']}）：")
                lines.append(f"> {pc['new_text'][:200]}\n")

    if not report["new_issues"] and not report["resolved_issues"]:
        lines.append("## 结论\n")
        lines.append("本次版本变更未引入新的审查问题，也未修复已有问题。\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="标准草稿版本对比检查工具"
    )
    parser.add_argument("old_file", help="旧版本文件路径（.docx 或 .pdf）")
    parser.add_argument("new_file", help="新版本文件路径（.docx 或 .pdf）")
    parser.add_argument("--output", "-o", help="输出 JSON 结果文件路径（可选）")
    parser.add_argument("--pretty", "-p", action="store_true", help="格式化输出 JSON")
    parser.add_argument("--markdown", "-m", help="输出 Markdown 报告文件路径（可选）")
    parser.add_argument(
        "--standard", "-s",
        help="指定标准类型（默认自动检测）：gb-national, gb-industry, "
             "gb-local, gb-enterprise, gb-group"
    )

    args = parser.parse_args()

    # 检查文件
    for f, label in [(args.old_file, "旧版本"), (args.new_file, "新版本")]:
        path = Path(f)
        if not path.exists():
            print(f"错误：{label}文件不存在：{path}")
            sys.exit(1)
        if path.suffix.lower() not in (".docx", ".pdf"):
            print(f"错误：{label}文件格式不支持：{path.suffix}（仅支持 .docx 和 .pdf）")
            sys.exit(1)

    # 执行对比检查
    checker = DiffChecker(standard=args.standard)
    report = checker.check(args.old_file, args.new_file)

    # 输出 JSON
    if args.output:
        output_path = Path(args.output)
        indent = 2 if args.pretty else None
        output_path.write_text(json.dumps(report, indent=indent, ensure_ascii=False), encoding="utf-8")
        print(f"对比检查完成，JSON 结果已保存到：{output_path}")
    else:
        indent = 2 if args.pretty else None
        print(json.dumps(report, indent=indent, ensure_ascii=False))

    # 输出 Markdown 报告
    if args.markdown:
        md_path = Path(args.markdown)
        md_content = generate_diff_markdown_report(report)
        md_path.write_text(md_content, encoding="utf-8")
        print(f"Markdown 报告已保存到：{md_path}")

    # 打印摘要
    s = report["summary"]
    print(f"\n=== 对比检查摘要 ===")
    print(f"段落变更：{s['paragraph_changes']['total_changed']} 处"
          f"（新增 {s['paragraph_changes']['added']}, "
          f"删除 {s['paragraph_changes']['deleted']}, "
          f"修改 {s['paragraph_changes']['modified']}）")
    print(f"结构变更：{s['structural_changes']} 处")
    print(f"新增问题：{s['new_issues']} 个")
    print(f"已修复：{s['resolved_issues']} 个")
    print(f"持续存在：{s['persistent_issues']} 个")


if __name__ == "__main__":
    main()
