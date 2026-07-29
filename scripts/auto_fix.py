#!/usr/bin/env python3
"""
GB/T 1.1-2020 标准草稿自动修复器

功能：
1. 接收 Checker 的检查结果，筛选可自动修复的确定性规则
2. 在 .docx 的 run 级别应用修复，生成带 Word Track Changes 标记的修订版
3. 输出修复日志，记录每处修改的详细信息

可自动修复的规则：
- T001: 禁用能愿动词替换（必须→应, 应当→应, 不得→不应）
- W001: 中文正文半角标点→全角标点（,→， :→： ;→；）
- F002: 数字与单位间补空格（80mm→80 mm）
- F003: 尺寸表述规范化（80x25x50 mm→80 mm x 25 mm x 50 mm）
- F011: 公式编号补括号（公式3→公式(3)）
- F001: 标题末尾标点删除
- T006: 注日期引用冒号→一字线（GB/T XXXXX:YYYY→GB/T XXXXX-YYYY）

使用方法：
    from auto_fix import AutoFixer
    fixer = AutoFixer(doc, issues)
    fixer.fix("revised.docx")
"""

import re
import copy
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from lxml import etree

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
W = f'{{{W_NS}}}'
XML_NS = 'http://www.w3.org/XML/1998/namespace'


class FixRecord:
    """修复记录"""
    def __init__(self, code: str, paragraph_idx: int, original: str,
                 fixed: str, description: str):
        self.code = code
        self.paragraph_idx = paragraph_idx
        self.original = original
        self.fixed = fixed
        self.description = description

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "paragraph": self.paragraph_idx,
            "original": self.original,
            "fixed": self.fixed,
            "description": self.description,
        }


