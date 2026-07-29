#!/usr/bin/env python3
"""
标准类型配置模块

支持五种中国标准类型：
- 国家标准 (GB / GB/T)
- 行业标准 (如 YY, JB, QB, CJ, SL 等)
- 地方标准 (DBXX / DBXX/T)
- 企业标准 (Q/XXX)
- 团体标准 (T/XXX)

每种类型可配置：
- 标准编号前缀模式（用于自动检测）
- 必备/可选要素
- 启用/禁用的规则集
- 专属检查规则

使用方法：
    from standard_profiles import get_profile, auto_detect, list_profiles
"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class StandardProfile:
    """标准类型配置"""
    id: str                         # 配置 ID，如 "gb-national"
    name: str                       # 显示名称，如 "国家标准"
    description: str                # 简短描述
    drafting_standard: str          # 起草依据，如 "GB/T 1.1-2020"
    # 标准编号前缀正则（用于自动检测），按优先级排列
    prefix_patterns: List[str] = field(default_factory=list)
    # 必备结构要素
    required_elements: List[str] = field(default_factory=lambda: ["前言", "范围"])
    # 可选要素（缺失不报错）
    optional_elements: List[str] = field(default_factory=list)
    # 启用的规则编号集合（None = 全部启用）
    enabled_rules: Optional[set] = None
    # 禁用的规则编号集合
    disabled_rules: set = field(default_factory=set)
    # 专属检查规则函数名列表（对应 StandardChecker 的方法名）
    specific_checks: List[str] = field(default_factory=list)
    # 标准编号示例（用于报告显示）
    number_example: str = ""


# ===== 预定义配置 =====

PROFILES: Dict[str, StandardProfile] = {
    "gb-national": StandardProfile(
        id="gb-national",
        name="国家标准",
        description="GB 或 GB/T 国家标准，严格遵循 GB/T 1.1-2020",
        drafting_standard="GB/T 1.1-2020",
        prefix_patterns=[
            r'GB/T\s*\d+\.?\d*[-—:]\d{4}',
            r'GB\s+\d+\.?\d*[-—:]\d{4}',
            r'GB/T\s*\d+\.?\d*',
            r'GB\s+\d+\.?\d*',
        ],
        required_elements=["前言", "范围"],
        optional_elements=["引言", "目次", "参考文献", "索引"],
        enabled_rules=None,  # 全部启用
        disabled_rules=set(),
        specific_checks=[
            "_check_national_standard_number",   # 国家标准编号格式
        ],
        number_example="GB/T 1.1-2020",
    ),

    "gb-industry": StandardProfile(
        id="gb-industry",
        name="行业标准",
        description="行业标准（如 YY、JB、QB、CJ、SL 等），遵循 GB/T 1.1-2020",
        drafting_standard="GB/T 1.1-2020",
        prefix_patterns=[
            r'[A-Z]{2,}/T\s*\d+\.?\d*[-—:]\d{4}',
            r'[A-Z]{2,}\s+\d+\.?\d*[-—:]\d{4}',
            r'[A-Z]{2,}/T\s*\d+',
            r'[A-Z]{2,}\s+\d+\.?\d*',
        ],
        required_elements=["前言", "范围"],
        optional_elements=["引言", "目次", "参考文献", "索引"],
        enabled_rules=None,
        disabled_rules=set(),
        specific_checks=[
            "_check_industry_standard_number",   # 行业标准编号格式
        ],
        number_example="YY 0123-2020",
    ),

    "gb-local": StandardProfile(
        id="gb-local",
        name="地方标准",
        description="地方标准（DBXX/T），遵循 GB/T 1.1-2020",
        drafting_standard="GB/T 1.1-2020",
        prefix_patterns=[
            r'DB\d{2}/T\s*\d+\.?\d*[-—:]\d{4}',
            r'DB\d{2}\s+\d+\.?\d*[-—:]\d{4}',
            r'DB\d{2}/T\s*\d+',
            r'DB\d{2}\s+\d+\.?\d*',
        ],
        required_elements=["前言", "范围"],
        optional_elements=["引言", "目次", "参考文献", "索引"],
        enabled_rules=None,
        disabled_rules=set(),
        specific_checks=[
            "_check_local_standard_number",      # 地方标准编号 + 区域代码
        ],
        number_example="DB11/T 1322-2023",
    ),

    "gb-enterprise": StandardProfile(
        id="gb-enterprise",
        name="企业标准",
        description="企业标准（Q/XXX），参照 GB/T 1.1-2020，部分要求放宽",
        drafting_standard="GB/T 1.1-2020",
        prefix_patterns=[
            r'Q/[A-Z]{2,}\s*\d+\.?\d*[-—:]\d{4}',
            r'Q/[A-Z]{2,}\s*\d+',
            r'Q/\S+\s+\d+\.?\d*',
        ],
        required_elements=["范围"],  # 企业标准前言非强制
        optional_elements=["前言", "引言", "目次", "参考文献", "索引"],
        enabled_rules=None,
        disabled_rules={"S007"},  # 企业标准不强制要求规范性引用文件/术语声明
        specific_checks=[
            "_check_enterprise_standard_number",  # 企业标准编号格式
        ],
        number_example="Q/ABC 001-2023",
    ),

    "gb-group": StandardProfile(
        id="gb-group",
        name="团体标准",
        description="团体标准（T/XXX），遵循 GB/T 1.1-2020，部分要求灵活",
        drafting_standard="GB/T 1.1-2020",
        prefix_patterns=[
            r'T/[A-Z]{2,}\s*\d+\.?\d*[-—:]\d{4}',
            r'T/[A-Z]{2,}\s*\d+',
            r'T/\S+\s+\d+\.?\d*',
        ],
        required_elements=["前言", "范围"],
        optional_elements=["引言", "目次", "参考文献", "索引"],
        enabled_rules=None,
        disabled_rules={"S007"},  # 团体标准不强制要求空要素声明
        specific_checks=[
            "_check_group_standard_number",      # 团体标准编号格式
        ],
        number_example="T/CAS 001-2023",
    ),
}


def get_profile(profile_id: str) -> StandardProfile:
    """获取指定配置"""
    if profile_id not in PROFILES:
        raise ValueError(
            f"未知的标准类型: {profile_id}\n"
            f"可用类型: {', '.join(PROFILES.keys())}"
        )
    return PROFILES[profile_id]


def list_profiles() -> List[Dict[str, str]]:
    """列出所有可用配置（摘要）"""
    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "number_example": p.number_example,
        }
        for p in PROFILES.values()
    ]


def auto_detect(paragraphs: List[Dict]) -> str:
    """
    从文档段落内容自动检测标准类型

    Args:
        paragraphs: 段落列表，每项含 "text" 键

    Returns:
        检测到的 profile ID；无法判定时返回 "gb-national"（默认）
    """
    all_text = " ".join(p.get("text", "") for p in paragraphs)

    # 按优先级尝试匹配：地方标准 > 团体标准 > 企业标准 > 国家标准 > 行业标准
    # （因为地方/团体/企业标准的前缀更独特，不易误判）

    # 1. 地方标准: DB11/T, DB31/T, DB44/T ...
    if re.search(r'DB\d{2}/?T?\s*\d+', all_text):
        return "gb-local"

    # 2. 团体标准: T/CAS, T/ZSA, T/CNITA ...
    if re.search(r'T/[A-Z]{2,}\s*\d+', all_text):
        return "gb-group"

    # 3. 企业标准: Q/XXX
    if re.search(r'Q/[A-Z]{2,}\s*\d+', all_text):
        return "gb-enterprise"

    # 4. 国家标准: GB/T 或 GB
    if re.search(r'GB/T\s*\d+', all_text) or re.search(r'GB\s+\d+', all_text):
        return "gb-national"

    # 5. 行业标准: YY, JB, QB, CJ, SL, JG, GA, etc.
    # 排除 GB（已在上面处理）
    industry_pattern = re.compile(
        r'(?<!G)([A-Z]{2})/T\s*\d+|(?<!G)([A-Z]{2})\s+\d+\.?\d*[-—:]\d{4}'
    )
    if industry_pattern.search(all_text):
        return "gb-industry"

    # 默认：国家标准
    return "gb-national"


def is_rule_enabled(profile: StandardProfile, rule_code: str) -> bool:
    """判断某条规则在给定 profile 下是否启用"""
    # 先检查禁用列表
    if rule_code in profile.disabled_rules:
        return False
    # enabled_rules 为 None 表示全部启用
    if profile.enabled_rules is None:
        return True
    return rule_code in profile.enabled_rules


def get_specific_checks(profile: StandardProfile) -> List[str]:
    """获取 profile 的专属检查方法名列表"""
    return profile.specific_checks
