# Standard Review Skill

基于 GB/T 1.1-2020 标准要求，采用**脚本 + AI 混合审查方案**，全面审查标准草稿的格式编排、结构要素、规范性用词和文字表述问题。

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.7+-green.svg)](https://www.python.org/)
[![GB/T 1.1-2020](https://img.shields.io/badge/GB%2FT%201.1-2020-orange.svg)](https://std.samr.gov.cn/)
[![Version](https://img.shields.io/badge/version-2.8-purple.svg)](https://github.com/surfy2024/standard-review/releases)
[![AI Enhanced](https://img.shields.io/badge/AI-Enhanced-blue.svg)](https://github.com/surfy2024/standard-review)

---

## ✨ 核心特性

| 能力 | 说明 |
|------|------|
| 🤖 **AI 深度审查** | 语义理解、上下文分析、灵活判断、专业建议 |
| ⚡ **40+ 检查规则** | 格式编排 / 结构要素 / 规范性用词 / 文字表述四大类 |
| 🔧 **自动修复** | 7 类规则自动修复，生成 Word Track Changes 修订版 |
| 📊 **HTML 交互报告** | 可筛选、可搜索、可展开详情的交互式报告 |
| 📄 **多格式支持** | 同时支持 .docx 和 .pdf 输入，检测结果完全一致 |
| 🔄 **版本对比** | 新旧版本草稿 diff，区分新增/已修复/持续存在问题 |
| 📚 **多标准支持** | 国家/行业/地方/企业/团体 5 类标准，自动检测 + 差异化规则 |
| 🔗 **引用标准符合性检查** | 引用提取、交叉一致性、**自动下载国标 PDF**、指标级符合性比对、不符合问题完整条款对比 |
| 🎯 **精准定位** | "第X页，章节Y.Y 标题，文本摘要"格式，章节上下文感知匹配（99.3%页码匹配率） |

---

## 📦 安装

### 前置要求

- Python 3.7+
- python-docx（.docx 文档处理）
- PyMuPDF（.pdf 文档处理，可选）

```bash
pip install python-docx PyMuPDF
```

---

## 🚀 快速开始

### 基本审查

```bash
# 审查 DOCX 文件
python scripts/check_standard.py your_standard.docx --output result.json --pretty

# 审查 PDF 文件
python scripts/check_standard.py your_standard.pdf --output result.json --pretty
```

### 自动修复

```bash
# 生成带 Track Changes 标记的修订版
python scripts/auto_fix.py your_standard.docx --output revised.docx
```

### HTML 交互报告

```bash
# 从 JSON 结果生成 HTML 报告
python scripts/generate_html_report.py result.json --output report.html
```

### 版本对比

```bash
# 新旧版本对比审查
python scripts/diff_checker.py old_version.docx new_version.docx \
  --output diff_result.json --pretty --markdown diff_report.md
```

### 指定标准类型

```bash
# 自动检测标准类型（默认）
python scripts/check_standard.py input.docx

# 手动指定团体标准
python scripts/check_standard.py input.docx --standard gb-group

# 列出所有支持的标准类型
python scripts/check_standard.py --list-standards
```

### 引用标准符合性检查

```bash
# 基础检查 + 自动下载引用标准（默认行为，零额外输入）
python scripts/check_standard.py input.docx

# 禁用自动下载（仅运行自动层 R001-R008）
python scripts/check_standard.py input.docx --no-auto-ref

# 自动下载 + 手动补充非国标引用标准
python scripts/check_standard.py input.docx \
  --ref SY-T-6276.pdf --ref HJ-169.docx

# 或指定引用标准目录
python scripts/check_standard.py input.docx --ref-dir ./references/
```

---

## 📋 功能详解

### 1. 脚本快速检查（40+ 规则）

#### 格式编排检查

| 规则代码 | 检查内容 |
|---------|---------|
| F001 | 标题末尾标点检查 |
| F002 | 数字与单位间距 |
| F003 | 尺寸表述规范性（80x25x50 mm → 80 mm x 25 mm x 50 mm） |
| F005-F007 | 层次编号连续性（章/条编号） |
| F009 | 图表编号连续性 |
| F010 | 目次页码罗马数字检查 |
| F011 | 公式编号括号检查 |
| F012 | 图/表脚注编号格式检查 |
| F013 | 百分率公差格式 |
| F014 | 连字符一致性（半角/全角混用） |

#### 结构要素检查

| 规则代码 | 检查内容 |
|---------|---------|
| S001 | 必备要素存在性（前言、范围） |
| S002 | 要素排列顺序 |
| S003 | 前言必备内容 |
| S004 | 孤立条编号检查 |
| S005 | 款/项无归属检查 |
| S006 | 附录编号 I/O 检查 |
| S007 | 无内容要素声明检查 |
| S009 | 引言规范性条款检查 |

#### 规范性用词检查

| 规则代码 | 检查内容 |
|---------|---------|
| T001 | 禁用词检测（必须、应当、不得） |
| T002 | "应"与弱化词搭配 |
| T003 | 引用格式（注日期引用） |
| T004 | "遵守"/"符合"混用检查 |
| T006 | 注日期引用冒号→一字线 |
| T007 | 条文脚注含要求条款检查 |
| T008 | "概述"含要求条款检查 |
| T009 | 术语定义含要求型条款检查 |

#### 文字表述检查

| 规则代码 | 检查内容 |
|---------|---------|
| W001 | 中文正文半角标点检查 |
| W003 | 术语首次出现加粗检查 |

#### 多标准专属检查

| 规则代码 | 检查内容 |
|---------|---------|
| MS001 | 国家标准编号冒号→一字线 |
| MS002 | 行业标准前缀代号校验（60+ 行业代号） |
| MS003 | 地方标准区域代码校验（34 个省级行政区划） |
| MS004 | 企业标准编号年份缺失检查 |
| MS005 | 团体标准编号年份缺失检查 |

#### 引用标准符合性检查

**自动层（始终运行）：**

| 规则代码 | 检查内容 |
|---------|---------|
| R001 | 从"规范性引用文件"提取所有引用标准编号 |
| R002 | 引用格式校验（编号空格、连接符、全角/半角） |
| R003 | 重复引用检测 |
| R004 | 排序规范性检查（国标→行标→地标→国际标准） |
| R005 | 引导语完整性和存在性检查 |
| R006 | 全文标准引用提取 |
| R007 | 缺失引用检测（正文引用但未在引用文件中列出） |
| R008 | 冗余引用检测（引用文件中列出但正文未引用） |

**用户提交层（自动下载国标 PDF 或 `--ref` 提供非国标文档）：**

| 规则代码 | 检查内容 |
|---------|---------|
| R009 | 从引用标准文档提取要求性条款（应/必须/不得/宜/可） |
| R010 | 从草稿提取对应要求性条款 |
| R011 | 语义匹配——关键词 Jaccard 相似度关联 |
| R012 | 指标级比对——不符合 / 符合 / 优于 |

---

### 2. 自动修复（Track Changes）

对确定性规则自动修复，生成带 Word Track Changes 标记的修订版，用户可在 Word 中逐条接受/拒绝：

| 规则 | 修复内容 |
|------|---------|
| T001 | 禁用能愿动词替换（必须→应, 应当→应, 不得→不应） |
| W001 | 半角标点→全角标点（,→， :→： ;→；） |
| F002 | 数字与单位间补空格（80mm→80 mm） |
| F003 | 尺寸表述规范化（80x25x50 mm→80 mm x 25 mm x 50 mm） |
| F011 | 公式编号补括号（公式3→公式(3)） |
| F001 | 删除标题末尾标点 |
| T006 | 注日期引用冒号→一字线（GB/T XXXXX:YYYY→GB/T XXXXX-YYYY） |

---

### 3. HTML 交互报告

自包含 HTML 报告（内联 CSS + JS，无外部依赖）：

- 📊 统计概览卡片（ERROR / WARNING / SUGGESTION 三级分类）
- 🏷️ 高频问题类型 TOP 10
- 🔍 多维筛选（按严重等级 + 按规则分类）
- 🔎 全文搜索（实时搜索问题描述、位置、建议）
- 📎 上下文展开（点击展开问题原文上下文）
- 🔧 可修复标记（自动标注可自动修复的问题）
- 📱 响应式设计（适配桌面和移动端）

---

### 4. 多标准支持

支持五种中国标准类型，自动从文档内容检测标准编号前缀：

| 标准类型 | ID | 编号示例 | 差异说明 |
|---------|-----|---------|---------|
| 国家标准 | `gb-national` | GB/T 12345-2020 | 全部 GB/T 1.1-2020 规则 |
| 行业标准 | `gb-industry` | YY 0123-2020 | 全部规则 + 行业代号校验 |
| 地方标准 | `gb-local` | DB11/T 1322-2023 | 全部规则 + 区域代码校验 |
| 企业标准 | `gb-enterprise` | Q/ABC 001-2023 | 前言非强制，S007 禁用 |
| 团体标准 | `gb-group` | T/CAS 001-2023 | S007 禁用 |

---

### 5. 版本对比 diff

```bash
python scripts/diff_checker.py old.docx new.docx --output diff.json --markdown report.md
```

- 🔄 段落级 diff（difflib.SequenceMatcher）
- 🏗️ 结构变更检测（标题增删改、章节变化）
- 📋 问题三分类：新增问题 / 已修复问题 / 持续存在问题
- 📄 双格式报告：JSON + Markdown

---

### 6. 引用标准符合性检查

**自动下载 + 用户提交混合模式**：
- **国标（GB/GB-T/GB-Z）**：自动从 [openstd.samr.gov.cn](https://openstd.samr.gov.cn/) 搜索并下载 PDF，无需用户干预
- **非国标（行业标准等）**：用户通过 `--ref` 手动提交

**自动下载流程**：
1. 从草稿"规范性引用文件"章节提取引用标准清单
2. 筛选可下载的国标类型
3. 搜索 openstd.samr.gov.cn → 获取标准唯一标识 hcno
4. 三步下载：详情页建立会话 → 激活下载权限 → 下载 PDF
5. 下载的 PDF 自动传入 R009-R012 符合性检查

**指标比对逻辑：**
- 草稿要求 ≥ 引用标准要求 → **优于**（草稿更严格，合规）
- 草稿要求 = 引用标准要求 → **符合**
- 草稿要求 < 引用标准要求 → **不符合**（草稿低于现行标准，违规）

---

## 📖 使用示例

### Python API 调用

```python
from scripts.check_standard import StandardChecker

# 创建检查器（自动检测标准类型）
checker = StandardChecker()
issues = checker.check("your_standard.docx")

# 指定标准类型
checker = StandardChecker(standard="gb-group")
issues = checker.check("your_standard.docx")

# 引用标准符合性检查
issues = checker.check("your_standard.docx", ref_files=["GB-T1.1-2020.docx"])

# 输出结果
for issue in issues:
    print(f"[{issue.severity}] {issue.code} {issue.description}")
```

### 输出示例

```json
{
  "file": "national_standard.docx",
  "standard_type": "gb-national",
  "standard_name": "国家标准",
  "drafting_standard": "GB/T 1.1-2020",
  "total_issues": 17,
  "summary": {
    "ERROR": 8,
    "WARNING": 9,
    "SUGGESTION": 0
  },
  "issues": [...]
}
```

---

## 🛠️ 项目结构

```
standard-review/
├── README.md                       # 项目说明
├── LICENSE                         # 许可证
├── SKILL.md                        # Skill 配置文档
├── references/                     # 规则参考文件
│   ├── structure-rules.md
│   ├── format-rules.md
│   ├── terminology-rules.md
│   ├── common-errors.md
│   └── usage-guide.md
└── scripts/                        # 核心脚本
    ├── check_standard.py           # 主检查器（40+ 规则）
    ├── auto_fix.py                 # 自动修复（Track Changes）
    ├── generate_html_report.py     # HTML 交互报告生成
    ├── pdf_extractor.py            # PDF 文本提取（PyMuPDF）
    ├── diff_checker.py             # 版本对比 diff
    ├── standard_profiles.py        # 多标准配置（5 类标准）
    ├── reference_checker.py        # 引用标准符合性检查
    ├── std_downloader.py           # 国标自动下载（openstd.samr.gov.cn）
    ├── analyze_styles.py           # 文档样式分析
    ├── test_rules.py               # 规则测试（14 项）
    ├── test_autofix.py             # 自动修复测试（15 项）
    ├── test_html_report.py         # HTML 报告测试（7 项）
    ├── test_pdf.py                 # PDF 提取测试（15 项）
    ├── test_diff.py                # 版本对比测试（33 项）
    ├── test_multi_standard.py      # 多标准测试（106 项）
    └── test_reference_check.py     # 引用标准检查测试（54 项）
```

---

## 🧪 测试

```bash
# 运行全部测试
cd scripts
python test_rules.py            # 规则测试
python test_autofix.py          # 自动修复测试
python test_html_report.py      # HTML 报告测试
python test_pdf.py              # PDF 提取测试
python test_diff.py             # 版本对比测试
python test_multi_standard.py   # 多标准测试
python test_reference_check.py  # 引用标准检查测试
```

共 7 套测试脚本，254+ 测试用例，全部通过。

---

## 📝 更新日志

### v2.8（2026-07-30）— 精准定位与 R012 增强

**精准定位**：问题位置从"段落X"升级为"第X页，章节Y.Y 标题，文本摘要"格式
- 新增章节上下文感知匹配算法，从目次解析标题→页码映射（99.3%匹配率）
- 仅"章标题"样式触发章节切换，避免同名子标题误匹配
- 修复 `_post_process_locations` 中 prefix 逗号残留导致 R012/R004/R008 位置格式化失败
- 修复 `_is_heading` 中 TOC 条目泄漏到标题列表

**R012 符合性比对增强**：不符合问题包含完整条款对比
- 草稿条款全文 + 引用标准条款全文（含来源标注）+ 指标对比表 + 对比结论
- 新增 `_extract_source_name()` 提取引用标准来源名称
- 条款文本不再截断（之前截断到60字符）

**HTML 报告改进**：R012 上下文默认展开、suggestion 字段支持换行、escape_html 保留换行符

### v2.7（2026-07-30）— 引用标准自动下载

新增 `std_downloader.py`，实现从 openstd.samr.gov.cn 自动搜索和下载国标 PDF：
- 自动从草稿提取引用标准清单，筛选可下载的国标类型（GB/GB-T/GB-Z）
- 三步下载流程：搜索获取 hcno → 详情页建立会话 → 下载 PDF
- 下载的 PDF 自动传入 R009-R012 符合性检查，实现零手动操作
- CLI 新增 `--auto-ref`（默认开启）/ `--no-auto-ref` 参数
- 修复 `get_summary()` 中 `matched_pairs` 始终为 0 的问题

### v2.6（2026-07-29）— 引用标准符合性检查

新增 `reference_checker.py`，实现两层架构：
- **自动层 R001-R008**：引用标准提取、格式校验、重复检测、排序检查、交叉引用一致性（缺失引用 + 冗余引用）
- **用户提交层 R009-R012**：从用户提供的引用标准文档提取要求性条款，语义匹配，指标级比对（不符合/符合/优于）
- CLI 新增 `--ref` 和 `--ref-dir` 参数

### v2.5（2026-07-29）— 多标准支持

新增 `standard_profiles.py`，支持国家/行业/地方/企业/团体 5 类标准，自动检测 + 差异化规则 + MS001-MS005 专属检查。

### v2.4（2026-07-29）— 版本对比

新增 `diff_checker.py`，段落级 diff 对齐，问题三分类（新增/已修复/持续存在），双格式报告。

### v2.3（2026-07-29）— PDF 支持

新增 `pdf_extractor.py`，PyMuPDF 文本提取 + 字体聚类识别标题，模拟 python-docx 接口，PDF/DOCX 检测结果完全一致。

### v2.2（2026-07-29）— HTML 交互报告

新增 `generate_html_report.py`，自包含 HTML 报告，统计卡片 + TOP10 + 多维筛选 + 全文搜索 + 上下文展开。

### v2.1（2026-07-29）— 自动修复

新增 `auto_fix.py`，7 类规则自动修复，Word Track Changes 标记，run 级别精确操作。

### v2.0（2026-07-29）— 规则补全

新增 15 条检查规则（F003/F010-F012/S004-S007/S009/T004/T007-T009/W001/W003），脚本覆盖率从 19% 提升至 81%。

### v1.2（2026-07-14）— AI 增强版

引入 AI 深度审查能力，脚本 + AI 混合审查方案。

### v1.1（2026-07-14）

样式分析功能，智能标题识别算法。

### v1.0（初始版本）

基本格式编排、结构要素、规范性用词、文字表述检查。

---

## 📄 许可证

MIT License — 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- GB/T 1.1-2020《标准化工作导则 第1部分：标准化文件的结构和起草规则》
- [python-docx](https://github.com/python-docx/python-docx)
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF)

## 📧 联系方式

- 项目地址：https://github.com/surfy2024/standard-review
- 问题反馈：https://github.com/surfy2024/standard-review/issues
- Releases：https://github.com/surfy2024/standard-review/releases

---

**注意**：本工具审查结果仅供参考，最终以专业审查人员意见为准。
