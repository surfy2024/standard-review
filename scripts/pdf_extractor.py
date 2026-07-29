#!/usr/bin/env python3
"""
PDF 文本结构提取器

从 PDF 文件中提取文本和结构信息，输出与 python-docx 兼容的接口，
使 check_standard.py 的 _extract_structure 无需改动即可处理 PDF。

使用 PyMuPDF (fitz) 提取文本块、字体大小、字体粗细等信息，
通过字体大小聚类分析识别标题层级。

使用方法：
    from pdf_extractor import extract
    doc = extract("standard.pdf")
    for para in doc.paragraphs:
        print(para.text, para.style.name)
"""

import re
from typing import List, Dict, Tuple, Optional
from collections import Counter

try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError("需要安装 PyMuPDF: pip install PyMuPDF")


# ===== 模拟 python-docx 接口 =====

class PDFStyle:
    """模拟 docx.paragraphs[i].style"""
    def __init__(self, name: str = ""):
        self.name = name


class PDFRun:
    """模拟 docx paragraph.runs[i]"""
    def __init__(self, text: str = "", bold: bool = False):
        self.text = text
        self.bold = bold


class PDFParagraph:
    """模拟 docx paragraph 对象"""
    def __init__(self, text: str = "", style_name: str = "", runs: List[PDFRun] = None):
        self.text = text
        self.style = PDFStyle(style_name)
        self.runs = runs if runs is not None else [PDFRun(text)]


class PDFDocument:
    """模拟 docx Document 对象"""
    def __init__(self, paragraphs: List[PDFParagraph]):
        self.paragraphs = paragraphs
        # PDF 没有 part.rels，T007 脚注检查会跳过
        self.part = None


# ===== 核心提取逻辑 =====

class _TextBlock:
    """PDF 文本块的中间表示"""
    def __init__(self, text: str, font_size: float, is_bold: bool,
                 font_name: str, y: float, page: int):
        self.text = text.strip()
        self.font_size = font_size
        self.is_bold = is_bold
        self.font_name = font_name
        self.y = y
        self.page = page
        # 拆分为 runs（保留 bold 信息）
        self.runs: List[PDFRun] = []


def _extract_raw_blocks(pdf_path: str) -> List[_TextBlock]:
    """从 PDF 提取原始文本块"""
    doc = fitz.open(pdf_path)
    blocks: List[_TextBlock] = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_dict = page.get_text("dict")

        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:  # 0 = text block
                continue

            block_lines = block.get("lines", [])
            if not block_lines:
                continue

            # 将 block 内所有 span 收集起来
            spans_data: List[Dict] = []
            for line in block_lines:
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue
                    size = round(span.get("size", 12), 1)
                    flags = span.get("flags", 0)
                    is_bold = bool(flags & 2**4) or "bold" in span.get("font", "").lower()
                    font_name = span.get("font", "")
                    spans_data.append({
                        "text": text,
                        "size": size,
                        "is_bold": is_bold,
                        "font_name": font_name,
                    })

            if not spans_data:
                continue

            # 合并同一 block 内的 spans
            # 如果 spans 在同一行，用空格连接；跨行用换行
            # PyMuPDF 的 block 结构已经按行分组，但我们简化处理：直接拼接
            full_text = ""
            runs: List[PDFRun] = []
            avg_size = sum(s["size"] for s in spans_data) / len(spans_data)
            any_bold = any(s["is_bold"] for s in spans_data)
            font_name = spans_data[0]["font_name"]

            for s in spans_data:
                full_text += s["text"]
                runs.append(PDFRun(s["text"], s["is_bold"]))

            full_text = full_text.strip()
            if not full_text:
                continue

            block_obj = _TextBlock(
                text=full_text,
                font_size=avg_size,
                is_bold=any_bold,
                font_name=font_name,
                y=block.get("bbox", [0, 0, 0, 0])[1],
                page=page_num,
            )
            block_obj.runs = runs
            blocks.append(block_obj)

    doc.close()
    return blocks


def _cluster_font_sizes(blocks: List[_TextBlock]) -> Dict[float, str]:
    """
    对字体大小进行聚类，返回 {font_size: style_name} 映射。

    策略：
    1. 统计各字体大小的出现频率
    2. 最常见的 → 正文（Body Text）
    3. 比正文大的 → 标题（按大小排序映射 Heading 1/2/3）
    4. 比正文小的 → 脚注/页码等（Footnote）
    """
    size_counter: Counter = Counter()
    for b in blocks:
        # 用文本长度作为权重（长文本的大小更能代表正文）
        size_counter[b.font_size] += len(b.text)

    if not size_counter:
        return {}

    # 找到权重最大的字体大小 → 正文
    body_size = size_counter.most_common(1)[0][0]

    # 收集所有不同的字体大小，排序
    all_sizes = sorted(set(b.font_size for b in blocks), reverse=True)

    size_to_style: Dict[float, str] = {}
    heading_level = 0
    for size in all_sizes:
        if size > body_size + 0.5:
            heading_level += 1
            size_to_style[size] = f"Heading {heading_level}"
        elif size < body_size - 0.5:
            size_to_style[size] = "Footnote"
        else:
            size_to_style[size] = "Body Text"

    return size_to_style


