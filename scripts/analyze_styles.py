#!/usr/bin/env python3
"""
文档样式分析示例脚本

功能：
- 分析文档的样式体系
- 识别标题样式和正文样式
- 输出样式统计报告

使用方法：
    python analyze_styles.py <input.docx>
"""

import sys
from pathlib import Path
from collections import Counter

try:
    from docx import Document
except ImportError:
    print("错误：需要安装 python-docx 库")
    print("请运行：pip install python-docx")
    sys.exit(1)


def analyze_document_styles(doc_path: str) -> None:
    """分析文档样式"""
    
    print(f"\n{'='*60}")
    print(f"文档样式分析报告")
    print(f"{'='*60}")
    print(f"文件：{doc_path}\n")
    
    # 加载文档
    doc = Document(doc_path)
    
    # 统计样式
    style_counter = Counter()
    style_samples = {}
    style_chars = {}
    
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        
        style_name = para.style.name if para.style else "None"
        style_counter[style_name] += 1
        
        # 收集样本
        if style_name not in style_samples:
            style_samples[style_name] = []
        if len(style_samples[style_name]) < 3:
            style_samples[style_name].append(text[:80])
        
        # 统计字符数
        if style_name not in style_chars:
            style_chars[style_name] = []
        style_chars[style_name].append(len(text))
    
    # 输出统计结果
    print(f"总样式数：{len(style_counter)}")
    print(f"总段落数：{sum(style_counter.values())}")
    print(f"\n{'='*60}")
    print("样式详细统计：")
    print(f"{'='*60}\n")
    
    # 按使用频率排序
    for style_name, count in style_counter.most_common():
        samples = style_samples.get(style_name, [])
        chars = style_chars.get(style_name, [])
        avg_chars = sum(chars) / len(chars) if chars else 0
        
        # 判断样式类型
        is_heading = _is_heading_style(style_name, samples, avg_chars)
        style_type = "标题" if is_heading else "正文"
        
        print(f"样式名称：{style_name}")
        print(f"  - 使用次数：{count}")
        print(f"  - 平均长度：{avg_chars:.1f} 字符")
        print(f"  - 样式类型：{style_type}")
        
        if samples:
            print(f"  - 示例内容：")
            for i, sample in enumerate(samples, 1):
                print(f"    {i}. {sample}...")
        
        print()
    
    # 识别标题样式
    print(f"{'='*60}")
    print("识别的标题样式：")
    print(f"{'='*60}\n")
    
    heading_styles = []
    for style_name, count in style_counter.items():
        samples = style_samples.get(style_name, [])
        chars = style_chars.get(style_name, [])
        avg_chars = sum(chars) / len(chars) if chars else 0
        
        if _is_heading_style(style_name, samples, avg_chars):
            heading_styles.append(style_name)
            print(f"- {style_name} ({count} 次)")
    
    if not heading_styles:
        print("（未识别到标题样式）")
    
    print(f"\n{'='*60}")
    print("分析完成！")
    print(f"{'='*60}\n")


def _is_heading_style(style_name: str, samples: list, avg_chars: float) -> bool:
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
        ends_with_period = all(s.endswith('。') for s in samples if s)
        
        if avg_chars > 50 and ends_with_period:
            return False
        
        # 如果样本符合编号格式，可能是标题
        import re
        for sample in samples:
            if re.match(r'^\d+\s+\S', sample) or re.match(r'^\d+\.\d+\s+\S', sample):
                if len(sample) <= 50:
                    return True
    
    return False


def main():
    if len(sys.argv) < 2:
        print("使用方法：python analyze_styles.py <input.docx>")
        sys.exit(1)
    
    doc_path = sys.argv[1]
    
    if not Path(doc_path).exists():
        print(f"错误：文件不存在：{doc_path}")
        sys.exit(1)
    
    analyze_document_styles(doc_path)


if __name__ == "__main__":
    main()