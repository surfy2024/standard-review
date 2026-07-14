#!/usr/bin/env python3
"""
GB/T 1.1-2020 标准草稿自动化检查脚本（改进版）

功能：
1. 分析文档样式体系，智能识别标题
2. 执行结构化规则检查（编号连续性、能愿动词、格式等）
3. 输出 JSON 格式的检查结果

使用方法：
    python check_standard.py <input.docx> [--output result.json] [--analyze-styles]
"""

import re
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from collections import Counter


class Severity(Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    SUGGESTION = "SUGGESTION"


@dataclass
class Issue:
    """检查问题"""
    code: str          # 问题编号，如 S001, F001
    severity: str      # 严重等级：ERROR/WARNING/SUGGESTION
    location: str      # 位置描述
    description: str   # 问题描述
    suggestion: str    # 修改建议
    context: str = ""  # 上下文信息（可选）


class StyleAnalyzer:
    """文档样式分析器"""
    
    def __init__(self):
        self.style_stats: Dict[str, Dict] = {}
        self.heading_styles: List[str] = []
        
    def analyze(self, doc) -> Dict[str, Any]:
        """分析文档样式"""
        style_counter = Counter()
        style_samples: Dict[str, List[str]] = {}
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            
            style_name = para.style.name if para.style else "None"
            style_counter[style_name] += 1
            
            # 收集样式样本
            if style_name not in style_samples:
                style_samples[style_name] = []
            if len(style_samples[style_name]) < 3:
                style_samples[style_name].append(text[:80])
        
        # 分析样式特征
        for style_name, count in style_counter.items():
            samples = style_samples.get(style_name, [])
            
            # 判断是否为标题样式
            is_heading = self._is_heading_style(style_name, samples)
            
            self.style_stats[style_name] = {
                "count": count,
                "samples": samples,
                "is_heading": is_heading
            }
            
            if is_heading:
                self.heading_styles.append(style_name)
        
        return {
            "style_stats": self.style_stats,
            "heading_styles": self.heading_styles,
            "total_styles": len(style_counter)
        }
    
    def _is_heading_style(self, style_name: str, samples: List[str]) -> bool:
        """判断样式是否为标题样式"""
        
        # 1. 明确的标题样式关键词
        heading_keywords = ["章标题", "一级条标题", "标题 1", "Heading 1", "标题"]
        
        # 2. 明确的非标题样式关键词
        non_heading_keywords = ["无标题条", "正文", "Body Text", "Normal"]
        
        # 检查样式名称
        for keyword in heading_keywords:
            if keyword in style_name:
                # 但要排除"无标题条"
                if "无标题条" not in style_name:
                    return True
        
        for keyword in non_heading_keywords:
            if keyword in style_name:
                return False
        
        # 3. 根据样本内容判断
        if samples:
            # 如果样本都是长文本（>50字符）且以句号结尾，可能是正文
            avg_length = sum(len(s) for s in samples) / len(samples)
            ends_with_period = all(s.endswith('。') for s in samples if s)
            
            if avg_length > 50 and ends_with_period:
                return False
            
            # 如果样本符合编号格式，可能是标题
            for sample in samples:
                if re.match(r'^\d+\s+\S', sample) or re.match(r'^\d+\.\d+\s+\S', sample):
                    if len(sample) <= 50:
                        return True
        
        return False


class StandardChecker:
    """GB/T 1.1-2020 标准草稿检查器"""
    
    def __init__(self):
        self.issues: List[Issue] = []
        self.paragraphs: List[Dict] = []
        self.headings: List[Dict] = []
        self.style_analyzer = StyleAnalyzer()
        
    def check(self, docx_path: str, analyze_styles: bool = False) -> List[Issue]:
        """执行检查"""
        try:
            from docx import Document
        except ImportError:
            print("错误：需要安装 python-docx 库")
            print("请运行：pip install python-docx")
            sys.exit(1)
        
        doc = Document(docx_path)
        
        # 分析样式（可选）
        if analyze_styles:
            style_info = self.style_analyzer.analyze(doc)
            print("\n=== 文档样式分析 ===")
            print(f"总样式数: {style_info['total_styles']}")
            print(f"标题样式: {', '.join(style_info['heading_styles'])}")
        
        # 提取文档结构
        self._extract_structure(doc)
        
        # 执行各项检查
        self._check_structure()
        self._check_headings()
        self._check_modal_verbs()
        self._check_number_unit_spacing()
        self._check_figure_table_numbering()
        self._check_references()
        self._check_percentage_tolerance()
        
        return self.issues
    
    def _extract_structure(self, doc) -> None:
        """提取文档结构"""
        for i, para in enumerate(doc.paragraphs):
            text = para.text.strip()
            if not text:
                continue
            
            style_name = para.style.name if para.style else ""
            
            # 智能识别标题
            is_heading = self._is_heading(text, style_name)
            
            item = {
                "index": i,
                "text": text,
                "style": style_name,
                "is_heading": is_heading
            }
            
            self.paragraphs.append(item)
            
            if is_heading:
                self.headings.append(item)
    
    def _is_heading(self, text: str, style_name: str) -> bool:
        """智能判断是否为标题"""
        
        # 1. 使用样式分析器的结果
        if style_name in self.style_analyzer.heading_styles:
            # 额外检查：长度和内容
            if len(text) <= 50 and not text.endswith('。'):
                return True
        
        # 2. 检查编号格式
        # 章编号：数字+空格+文字（如"1 范围"）
        if re.match(r'^\d+\s+\S', text):
            # 排除目录项（包含制表符）
            if '\t' not in text:
                # 长度检查
                if len(text) <= 50:
                    return True
        
        # 条编号：数字.数字+空格+文字（如"5.1 总体要求"）
        if re.match(r'^\d+\.\d+\s+\S', text):
            if '\t' not in text and len(text) <= 50:
                return True
        
        return False
    
    def _add_issue(self, code: str, severity: Severity, location: str,
                   description: str, suggestion: str, context: str = "") -> None:
        """添加问题"""
        self.issues.append(Issue(
            code=code,
            severity=severity.value,
            location=location,
            description=description,
            suggestion=suggestion,
            context=context
        ))
    
    def _check_structure(self) -> None:
        """检查结构要素"""
        # 检查必备要素
        required_elements = ["前言", "范围"]
        heading_texts = [h["text"] for h in self.headings]
        all_text = " ".join([p["text"] for p in self.paragraphs])
        
        for elem in required_elements:
            found_in_heading = any(elem in h for h in heading_texts)
            found_in_text = elem in all_text
            
            if not found_in_text:
                self._add_issue(
                    "S001",
                    Severity.ERROR,
                    "整体",
                    f"缺少必备要素\"{elem}\"",
                    f"补充\"{elem}\"要素"
                )
            elif not found_in_heading:
                # 要素存在但可能格式不规范
                self._add_issue(
                    "S010",
                    Severity.WARNING,
                    "整体",
                    f"\"{elem}\"要素可能存在但格式不规范",
                    f"检查\"{elem}\"是否使用了正确的标题样式"
                )
        
        # 检查要素顺序
        element_order = []
        for h in self.headings:
            text = h["text"]
            if "前言" in text:
                element_order.append("前言")
            elif "范围" in text:
                element_order.append("范围")
            elif "规范性引用文件" in text:
                element_order.append("规范性引用文件")
        
        expected_order = ["前言", "范围", "规范性引用文件"]
        for i, elem in enumerate(expected_order):
            if elem in element_order:
                idx = element_order.index(elem)
                for j in range(i):
                    if expected_order[j] in element_order:
                        if element_order.index(expected_order[j]) > idx:
                            self._add_issue(
                                "S002",
                                Severity.ERROR,
                                "整体",
                                f"要素顺序错误：\"{elem}\"应在\"{expected_order[j]}\"之后",
                                "调整要素顺序为：前言->范围->规范性引用文件->..."
                            )
                            break
    
    def _check_headings(self) -> None:
        """检查标题格式"""
        chapter_pattern = re.compile(r'^(\d+)\s+')
        clause_pattern = re.compile(r'^(\d+\.\d+)\s+')
        
        chapter_numbers = []
        clause_numbers = []
        
        for h in self.headings:
            text = h["text"]
            
            # 检查标题末尾标点
            if text and text[-1] in '：:，,。.、；;!！':
                self._add_issue(
                    "F001",
                    Severity.ERROR,
                    f"位置 {h['index']}",
                    f"标题末尾有标点：\"{text}\"",
                    "删除末尾标点",
                    f"样式: {h['style']}"
                )
            
            # 提取章编号
            chapter_match = chapter_pattern.match(text)
            if chapter_match:
                num = int(chapter_match.group(1))
                chapter_numbers.append(num)
            
            # 提取条编号
            clause_match = clause_pattern.match(text)
            if clause_match:
                clause_numbers.append(clause_match.group(1))
        
        # 检查章编号连续性
        if chapter_numbers:
            chapter_numbers = sorted(set(chapter_numbers))
            for i in range(len(chapter_numbers) - 1):
                if chapter_numbers[i+1] - chapter_numbers[i] > 1:
                    self._add_issue(
                        "S003",
                        Severity.ERROR,
                        "整体",
                        f"章编号不连续：从{chapter_numbers[i]}跳到{chapter_numbers[i+1]}",
                        "补充缺失章节或重新编号"
                    )
    
    def _check_modal_verbs(self) -> None:
        """检查能愿动词使用"""
        # 禁用词
        forbidden_words = ["必须", "应当", "不得"]
        # 弱化词
        weakening_words = ["尽量", "尽可能", "考虑", "优先考虑", "充分考虑", "避免", "慎重"]
        # 限定词
        limiting_words = ["通常", "一般", "原则上"]
        
        for para in self.paragraphs:
            text = para["text"]
            
            # 检查禁用词
            for word in forbidden_words:
                if word in text:
                    replacement = "应" if word != "不得" else "不应"
                    self._add_issue(
                        "T001",
                        Severity.ERROR,
                        f"段落 {para['index']}",
                        f"使用禁用能愿动词\"{word}\"",
                        f"改为\"{replacement}\"",
                        text[:100]
                    )
            
            # 检查"应"与弱化词搭配
            if "应" in text:
                for word in weakening_words:
                    if word in text:
                        self._add_issue(
                            "T002",
                            Severity.ERROR,
                            f"段落 {para['index']}",
                            f"\"应\"与弱化词\"{word}\"搭配",
                            f"改为\"宜{word}\"",
                            text[:100]
                        )
            
            # 检查"应"与限定词搭配
            for word in limiting_words:
                if f"{word}应" in text or f"{word} 应" in text:
                    self._add_issue(
                        "T003",
                        Severity.WARNING,
                        f"段落 {para['index']}",
                        f"\"应\"与限定词\"{word}\"搭配",
                        f"改为\"{word}宜\"",
                        text[:100]
                    )
    
    def _check_number_unit_spacing(self) -> None:
        """检查数字与单位间距"""
        # 常见单位
        units = ["mm", "cm", "m", "km", "g", "kg", "t", "ml", "L", "W", "kW",
                 "V", "A", "Hz", "kHz", "MHz", "Pa", "kPa", "MPa", "J", "kJ",
                 "C", "K", "min", "h", "s", "ms", "r", "r/min"]
        
        for para in self.paragraphs:
            text = para["text"]
            
            # 检查数字+单位无空格
            for unit in units:
                # 匹配数字直接接单位（无空格）
                pattern = re.compile(rf'(\d){unit}(?![a-zA-Z])')
                if pattern.search(text):
                    self._add_issue(
                        "F002",
                        Severity.WARNING,
                        f"段落 {para['index']}",
                        f"数字与单位\"{unit}\"之间缺少空格",
                        "在数字与单位间添加空格"
                    )
    
    def _check_figure_table_numbering(self) -> None:
        """检查图表编号"""
        # 提取图编号
        figure_pattern = re.compile(r'图\s*(\d+)')
        table_pattern = re.compile(r'表\s*(\d+)')
        
        figure_numbers = []
        table_numbers = []
        
        for para in self.paragraphs:
            text = para["text"]
            
            # 提取图编号
            for match in figure_pattern.finditer(text):
                figure_numbers.append(int(match.group(1)))
            
            # 提取表编号
            for match in table_pattern.finditer(text):
                table_numbers.append(int(match.group(1)))
        
        # 检查图编号连续性
        if figure_numbers:
            figure_numbers = sorted(set(figure_numbers))
            for i in range(len(figure_numbers) - 1):
                if figure_numbers[i+1] - figure_numbers[i] > 1:
                    self._add_issue(
                        "F005",
                        Severity.ERROR,
                        "整体",
                        f"图编号不连续：从图{figure_numbers[i]}跳到图{figure_numbers[i+1]}",
                        "重新编号或补充缺失图"
                    )
        
        # 检查表编号连续性
        if table_numbers:
            table_numbers = sorted(set(table_numbers))
            for i in range(len(table_numbers) - 1):
                if table_numbers[i+1] - table_numbers[i] > 1:
                    self._add_issue(
                        "F006",
                        Severity.ERROR,
                        "整体",
                        f"表编号不连续：从表{table_numbers[i]}跳到表{table_numbers[i+1]}",
                        "重新编号或补充缺失表"
                    )
        
        # 检查分表编号
        for para in self.paragraphs:
            text = para["text"]
            if re.search(r'表\d+[a-zA-Z]', text):
                self._add_issue(
                    "F007",
                    Severity.ERROR,
                    f"段落 {para['index']}",
                    "存在分表编号（如表2a）",
                    "合并为一个表或分别编号"
                )
    
    def _check_references(self) -> None:
        """检查引用格式"""
        # 注日期引用格式（应为 GB/T XXXXX-YYYY，用一字线）
        dated_ref_pattern = re.compile(r'GB/T\s*\d+[:：]\d{4}')
        # 页码引用
        page_ref_pattern = re.compile(r'第\s*\d+\s*页')
        
        for para in self.paragraphs:
            text = para["text"]
            
            # 检查注日期引用格式
            if dated_ref_pattern.search(text):
                self._add_issue(
                    "T006",
                    Severity.ERROR,
                    f"段落 {para['index']}",
                    "注日期引用格式错误（使用了冒号）",
                    "使用一字线连接，如 GB/T XXXXX-2020"
                )
            
            # 检查页码引用
            if page_ref_pattern.search(text):
                self._add_issue(
                    "T005",
                    Severity.ERROR,
                    f"段落 {para['index']}",
                    "引用中包含页码",
                    "引用内容编号而非页码，如\"第3章\"\"5.2条\""
                )
    
    def _check_percentage_tolerance(self) -> None:
        """检查百分率公差格式"""
        # 匹配错误的百分率公差格式
        wrong_tolerance_pattern = re.compile(r'\d+\s*[+＋]\s*[-－]\s*\d+\s*%')
        
        for para in self.paragraphs:
            text = para["text"]
            
            if wrong_tolerance_pattern.search(text):
                self._add_issue(
                    "F004",
                    Severity.ERROR,
                    f"段落 {para['index']}",
                    "百分率公差格式错误",
                    "使用括号包裹，如 (65+/-2)%"
                )


def main():
    parser = argparse.ArgumentParser(
        description="GB/T 1.1-2020 标准草稿自动化检查工具（改进版）"
    )
    parser.add_argument("input", help="输入的 .docx 文件路径")
    parser.add_argument("--output", "-o", help="输出 JSON 结果文件路径（可选）")
    parser.add_argument("--pretty", "-p", action="store_true", help="格式化输出 JSON")
    parser.add_argument("--analyze-styles", "-a", action="store_true", help="分析文档样式")
    
    args = parser.parse_args()
    
    # 检查输入文件
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误：文件不存在：{input_path}")
        sys.exit(1)
    
    if input_path.suffix.lower() != ".docx":
        print(f"警告：文件扩展名不是 .docx：{input_path}")
    
    # 执行检查
    checker = StandardChecker()
    issues = checker.check(str(input_path), analyze_styles=args.analyze_styles)
    
    # 输出结果
    result = {
        "file": str(input_path),
        "total_issues": len(issues),
        "summary": {
            "ERROR": sum(1 for i in issues if i.severity == "ERROR"),
            "WARNING": sum(1 for i in issues if i.severity == "WARNING"),
            "SUGGESTION": sum(1 for i in issues if i.severity == "SUGGESTION")
        },
        "issues": [asdict(i) for i in issues]
    }
    
    # 输出到文件或控制台
    if args.output:
        output_path = Path(args.output)
        indent = 2 if args.pretty else None
        output_path.write_text(json.dumps(result, indent=indent, ensure_ascii=False), encoding="utf-8")
        print(f"检查完成，结果已保存到：{output_path}")
    else:
        indent = 2 if args.pretty else None
        print(json.dumps(result, indent=indent, ensure_ascii=False))
    
    # 返回退出码
    if result["summary"]["ERROR"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()