#!/usr/bin/env python3
"""
Web Search Skill - 搜索脚本

使用 DuckDuckGo 实现真实的网络搜索功能。
支持通用搜索和新闻搜索。

依赖: pip install duckduckgo-search

使用方式:
    # 通用搜索
    python search.py --query "Python 异步编程" --max-results 5
    
    # 新闻搜索
    python search.py --query "AI 最新进展" --type news --max-results 10
    
    # 限定时间范围
    python search.py --query "React 19" --time-range w
"""

import argparse
import json
import sys
import asyncio
from typing import List, Dict, Any, Optional

try:
    # 尝试新包名 ddgs
    from ddgs import DDGS
    DuckDuckGoSearchException = Exception  # ddgs 使用通用异常
except ImportError:
    try:
        # 回退到旧包名
        from duckduckgo_search import DDGS
        from duckduckgo_search.exceptions import DuckDuckGoSearchException
    except ImportError:
        print(json.dumps({
            "success": False,
            "error": "缺少依赖: 请运行 pip install ddgs (或 pip install duckduckgo-search)",
            "error_code": "MISSING_DEPENDENCY"
        }))
        sys.exit(1)


class WebSearcher:
    """DuckDuckGo 搜索封装"""
    
    def __init__(self, timeout: int = 30):
        """
        Args:
            timeout: 搜索超时时间（秒）
        """
        self.timeout = timeout
    
    def search(
        self,
        query: str,
        max_results: int = 5,
        region: str = "wt-wt",
        time_range: Optional[str] = None,
        safesearch: str = "moderate"
    ) -> List[Dict[str, Any]]:
        """
        执行通用网页搜索
        
        Args:
            query: 搜索关键词
            max_results: 返回结果数量（最大20）
            region: 搜索区域 (wt-wt:全球, cn-zh:中国, us-en:美国)
            time_range: 时间范围 (d:天, w:周, m:月, y:年)
            safesearch: 安全搜索级别 (on, moderate, off)
            
        Returns:
            搜索结果列表，每个结果包含:
            - title: 标题
            - href: 链接
            - body: 摘要
        """
        max_results = min(max_results, 20)  # 限制最大结果数
        
        try:
            # 新版 ddgs API: 不使用 context manager, 直接实例化
            ddgs = DDGS(timeout=self.timeout)
            results = ddgs.text(
                query,  # 第一个位置参数是 query
                region=region,
                safesearch=safesearch,
                timelimit=time_range,
                max_results=max_results
            )
            
            # 标准化结果格式
            standardized = []
            for r in results:
                standardized.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", r.get("link", "")),
                    "snippet": r.get("body", r.get("snippet", "")),
                    "source": "duckduckgo"
                })
            
            return standardized
                
        except DuckDuckGoSearchException as e:
            raise SearchError(f"DuckDuckGo 搜索失败: {e}")
        except Exception as e:
            raise SearchError(f"搜索执行错误: {e}")
    
    def search_news(
        self,
        query: str,
        max_results: int = 5,
        region: str = "wt-wt",
        time_range: Optional[str] = None,
        safesearch: str = "moderate"
    ) -> List[Dict[str, Any]]:
        """
        执行新闻搜索
        
        Args:
            query: 搜索关键词
            max_results: 返回结果数量（最大20）
            region: 搜索区域
            time_range: 时间范围 (d:天, w:周, m:月)
            safesearch: 安全搜索级别
            
        Returns:
            新闻搜索结果列表，每个结果包含:
            - title: 新闻标题
            - url: 新闻链接
            - snippet: 新闻摘要
            - date: 发布日期
            - source: 来源
        """
        max_results = min(max_results, 20)
        
        try:
            # 新版 ddgs API
            ddgs = DDGS(timeout=self.timeout)
            results = ddgs.news(
                query,  # 第一个位置参数是 query
                region=region,
                safesearch=safesearch,
                timelimit=time_range,
                max_results=max_results
            )
            
            # 标准化结果格式
            standardized = []
            for r in results:
                standardized.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", r.get("link", "")),
                    "snippet": r.get("body", r.get("excerpt", "")),
                    "date": r.get("date", ""),
                    "source": r.get("source", "unknown"),
                    "image": r.get("image", "")
                })
            
            return standardized
                
        except DuckDuckGoSearchException as e:
            raise SearchError(f"DuckDuckGo 新闻搜索失败: {e}")
        except Exception as e:
            raise SearchError(f"新闻搜索执行错误: {e}")
    
    def instant_answer(self, query: str) -> Optional[Dict[str, Any]]:
        """
        获取即时答案（如果有）
        
        Args:
            query: 查询关键词
            
        Returns:
            即时答案信息，可能为 None
        """
        try:
            ddgs = DDGS(timeout=self.timeout)
            results = ddgs.answers(query)
            if results:
                return {
                    "type": "instant_answer",
                    "text": results[0].get("text", ""),
                    "url": results[0].get("url", "")
                }
            return None
        except Exception:
            return None


