#!/usr/bin/env python3
"""
国家标准自动下载模块

从 openstd.samr.gov.cn（国家标准全文公开系统）自动搜索和下载国家标准 PDF。

工作流程：
1. 搜索标准 → 从 HTML 结果中提取 hcno（标准唯一标识）
2. 访问详情页 → 建立 JSESSIONID 会话
3. 下载 PDF → GET /bzgk/std/viewGb?hcno=<hcno>

支持标准类型：GB（强制性）、GB/T（推荐性）、GB/Z（指导性技术文件）
不支持：采标标准（仅在线阅读）、工程建设国家标准、行业/地方标准

使用方式：
    from std_downloader import StdDownloader
    dl = StdDownloader()
    path = dl.download_by_number("GB/T 1.1-2020", "./downloads")
"""

import re
import os
import time
import urllib.parse
import urllib.request
import http.cookiejar
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass


# ============================================================
# 常量
# ============================================================

BASE_URL = "https://openstd.samr.gov.cn"
SEARCH_URL = f"{BASE_URL}/bzgk/gb/std_list"
DETAIL_URL = f"{BASE_URL}/bzgk/gb/newGbInfo"
DOWNLOAD_URL = f"{BASE_URL}/bzgk/std/viewGb"

# 可下载的标准前缀（仅国标）
DOWNLOADABLE_PREFIXES = {"GB", "GB/T", "GB/Z"}

# 请求超时（秒）
REQUEST_TIMEOUT = 30

# 下载重试次数
MAX_RETRIES = 2

# 请求间隔（秒，避免被封）
REQUEST_INTERVAL = 1.0


@dataclass
class SearchResult:
    """标准搜索结果"""
    hcno: str               # 标准唯一标识
    number: str             # 标准号（如 GB/T 1.1-2020）
    title: str              # 标准名称
    status: str             # 状态（现行/废止/即将实施）
    is_adopted: bool        # 是否采标（采标不可下载）
    is_downloadable: bool   # 是否可下载