class AutoFixer:
    """自动修复器"""

    FIXABLE_RULES = {
        'T001', 'W001', 'F002', 'F003', 'F011', 'F001', 'T006',
    }

    # T001: 禁用词替换映射
    MODAL_VERB_REPLACEMENTS = {
        '必须': '应',
        '应当': '应',
        '不得': '不应',
    }

    # W001: 半角→全角标点
    PUNCTUATION_MAP = {
        ',': '，',
        ':': '：',
        ';': '；',
    }

    # F002: 常见单位列表
    UNITS = [
        "mm", "cm", "km", "kg", "ml", "kW", "kHz", "MHz", "kPa", "MPa",
        "kJ", "ms", "r/min",
        "m", "g", "t", "L", "W", "V", "A", "Hz", "Pa", "J", "C", "K",
        "min", "h", "s", "r",
    ]

    def __init__(self, doc, issues: List, author: str = 'StandardReview-AutoFixer'):
        self.doc = doc
        self.issues = issues
        self.author = author
        self.date = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        self._fix_id = 0
        self.fix_log: List[FixRecord] = []

    @property
    def next_id(self) -> int:
        self._fix_id += 1
        return self._fix_id

    def fix(self, output_path: str) -> List[FixRecord]:
        """应用所有可自动修复的规则，保存修订版"""
        # 按规则类型分组
        fixable = [i for i in self.issues if i.code in self.FIXABLE_RULES]

        for issue in fixable:
            handler = getattr(self, f'_fix_{issue.code.lower()}', None)
            if handler:
                try:
                    handler(issue)
                except Exception as e:
                    # 记录失败但不中断
                    self.fix_log.append(FixRecord(
                        issue.code, -1, '', '',
                        f"修复失败: {e}"
                    ))

        # 保存
        self.doc.save(output_path)
        return self.fix_log

    # ===== XML 操作工具方法 =====

    def _get_paragraph_by_index(self, idx: int):
        """根据段落索引获取 Paragraph 对象"""
        if idx < 0 or idx >= len(self.doc.paragraphs):
            return None
        return self.doc.paragraphs[idx]

    def _parse_para_idx(self, location: str) -> int:
        """从 issue location 解析段落索引"""
        # "段落 5" or "位置 3"
        m = re.search(r'(\d+)', location)
        if m:
            return int(m.group(1))
        return -1

    def _get_run_elements(self, para_element) -> List:
        """获取段落下所有 w:r 元素"""
        return para_element.findall(f'{W}r')

    def _build_char_map(self, para_element) -> List[Tuple]:
        """构建 字符位置 → (run元素, run内偏移) 的映射"""
        char_map = []
        for run_elem in self._get_run_elements(para_element):
            t_elems = run_elem.findall(f'{W}t')
            for t_elem in t_elems:
                text = t_elem.text or ''
                for j in range(len(text)):
                    char_map.append((run_elem, t_elem, j))
        return char_map

    def _split_run(self, run_elem: etree._Element, t_elem: etree._Element,
                   offset: int) -> Tuple[etree._Element, etree._Element]:
        """
        在 t_elem 的 offset 位置拆分 run。
        返回 (前半run, 后半run)，两个 run 都有独立的 w:t。
        """
        text = t_elem.text or ''
        if offset <= 0:
            return None, run_elem
        if offset >= len(text):
            return run_elem, None

        # 前半部分
        t_elem.text = text[:offset]
        t_elem.set(f'{{{XML_NS}}}space', 'preserve')

        # 创建后半 run（复制 rPr）
        new_run = etree.SubElement(run_elem.getparent(), f'{W}r')
        run_elem.getparent().remove(new_run)

        # 复制 run properties
        rpr = run_elem.find(f'{W}rPr')
        if rpr is not None:
            new_rpr = copy.deepcopy(rpr)
            new_run.append(new_rpr)

        # 创建后半 t
        new_t = etree.SubElement(new_run, f'{W}t')
        new_t.text = text[offset:]
        new_t.set(f'{{{XML_NS}}}space', 'preserve')

        # 插入到原 run 之后
        run_elem.addnext(new_run)

        return run_elem, new_run

    def _find_run_for_range(self, para_element, start: int, end: int):
        """
        找到覆盖 [start, end) 文本范围的 run 元素。
        必要时拆分 run 以精确匹配范围。
        返回 list of (run_elem, t_elem, text_start_in_t, text_end_in_t)
        """
        char_map = self._build_char_map(para_element)
        if start >= len(char_map) or end > len(char_map) or start >= end:
            return []

        # 找到起始和结束的 run/t/offset
        start_run, start_t, start_offset = char_map[start]
        end_run, end_t, end_offset_in_t = char_map[end - 1]
        end_offset = end_offset_in_t + 1  # end is exclusive

        # 如果 start 和 end 在同一个 t 元素中
        if start_t is end_t:
            # 需要拆分：前面保留 [0, start_offset)，中间是 [start_offset, end_offset)，后面是 [end_offset, ...)
            t_text = start_t.text or ''
            # 先在 end_offset 处拆分（后移）
            if end_offset < len(t_text):
                _, _ = self._split_run(start_run, start_t, end_offset)
                # 重新获取 char_map，因为拆分后元素变了
                # start_t 仍然是前半的 t
            # 再在 start_offset 处拆分（前移）
            if start_offset > 0:
                _, middle_run = self._split_run(start_run, start_t, start_offset)
                # middle_run 就是我们要删除的 run
                return [(middle_run, middle_run.find(f'{W}t'), 0,
                         end_offset - start_offset)]
            else:
                return [(start_run, start_t, 0, end_offset)]
        else:
            # 跨多个 run/t
            result = []

            # 第一段：从 start_offset 到 start_t 的末尾
            start_t_text = start_t.text or ''
            if start_offset > 0:
                _, second_run = self._split_run(start_run, start_t, start_offset)
                # second_run 包含后半
                second_t = second_run.find(f'{W}t')
                result.append((second_run, second_t, 0, len(second_t.text or '')))
            else:
                result.append((start_run, start_t, 0, len(start_t.text or '')))

            # 中间的 run 全部包含
            # 需要重新遍历 para_element 的 runs，找在 start_run 之后、end_run 之前的
            all_runs = self._get_run_elements(para_element)
            started = False
            for r in all_runs:
                if r is start_run:
                    started = True
                    continue
                if not started:
                    continue
                if r is end_run:
                    break
                t = r.find(f'{W}t')
                if t is not None and t.text:
                    result.append((r, t, 0, len(t.text)))

            # 最后一段：从 end_t 的开头到 end_offset
            end_t_text = end_t.text or ''
            if end_offset < len(end_t_text):
                first_run, _ = self._split_run(end_run, end_t, end_offset)
                t = first_run.find(f'{W}t')
                result.append((first_run, t, 0, len(t.text or '')))
            else:
                result.append((end_run, end_t, 0, len(end_t_text)))

            return result

    def _wrap_in_del(self, run_elem: etree._Element):
        """将 run 包装在 w:del 中（删除标记）"""
        parent = run_elem.getparent()
        if parent is None:
            return

        idx = list(parent).index(run_elem)

        # 创建 w:del
        del_elem = etree.Element(f'{W}del')
        del_elem.set(f'{W}id', str(self.next_id))
        del_elem.set(f'{W}author', self.author)
        del_elem.set(f'{W}date', self.date)

        # 将 w:t 改为 w:delText
        for t_elem in run_elem.findall(f'{W}t'):
            del_text = etree.SubElement(run_elem, f'{W}delText')
            del_text.text = t_elem.text
            del_text.set(f'{{{XML_NS}}}space', 'preserve')
            run_elem.remove(t_elem)

        # 移动 run 到 del
        parent.remove(run_elem)
        del_elem.append(run_elem)
        parent.insert(idx, del_elem)

    def _insert_text_after(self, ref_elem: etree._Element, text: str):
        """在参考元素后插入带 w:ins 标记的新文本"""
        parent = ref_elem.getparent()
        if parent is None:
            return

        idx = list(parent).index(ref_elem)

        # 创建 w:ins
        ins_elem = etree.Element(f'{W}ins')
        ins_elem.set(f'{W}id', str(self.next_id))
        ins_elem.set(f'{W}author', self.author)
        ins_elem.set(f'{W}date', self.date)

        # 创建 run
        new_run = etree.SubElement(ins_elem, f'{W}r')
        new_t = etree.SubElement(new_run, f'{W}t')
        new_t.text = text
        new_t.set(f'{{{XML_NS}}}space', 'preserve')

        parent.insert(idx + 1, ins_elem)

    def _replace_text_in_paragraph(self, para_element, pattern: str,
                                    replacement: str, para_idx: int,
                                    code: str, description: str) -> int:
        """
        在段落中查找所有匹配 pattern 的文本，用 replacement 替换，
        并添加 Track Changes 标记。
        返回修复数量。
        """
        # 获取段落完整文本
        char_map = self._build_char_map(para_element)
        full_text = ''
        for _, t_elem, _ in char_map:
            # 重建文本 - 但 char_map 存的是逐字符的
            pass

        # 更简单的方法：直接遍历 runs 获取文本
        full_text = ''
        run_text_map = []  # [(run_elem, t_elem, start_pos, length)]
        for run_elem in self._get_run_elements(para_element):
            for t_elem in run_elem.findall(f'{W}t'):
                t_text = t_elem.text or ''
                run_text_map.append((run_elem, t_elem, len(full_text), len(t_text)))
                full_text += t_text

        matches = list(re.finditer(pattern, full_text))
        if not matches:
            return 0

        fixes = 0
        # 逆序处理，避免位置偏移
        for match in reversed(matches):
            start, end = match.span()
            old_text = match.group()
            new_text = replacement

            # 找到覆盖 [start, end) 的 run 范围
            segments = self._find_run_for_range(para_element, start, end)
            if not segments:
                continue

            # 删除原始文本（标记为 w:del）
            # 逆序处理 segments，避免位置混乱
            for run_elem, t_elem, t_start, t_end in reversed(segments):
                self._wrap_in_del(run_elem)

            # 在第一个被删除的元素前插入新文本
            # 找到第一个 del 元素的位置
            first_del_run = segments[0][0]
            # _wrap_in_del 已经把 run 包装在 w:del 里了
            # 需要找到 w:del 元素
            del_parent = first_del_run.getparent()  # 这是 w:del
            if del_parent is not None and del_parent.tag == f'{W}del':
                self._insert_text_after(del_parent, new_text)

            self.fix_log.append(FixRecord(
                code, para_idx, old_text, new_text, description
            ))
            fixes += 1

        return fixes

    # ===== 各规则修复方法 =====

    def _fix_t001(self, issue) -> None:
        """T001: 禁用能愿动词替换"""
        para_idx = self._parse_para_idx(issue.location)
        para = self._get_paragraph_by_index(para_idx)
        if not para:
            return

        for old_word, new_word in self.MODAL_VERB_REPLACEMENTS.items():
            count = self._replace_text_in_paragraph(
                para._element, re.escape(old_word), new_word,
                para_idx, 'T001',
                f'禁用词"{old_word}"替换为"{new_word}"'
            )

    def _fix_w001(self, issue) -> None:
        """W001: 半角标点→全角标点"""
        para_idx = self._parse_para_idx(issue.location)
        para = self._get_paragraph_by_index(para_idx)
        if not para:
            return

        # 获取段落文本，找到需要替换的标点
        full_text = para.text
        for i, char in enumerate(full_text):
            if char in self.PUNCTUATION_MAP:
                prev_char = full_text[i - 1] if i > 0 else ''
                next_char = full_text[i + 1] if i + 1 < len(full_text) else ''
                if ('\u4e00' <= prev_char <= '\u9fff' or
                        '\u4e00' <= next_char <= '\u9fff'):
                    if char == ':' and re.search(r'[A-Z]/[A-Z]\s*\d*$', full_text[:i]):
                        continue
                    # 精确替换这个位置的标点
                    self._replace_at_position(
                        para, i, char, self.PUNCTUATION_MAP[char],
                        para_idx, 'W001',
                        f'半角"{char}"→全角"{self.PUNCTUATION_MAP[char]}"'
                    )
                    break  # 每段只修第一个（与检查逻辑一致）

    def _replace_at_position(self, para, char_pos, old_char, new_char,
                              para_idx, code, description):
        """精确替换段落中指定位置的单个字符"""
        para_elem = para._element
        segments = self._find_run_for_range(para_elem, char_pos, char_pos + 1)
        if not segments:
            return

        for run_elem, t_elem, t_start, t_end in reversed(segments):
            self._wrap_in_del(run_elem)

        first_del_run = segments[0][0]
        del_parent = first_del_run.getparent()
        if del_parent is not None and del_parent.tag == f'{W}del':
            self._insert_text_after(del_parent, new_char)

        self.fix_log.append(FixRecord(
            code, para_idx, old_char, new_char, description
        ))

    def _fix_f002(self, issue) -> None:
        """F002: 数字与单位间补空格"""
        para_idx = self._parse_para_idx(issue.location)
        para = self._get_paragraph_by_index(para_idx)
        if not para:
            return

        # 构建匹配所有 数字+单位(无空格) 的 pattern
        units_alt = '|'.join(sorted(self.UNITS, key=len, reverse=True))
        pattern = rf'(\d)({units_alt})(?![a-zA-Z])'

        full_text = para.text
        matches = list(re.finditer(pattern, full_text))
        if not matches:
            return

        # 逆序处理
        for match in reversed(matches):
            start, end = match.span()
            old_text = match.group()
            # 在数字和单位间插入空格
            new_text = match.group(1) + ' ' + match.group(2)

            segments = self._find_run_for_range(para._element, start, end)
            if not segments:
                continue

            for run_elem, _, _, _ in reversed(segments):
                self._wrap_in_del(run_elem)

            first_del_run = segments[0][0]
            del_parent = first_del_run.getparent()
            if del_parent is not None and del_parent.tag == f'{W}del':
                self._insert_text_after(del_parent, new_text)

            self.fix_log.append(FixRecord(
                'F002', para_idx, old_text, new_text,
                f'数字与单位"{match.group(2)}"间补空格'
            ))

    def _fix_f003(self, issue) -> None:
        """F003: 尺寸表述规范化"""
        para_idx = self._parse_para_idx(issue.location)
        para = self._get_paragraph_by_index(para_idx)
        if not para:
            return

        units_alt = r'(?:mm|cm|m|km|μm|um|nm)'
        pattern = re.compile(
            rf'(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)'
            rf'(?:\s*[x×]\s*(\d+(?:\.\d+)?))?\s*{units_alt}'
        )

        full_text = para.text
        for match in reversed(list(pattern.finditer(full_text))):
            # 检查是否已经是规范格式
            full = match.group()
            if re.match(rf'\d+(?:\.\d+)?\s*{units_alt}\s*[x×]', full):
                continue

            # 构建替换文本
            unit = re.search(units_alt, full).group()
            nums = [match.group(1), match.group(2)]
            if match.group(3):
                nums.append(match.group(3))

            new_text = f' {unit} x '.join(nums) + f' {unit}'

            start, end = match.span()
            segments = self._find_run_for_range(para._element, start, end)
            if not segments:
                continue

            for run_elem, _, _, _ in reversed(segments):
                self._wrap_in_del(run_elem)

            first_del_run = segments[0][0]
            del_parent = first_del_run.getparent()
            if del_parent is not None and del_parent.tag == f'{W}del':
                self._insert_text_after(del_parent, new_text)

            self.fix_log.append(FixRecord(
                'F003', para_idx, full, new_text,
                '尺寸表述规范化：每个量后带单位'
            ))

    def _fix_f011(self, issue) -> None:
        """F011: 公式编号补括号"""
        para_idx = self._parse_para_idx(issue.location)
        para = self._get_paragraph_by_index(para_idx)
        if not para:
            return

        # 匹配 "公式" 后直接跟数字（无括号）
        pattern = r'公式\s*(?!\()\d+'

        full_text = para.text
        for match in reversed(list(re.finditer(pattern, full_text))):
            start, end = match.span()
            old_text = match.group()
            # 提取数字
            num = re.search(r'(\d+)', old_text).group(1)
            new_text = f'公式({num})'

            segments = self._find_run_for_range(para._element, start, end)
            if not segments:
                continue

            for run_elem, _, _, _ in reversed(segments):
                self._wrap_in_del(run_elem)

            first_del_run = segments[0][0]
            del_parent = first_del_run.getparent()
            if del_parent is not None and del_parent.tag == f'{W}del':
                self._insert_text_after(del_parent, new_text)

            self.fix_log.append(FixRecord(
                'F011', para_idx, old_text, new_text,
                f'公式编号补括号'
            ))

    def _fix_f001(self, issue) -> None:
        """F001: 删除标题末尾标点"""
        para_idx = self._parse_para_idx(issue.location)
        para = self._get_paragraph_by_index(para_idx)
        if not para:
            return

        text = para.text.strip()
        if not text:
            return

        last_char = text[-1]
        if last_char in '：:，,。.、；;!！':
            # 删除最后一个字符
            char_pos = len(para.text) - 1
            # 找到实际文本中最后一个标点的位置
            full_text = para.text
            # 找到最后一个标点的位置
            for i in range(len(full_text) - 1, -1, -1):
                if full_text[i] in '：:，,。.、；;!！':
                    char_pos = i
                    break

            segments = self._find_run_for_range(para._element, char_pos, char_pos + 1)
            if not segments:
                return

            for run_elem, _, _, _ in reversed(segments):
                self._wrap_in_del(run_elem)

            # 不插入新文本（纯删除）

            self.fix_log.append(FixRecord(
                'F001', para_idx, last_char, '(删除)',
                f'删除标题末尾标点"{last_char}"'
            ))

    def _fix_t006(self, issue) -> None:
        """T006: 注日期引用冒号→一字线"""
        para_idx = self._parse_para_idx(issue.location)
        para = self._get_paragraph_by_index(para_idx)
        if not para:
            return

        # 匹配 GB/T XXXXX:YYYY 或 GB/T XXXXX：YYYY
        pattern = r'(GB/T\s*\d+\.?\d*)[:：](\d{4})'

        full_text = para.text
        for match in reversed(list(re.finditer(pattern, full_text))):
            start, end = match.span()
            old_text = match.group()
            new_text = f'{match.group(1)}-{match.group(2)}'

            segments = self._find_run_for_range(para._element, start, end)
            if not segments:
                continue

            for run_elem, _, _, _ in reversed(segments):
                self._wrap_in_del(run_elem)

            first_del_run = segments[0][0]
            del_parent = first_del_run.getparent()
            if del_parent is not None and del_parent.tag == f'{W}del':
                self._insert_text_after(del_parent, new_text)

            self.fix_log.append(FixRecord(
                'T006', para_idx, old_text, new_text,
                '注日期引用冒号改为一字线'
            ))

    def get_summary(self) -> dict:
        """获取修复摘要"""
        from collections import Counter
        code_counts = Counter(r.code for r in self.fix_log)
        return {
            "total_fixes": len(self.fix_log),
            "by_code": dict(code_counts),
            "failed": [r for r in self.fix_log if r.paragraph_idx == -1],
        }