class SearchError(Exception):
    """搜索错误"""
    pass


def format_results_markdown(
    results: List[Dict[str, Any]],
    search_type: str = "web"
) -> str:
    """
    将搜索结果格式化为 Markdown
    
    Args:
        results: 搜索结果列表
        search_type: 搜索类型 (web/news)
        
    Returns:
        Markdown 格式的结果
    """
    if not results:
        return "未找到相关结果。"
    
    lines = []
    
    for i, r in enumerate(results, 1):
        title = r.get("title", "无标题")
        url = r.get("url", "")
        snippet = r.get("snippet", "")
        
        lines.append(f"### {i}. [{title}]({url})")
        
        if search_type == "news":
            date = r.get("date", "")
            source = r.get("source", "")
            if date or source:
                lines.append(f"*{source} - {date}*")
        
        if snippet:
            lines.append(f"> {snippet}")
        
        lines.append("")
    
    return "\n".join(lines)


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="Web Search - 使用 DuckDuckGo 搜索网络信息"
    )
    
    parser.add_argument(
        "--query", "-q",
        required=True,
        help="搜索关键词"
    )
    
    parser.add_argument(
        "--type", "-t",
        choices=["web", "news", "instant"],
        default="web",
        help="搜索类型: web(网页), news(新闻), instant(即时答案)"
    )
    
    parser.add_argument(
        "--max-results", "-n",
        type=int,
        default=5,
        help="返回结果数量 (默认5, 最大20)"
    )
    
    parser.add_argument(
        "--region", "-r",
        default="wt-wt",
        help="搜索区域 (默认: wt-wt 全球, cn-zh 中国, us-en 美国)"
    )
    
    parser.add_argument(
        "--time-range",
        choices=["d", "w", "m", "y"],
        help="时间范围: d(天), w(周), m(月), y(年)"
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["json", "markdown"],
        default="json",
        help="输出格式 (默认: json)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="搜索超时时间（秒）"
    )
    
    args = parser.parse_args()
    
    searcher = WebSearcher(timeout=args.timeout)
    
    try:
        if args.type == "web":
            results = searcher.search(
                query=args.query,
                max_results=args.max_results,
                region=args.region,
                time_range=args.time_range
            )
        elif args.type == "news":
            results = searcher.search_news(
                query=args.query,
                max_results=args.max_results,
                region=args.region,
                time_range=args.time_range
            )
        elif args.type == "instant":
            result = searcher.instant_answer(args.query)
            results = [result] if result else []
        
        # 构建响应
        response = {
            "success": True,
            "query": args.query,
            "type": args.type,
            "count": len(results),
            "results": results
        }
        
        if args.format == "markdown":
            response["markdown"] = format_results_markdown(results, args.type)
        
        print(json.dumps(response, ensure_ascii=False, indent=2))
        
    except SearchError as e:
        print(json.dumps({
            "success": False,
            "error": str(e),
            "error_code": "SEARCH_ERROR",
            "query": args.query
        }, ensure_ascii=False))
        sys.exit(1)
        
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"未知错误: {e}",
            "error_code": "UNKNOWN_ERROR",
            "query": args.query
        }, ensure_ascii=False))
        sys.exit(1)


# === 供其他 Python 代码直接调用的函数 ===

def web_search(
    query: str,
    max_results: int = 5,
    region: str = "wt-wt",
    time_range: Optional[str] = None
) -> Dict[str, Any]:
    """
    网页搜索（供直接调用）
    
    Args:
        query: 搜索关键词
        max_results: 返回结果数量
        region: 搜索区域
        time_range: 时间范围 (d/w/m/y)
        
    Returns:
        包含搜索结果的字典
    """
    searcher = WebSearcher()
    try:
        results = searcher.search(
            query=query,
            max_results=max_results,
            region=region,
            time_range=time_range
        )
        return {
            "success": True,
            "query": query,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": query
        }


def web_search_news(
    query: str,
    max_results: int = 5,
    region: str = "wt-wt",
    time_range: Optional[str] = None
) -> Dict[str, Any]:
    """
    新闻搜索（供直接调用）
    
    Args:
        query: 搜索关键词
        max_results: 返回结果数量
        region: 搜索区域
        time_range: 时间范围 (d/w/m)
        
    Returns:
        包含新闻搜索结果的字典
    """
    searcher = WebSearcher()
    try:
        results = searcher.search_news(
            query=query,
            max_results=max_results,
            region=region,
            time_range=time_range
        )
        return {
            "success": True,
            "query": query,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": query
        }


if __name__ == "__main__":
    main()