def _is_heading_text(text: str) -> bool:
    """通过文本特征判断是否为标题"""
    if not text or len(text) > 80:
        return False

    # 目次条目（含连续点号）不是标题
    if re.search(r'\.{2,}|…', text):
        return False

    # 章编号：数字+空格+文字
    if re.match(r'^\d+\s+\S', text) and len(text) <= 50:
        return True

    # 条编号：数字.数字+空格+文字
    if re.match(r'^\d+\.\d+\s+\S', text) and len(text) <= 50:
        return True

    # 已知非编号标题
    known_headings = ["前言", "引言", "目次", "参考文献", "索引", "概述",
                      "规范性引用文件", "术语和定义"]
    for kh in known_headings:
        if text == kh or text.startswith(kh):
            if len(text) <= 30:
                return True

    # 附录标题
    if re.match(r'^附录\s*[A-Z]', text) and len(text) <= 50:
        return True

    return False


def _merge_adjacent_blocks(blocks: List[_TextBlock]) -> List[_TextBlock]:
    """
    合并相邻的、属于同一段落的文本块。

    PDF 中一个段落可能被拆分成多个 block。合并策略：
    - 字体大小相同
    - 不以句末标点结尾
    - 下一个块不以大写字母或编号开头
    """
    if len(blocks) <= 1:
        return blocks

    merged: List[_TextBlock] = []
    current = blocks[0]

    for next_block in blocks[1:]:
        should_merge = False

        # 同一页面，字体大小相近
        if (current.page == next_block.page and
                abs(current.font_size - next_block.font_size) < 0.5):

            # 当前块不以句末标点结尾，且下一个块不以编号开头
            if (not re.search(r'[。！？；\n]$', current.text) and
                    not re.match(r'^\d+[\s.]', next_block.text) and
                    not _is_heading_text(next_block.text)):
                should_merge = True

        if should_merge:
            # 合并文本和 runs
            current.text = current.text + next_block.text
            current.runs.extend(next_block.runs)
        else:
            merged.append(current)
            current = next_block

    merged.append(current)
    return merged


def extract(pdf_path: str) -> PDFDocument:
    """
    从 PDF 文件提取文本结构，返回兼容 python-docx 接口的 PDFDocument。

    参数:
        pdf_path: PDF 文件路径

    返回:
        PDFDocument 对象，具有 .paragraphs 属性
    """
    # 1. 提取原始文本块
    blocks = _extract_raw_blocks(pdf_path)

    if not blocks:
        return PDFDocument([])

    # 2. 合并相邻段落
    blocks = _merge_adjacent_blocks(blocks)

    # 3. 聚类字体大小，生成样式映射
    size_to_style = _cluster_font_sizes(blocks)

    # 4. 转换为 PDFParagraph
    paragraphs: List[PDFParagraph] = []

    for b in blocks:
        text = b.text.strip()
        if not text:
            continue

        # 获取样式名
        style_name = size_to_style.get(b.font_size, "Body Text")

        # 对于字体大小无法区分的情况，用文本特征补充判断
        if style_name == "Body Text" and _is_heading_text(text):
            # 根据编号格式推断标题级别
            if re.match(r'^\d+\s+\S', text):
                style_name = "Heading 1"
            elif re.match(r'^\d+\.\d+\s+\S', text):
                style_name = "Heading 2"
            elif re.match(r'^\d+\.\d+\.\d+\s+\S', text):
                style_name = "Heading 3"
            else:
                style_name = "Heading 1"

        # 粗体 + 短文本也可能是标题
        if style_name == "Body Text" and b.is_bold and len(text) <= 50:
            if not text.endswith('。') and not re.search(r'\.{2,}|…', text):
                style_name = "Heading 1"

        # 构建 runs
        runs = b.runs if b.runs else [PDFRun(text, b.is_bold)]

        para = PDFParagraph(
            text=text,
            style_name=style_name,
            runs=runs,
        )
        paragraphs.append(para)

    return PDFDocument(paragraphs)


def extract_text(pdf_path: str) -> str:
    """提取 PDF 的纯文本（用于简单场景）"""
    doc = fitz.open(pdf_path)
    text_parts: List[str] = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)