class StdDownloader:
    """国家标准下载器"""

    def __init__(self, output_dir: str = "./std_downloads",
                 verbose: bool = True):
        """
        Args:
            output_dir: 下载文件保存目录
            verbose: 是否打印详细日志
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose

        # HTTP Cookie 管理
        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar)
        )

        # 请求头
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        # 缓存：标准号 → 本地文件路径（避免重复下载）
        self._cache: Dict[str, str] = {}

    def _log(self, msg: str):
        if self.verbose:
            print(f"  [下载器] {msg}")

    def _request(self, url: str, referer: str = None) -> bytes:
        """发起 HTTP 请求并返回响应内容"""
        headers = dict(self.headers)
        if referer:
            headers["Referer"] = referer

        req = urllib.request.Request(url, headers=headers)
        resp = self.opener.open(req, timeout=REQUEST_TIMEOUT)
        data = resp.read()
        resp.close()
        return data

    def search(self, std_number: str) -> Optional[SearchResult]:
        """搜索标准

        Args:
            std_number: 标准号，如 "GB/T 1.1-2020"

        Returns:
            SearchResult 或 None（未找到）
        """
        # 清理标准号用于搜索
        clean_number = std_number.strip()
        # 搜索时使用不含空格的标准号效果更好
        search_key = clean_number.replace(" ", "")

        params = urllib.parse.urlencode({
            "p.p1": "0",  # 全部类型
            "p.p90": "circulation_date",
            "p.p91": "desc",
            "p.p2": search_key,
        })
        url = f"{SEARCH_URL}?{params}"

        self._log(f"搜索标准: {clean_number}")
        html = self._request(url)
        html_text = html.decode("utf-8", errors="replace")

        # 从 HTML 中提取 showInfo('HCNO') 调用
        # 格式: onclick="showInfo('C4BFD981E993C417EF475F2A19B681F1');"
        pattern = r"showInfo\('([A-F0-9]+)'\)"
        matches = re.findall(pattern, html_text)

        if not matches:
            self._log(f"  未找到匹配结果: {clean_number}")
            return None

        # 提取所有结果，找到最匹配的
        results = self._parse_search_results(html_text, matches, clean_number)
        if not results:
            return None

        # 优先选择：标准号完全匹配 + 现行
        best = self._select_best_match(results, clean_number)
        if best:
            self._log(
                f"  找到: {best.number} ({best.title[:40]}...) "
                f"状态={best.status} 可下载={best.is_downloadable}"
            )
        return best

    def _parse_search_results(self, html: str, hcnos: List[str],
                              query: str) -> List[SearchResult]:
        """从搜索结果 HTML 中解析标准信息

        HTML 结构（每个标准一行）：
        <td><a onclick="showInfo('HCNO');">标准号</a></td>
        <td>采</td>  (采标标识，空则非采标)
        <td>...</td>
        <td><a onclick="showInfo('HCNO');">标准名称</a></td>
        <td>推标/强标</td>
        <td><span class="text-success">现行</span></td>
        """
        results = []

        for hcno in hcnos:
            # 找到该 hcno 在 HTML 中的所有出现位置
            pattern = r"showInfo\('" + hcno + r"'\);\">([^<]+)</a>"
            text_matches = re.findall(pattern, html)

            # 第一个匹配是标准号，第二个是标准名称
            number = text_matches[0].strip() if len(text_matches) >= 1 else ""
            title = text_matches[1].strip() if len(text_matches) >= 2 else ""

            if not number:
                continue

            # 提取该标准条目周围的 HTML 片段（从标准号到下一个标准号之前）
            idx = html.find(f"showInfo('{hcno}')")
            if idx < 0:
                continue
            # 从标准号位置向后取 2000 字符作为上下文
            context = html[idx:idx + 2000]

            # 检查是否采标：在标准号和名称之间是否有独立的"采"字
            # 采标标识在标准号后的 <td> 中
            is_adopted = bool(re.search(
                r"showInfo\('" + hcno + r"'\);\">[^<]+</a></td>\s*"
                r"<td[^>]*>\s*采\s*</td>",
                context
            ))

            # 检查状态
            status = "未知"
            if "现行" in context:
                status = "现行"
            elif "即将实施" in context:
                status = "即将实施"
            elif "废止" in context:
                status = "废止"

            # 判断是否可下载（采标不可下载）
            is_downloadable = not is_adopted and status in ("现行", "即将实施")

            results.append(SearchResult(
                hcno=hcno,
                number=number,
                title=title,
                status=status,
                is_adopted=is_adopted,
                is_downloadable=is_downloadable,
            ))

        return results

    def _select_best_match(self, results: List[SearchResult],
                           query: str) -> Optional[SearchResult]:
        """从搜索结果中选择最佳匹配"""
        # 规范化查询和标准号用于比较
        query_norm = re.sub(r"\s+", "", query).upper()

        # 1. 精确匹配标准号 + 现行
        for r in results:
            num_norm = re.sub(r"\s+", "", r.number).upper()
            if num_norm == query_norm and r.status == "现行":
                return r

        # 2. 精确匹配标准号（任意状态）
        for r in results:
            num_norm = re.sub(r"\s+", "", r.number).upper()
            if num_norm == query_norm:
                return r

        # 3. 包含匹配 + 现行
        for r in results:
            num_norm = re.sub(r"\s+", "", r.number).upper()
            if query_norm in num_norm and r.status == "现行":
                return r

        # 4. 包含匹配（任意状态）
        for r in results:
            num_norm = re.sub(r"\s+", "", r.number).upper()
            if query_norm in num_norm:
                return r

        # 5. 第一个结果
        return results[0] if results else None

    def download(self, hcno: str, filename_hint: str = None) -> Optional[str]:
        """下载标准 PDF

        三步下载流程：
        1. 访问详情页 newGbInfo → 建立 JSESSIONID 会话
        2. 访问下载中间页 showGb?type=download → 激活下载权限
        3. 下载 PDF viewGb → 返回实际 PDF 文件

        Args:
            hcno: 标准唯一标识
            filename_hint: 文件名提示（如 "GB-T_1.1-2020"）

        Returns:
            下载的文件路径，失败返回 None
        """
        SHOWGB_URL = f"{BASE_URL}/bzgk/std/showGb"

        # Step 1: 访问详情页建立会话
        detail_url = f"{DETAIL_URL}?hcno={hcno}"
        self._log(f"  [1/3] 访问详情页建立会话...")
        try:
            self._request(detail_url)
        except Exception as e:
            self._log(f"  访问详情页失败: {e}")
            return None

        time.sleep(0.5)

        # Step 2: 访问下载中间页（激活下载权限）
        # 注意：showGb 页面始终包含验证码相关 HTML/JS，但仅在需要时才显示
        # 不能通过页面内容判断是否需要验证码，直接继续到 step 3
        showgb_url = f"{SHOWGB_URL}?type=download&hcno={hcno}"
        self._log(f"  [2/3] 激活下载权限...")
        try:
            self._request(showgb_url, referer=detail_url)
        except Exception as e:
            self._log(f"  访问下载中间页失败: {e}")
            return None

        time.sleep(0.5)

        # Step 3: 下载 PDF
        download_url = f"{DOWNLOAD_URL}?hcno={hcno}"
        self._log(f"  [3/3] 下载 PDF...")

        try:
            headers = dict(self.headers)
            headers["Referer"] = showgb_url
            req = urllib.request.Request(download_url, headers=headers)
            resp = self.opener.open(req, timeout=REQUEST_TIMEOUT * 2)

            # 检查响应类型
            content_type = resp.headers.get("Content-Type", "")
            content_disp = resp.headers.get("Content-Disposition", "")
            content_length = resp.headers.get("Content-Length", "0")

            if "application/octet-stream" not in content_type and "application/pdf" not in content_type:
                data = resp.read()
                resp.close()
                if b"verifyCode" in data or "验证码".encode("utf-8") in data:
                    self._log(f"  需要验证码，无法自动下载")
                else:
                    self._log(f"  响应类型异常: {content_type}")
                return None

            # 从 Content-Disposition 提取文件名
            if not filename_hint:
                fname_match = re.search(
                    r'filename=([^\s;]+)', content_disp
                )
                if fname_match:
                    filename_hint = fname_match.group(1).replace("+", " ")
                else:
                    filename_hint = f"standard_{hcno}.pdf"

            # 确保文件名安全
            safe_name = re.sub(r'[\\/:*?"<>|]', "_", filename_hint)
            if not safe_name.endswith(".pdf"):
                safe_name += ".pdf"

            file_path = self.output_dir / safe_name

            # 写入文件
            with open(file_path, "wb") as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
            resp.close()

            file_size = file_path.stat().st_size
            if file_size == 0:
                self._log(f"  下载文件为空，可能需要验证码")
                file_path.unlink(missing_ok=True)
                return None

            self._log(f"  下载完成: {file_path.name} ({file_size / 1024:.0f} KB)")
            return str(file_path)

        except Exception as e:
            self._log(f"  下载失败: {e}")
            return None

    def download_by_number(self, std_number: str) -> Optional[str]:
        """按标准号搜索并下载

        Args:
            std_number: 标准号，如 "GB/T 1.1-2020"

        Returns:
            下载的文件路径，失败返回 None
        """
        # 检查缓存
        if std_number in self._cache:
            cached = self._cache[std_number]
            if Path(cached).exists():
                self._log(f"  使用缓存: {cached}")
                return cached
            else:
                del self._cache[std_number]

        # 检查是否为国标（可下载类型）
        prefix = self._extract_prefix(std_number)
        if prefix not in DOWNLOADABLE_PREFIXES:
            self._log(f"  跳过非国标: {std_number} (前缀={prefix})")
            return None

        # 搜索
        result = self.search(std_number)
        if not result:
            return None

        if not result.is_downloadable:
            self._log(
                f"  不可下载: {result.number} "
                f"(采标={result.is_adopted}, 状态={result.status})"
            )
            return None

        # 生成文件名提示
        filename_hint = result.number.replace("/", "-").replace(" ", "_")

        # 下载
        file_path = self.download(result.hcno, filename_hint)
        if file_path:
            self._cache[std_number] = file_path

        time.sleep(REQUEST_INTERVAL)
        return file_path

    def download_batch(self, std_numbers: List[str]) -> Dict[str, str]:
        """批量下载标准

        Args:
            std_numbers: 标准号列表

        Returns:
            {标准号: 文件路径} 字典（仅包含成功下载的）
        """
        results = {}
        total = len(std_numbers)
        success = 0
        failed = 0
        skipped = 0

        self._log(f"批量下载 {total} 个标准...")

        for i, num in enumerate(std_numbers, 1):
            self._log(f"[{i}/{total}] {num}")
            path = self.download_by_number(num)
            if path:
                results[num] = path
                success += 1
            else:
                # 检查是否被跳过（非国标）
                prefix = self._extract_prefix(num)
                if prefix not in DOWNLOADABLE_PREFIXES:
                    skipped += 1
                else:
                    failed += 1

        self._log(
            f"下载完成: 成功 {success}, 失败 {failed}, 跳过 {skipped} (非国标)"
        )
        return results

    @staticmethod
    def _extract_prefix(std_number: str) -> str:
        """从标准号中提取前缀"""
        std_number = std_number.strip()
        # GB/T, GB/Z, GB 开头
        if std_number.upper().startswith("GB/T"):
            return "GB/T"
        elif std_number.upper().startswith("GB/Z"):
            return "GB/Z"
        elif std_number.upper().startswith("GB"):
            return "GB"
        # 其他前缀
        match = re.match(r"^([A-Z]+(?:/[A-Z])?)", std_number.upper())
        if match:
            return match.group(1)
        return ""

    @staticmethod
    def is_downloadable_type(std_number: str) -> bool:
        """判断标准号是否为可下载的国标类型"""
        prefix = StdDownloader._extract_prefix(std_number)
        return prefix in DOWNLOADABLE_PREFIXES


# ============================================================
# CLI 入口（独立运行）
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="国家标准自动下载工具（从 openstd.samr.gov.cn）"
    )
    parser.add_argument(
        "standards", nargs="+",
        help="标准号列表，如 GB/T 1.1-2020 'GB/T 7714-2015'"
    )
    parser.add_argument(
        "-o", "--output", default="./std_downloads",
        help="下载目录（默认: ./std_downloads）"
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true",
        help="静默模式"
    )

    args = parser.parse_args()

    dl = StdDownloader(output_dir=args.output, verbose=not args.quiet)
    results = dl.download_batch(args.standards)

    print(f"\n下载结果:")
    for std, path in results.items():
        print(f"  ✓ {std} → {path}")

    failed = [s for s in args.standards if s not in results]
    if failed:
        print(f"\n未下载 ({len(failed)}):")
        for s in failed:
            print(f"  ✗ {s}")


if __name__ == "__main__":
    main()
