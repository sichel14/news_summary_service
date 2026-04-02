"""从 RSS URL 拉取条目，按「源站唯一标识」去重后写入 rss_wechat_article。

RSS/Atom 里这一标识通常来自 ``<guid>`` 或 ``<id>``；入库时存在表字段 ``aid`` 中（业务含义：article id，不限定字面叫 aid）。"""

from __future__ import annotations

import html
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

import feedparser
import requests
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.base import db
from app.models.information_source import InformationSource
from app.models.rss_wechat_article import RssWechatArticle

# 正文中常夹带真实图文链接；HTML 里 ``&`` 会写成 ``&amp;``，必须先 ``html.unescape``
# 匹配到空白或引号为止，避免把查询串截断在 ``&amp`` 上
_MP_WEIXIN_RE = re.compile(
    r"https?://mp\.weixin\.qq\.com/s[^\s\"'<>]+",
    re.I,
)

_FEED_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "application/rss+xml, application/atom+xml, application/xml, "
        "text/xml;q=0.9, */*;q=0.8"
    ),
}


def _parse_feed(url: str) -> tuple[Any, str | None]:
    """
    优先用 requests 拉取正文再 feedparser 解析（与部分站点兼容性更好）；
    失败时回退到 feedparser 自带 URL 拉取。
    返回 (parsed_feed, optional_warning)。
    """
    try:
        r = requests.get(url, timeout=25, headers=_FEED_HEADERS)
        r.raise_for_status()
        ct = (r.headers.get("Content-Type") or "").lower()
        raw = r.content
        parsed = feedparser.parse(raw)
        # print(parsed)
        warning: str | None = None
        if not getattr(parsed, "entries", None) and "text/html" in ct:
            warning = (
                "响应 Content-Type 为 HTML，可能不是 RSS（例如官网已改为落地页）；"
                "请换用自建 RSSHub 等提供的 Feed URL。"
            )
        elif not getattr(parsed, "entries", None) and raw[:200].strip().startswith(b"<"):
            warning = "正文以 HTML 开头且无条目，可能不是有效 Feed。"
        return parsed, warning
    except requests.RequestException:
        parsed = feedparser.parse(url)
        return parsed, None


def _entry_html_blobs(entry) -> str:
    parts: list[str] = []
    for attr in ("summary", "description"):
        v = getattr(entry, attr, None)
        if isinstance(v, str):
            parts.append(v)
    content = getattr(entry, "content", None)
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("value"):
                parts.append(str(block["value"]))
    return "\n".join(parts)


def _first_mp_weixin_url(text: str) -> str | None:
    if not text:
        return None
    text = html.unescape(text)
    m = _MP_WEIXIN_RE.search(text)
    return m.group(0) if m else None


def _follow_redirects(url: str, timeout: float = 12.0) -> str | None:
    """跟随 HTTP 重定向，若最终 URL 落在 mp.weixin.qq.com 则返回。"""
    if not url or not url.startswith(("http://", "https://")):
        return None
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; RSS-Sync/1.0)"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            final = resp.geturl()
            if "mp.weixin.qq.com" in final:
                return final
    except (urllib.error.URLError, OSError, ValueError):
        pass
    return None


def _best_article_link(entry) -> str | None:
    """
    优先得到可在浏览器直接打开的 mp.weixin.qq.com 链接。
    很多微信 RSS 的 ``entry.link`` 是中间页（跳转、搜狗搜索等），正文 HTML 里反而有真实链接。
    """
    blob = _entry_html_blobs(entry)
    if u := _first_mp_weixin_url(blob):
        return u[:512]

    raw = getattr(entry, "link", None)
    if not isinstance(raw, str) or not raw.strip():
        return None
    raw = html.unescape(raw.strip())
    if "mp.weixin.qq.com" in raw:
        return raw[:512]

    if resolved := _follow_redirects(raw):
        return resolved[:512]

    return raw[:512]


def _entry_aid(entry) -> str | None:
    """
    从 feedparser 条目中取出「稳定唯一键」，写入数据库的 ``aid`` 列。

    RSS 2.0 常见是 ``guid``，Atom 常见是 ``id``；feedparser 会映射到 ``entry.id`` /
    ``entry.guid``。二者优先，都没有再用 ``link``。不是「不用 guid」，而是规范里
    就叫 guid/id，我们只在库里统一叫 ``aid``。
    """
    for attr in ("id", "guid"):
        raw = getattr(entry, attr, None)
        if raw is None:
            continue
        if isinstance(raw, dict):
            raw = raw.get("value") or raw.get("guid")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()[:255]
    link = getattr(entry, "link", None)
    if isinstance(link, str) and link.strip():
        return link.strip()[:255]
    return None


@dataclass
class RssSyncResult:
    """同步统计；``skipped_no_aid`` 表示未能从 entry 解析出任何可用键（无 guid/id/link）。"""

    information_source_id: int
    fetched: int
    inserted: int
    skipped_already_in_db: int
    skipped_no_aid: int  # 无 guid/id/link，无法入库（aid 列必填）
    feed_warning: str | None = None  # 例如 URL 返回 HTML、可能不是 RSS


def sync_rss_for_source(information_source_id: int) -> RssSyncResult:
    """
    拉取指定信息源的 RSS，仅当 (information_source_id, aid) 尚不存在时插入文章。

    须在 Flask application context 中调用（以便使用 db 与配置）。
    """
    source = db.session.get(InformationSource, information_source_id)
    if source is None:
        raise ValueError(f"information source not found: id={information_source_id}")

    parsed, feed_warning = _parse_feed(source.rss_url)
    entries = getattr(parsed, "entries", []) or []

    existing_aids = {
        row[0]
        for row in db.session.execute(
            select(RssWechatArticle.aid).where(
                RssWechatArticle.information_source_id == information_source_id
            )
        ).all()
    }

    inserted = 0
    skipped_dup = 0
    skipped_no_aid = 0

    for entry in entries:
        aid = _entry_aid(entry)
        if not aid:
            skipped_no_aid += 1
            continue
        if aid in existing_aids:
            skipped_dup += 1
            continue

        title = getattr(entry, "title", None)
        if title is not None:
            title = str(title)

        link = _best_article_link(entry)

        row = RssWechatArticle(
            information_source_id=information_source_id,
            aid=aid,
            title=title,
            link=link,
        )
        db.session.add(row)
        existing_aids.add(aid)
        inserted += 1

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise

    return RssSyncResult(
        information_source_id=information_source_id,
        fetched=len(entries),
        inserted=inserted,
        skipped_already_in_db=skipped_dup,
        skipped_no_aid=skipped_no_aid,
        feed_warning=feed_warning,
    )
