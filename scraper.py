import os
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

from firecrawl import V1FirecrawlApp as FirecrawlApp

MAX_ARTICLES_PER_SOURCE = 20
REQUEST_TIMEOUT = 30


def _firecrawl_client() -> FirecrawlApp:
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise EnvironmentError("FIRECRAWL_API_KEY not set")
    return FirecrawlApp(api_key=api_key)


DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%d",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %B %Y",
    "%d %b %Y",
]


def parse_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    date_str = date_str.strip()
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def is_within_days(date: datetime | None, days: int) -> bool:
    if date is None:
        return True  # include articles with no parseable date
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    return date >= cutoff


# Patterns that indicate a link is NOT an article
_NON_ARTICLE_PATTERNS = re.compile(
    r"/(tag|tags|category|categories|author|authors|page|feed|rss|search|"
    r"about|contact|privacy|terms|login|signup|subscribe|newsletter|"
    r"atom|entries|blogmarks|quotations|notes|guides|elsewhere|archive|"
    r"topics|series|collections|podcasts|videos|webinars)(/|$)",
    re.IGNORECASE,
)


def is_article_url(base_url: str, link: str) -> bool:
    if not link or not link.startswith("http"):
        return False
    parsed_link = urlparse(link)
    base_host = urlparse(base_url).netloc
    link_host = parsed_link.netloc
    # must be same domain (exact match only — exclude subdomains)
    if link_host != base_host:
        return False
    # exclude pagination query strings like ?page=N or &page=N
    if re.search(r"[?&]page=", parsed_link.query, re.IGNORECASE):
        return False
    link_path = parsed_link.path.rstrip("/")
    if not link_path or link_path == "/" or _NON_ARTICLE_PATTERNS.search(link_path):
        return False
    # require at least one path segment that looks like content (contains letters)
    segments = [s for s in link_path.split("/") if s]
    if not segments:
        return False
    last_segment = segments[-1]
    if not re.search(r"[a-zA-Z]", last_segment):
        return False
    # exclude file extensions that are not articles
    if re.search(r"\.(css|js|png|jpg|jpeg|gif|svg|ico|pdf|zip|xml)$", link, re.IGNORECASE):
        return False
    return True


def _extract_date_from_metadata(metadata: dict) -> datetime | None:
    for key in ("publishedDate", "published_date", "date", "og:article:published_time"):
        value = metadata.get(key)
        if value:
            parsed = parse_date(str(value))
            if parsed:
                return parsed
    return None


def scrape_source(source: dict, days_lookback: int, seen_urls: set[str]) -> list[dict]:
    app = _firecrawl_client()
    source_name = source["name"]
    index_url = source["url"]

    print(f"  Scraping index: {index_url}")
    try:
        index_result = app.scrape_url(index_url, formats=["markdown", "links"])
    except Exception as exc:
        print(f"  ERROR scraping index {index_url}: {exc}")
        return []

    raw_links: list[str] = getattr(index_result, "links", None) or []
    article_links = [
        link for link in raw_links
        if is_article_url(index_url, link) and link not in seen_urls
    ]
    # deduplicate while preserving order
    seen_in_batch: set[str] = set()
    unique_links: list[str] = []
    for link in article_links:
        if link not in seen_in_batch:
            seen_in_batch.add(link)
            unique_links.append(link)

    print(f"  Found {len(unique_links)} candidate article links")
    articles: list[dict] = []

    for url in unique_links[:MAX_ARTICLES_PER_SOURCE]:
        print(f"    Scraping: {url}")
        try:
            result = app.scrape_url(url, formats=["markdown", "links"])
        except Exception as exc:
            print(f"    ERROR scraping {url}: {exc}")
            continue

        content: str = getattr(result, "markdown", "") or ""
        metadata: dict = getattr(result, "metadata", {}) or {}

        if len(content.split()) < 50:
            # skip near-empty pages (probably 404 or nav-only)
            continue

        date = _extract_date_from_metadata(metadata)
        if not is_within_days(date, days_lookback):
            print(f"    Skipping (too old): {url}")
            continue

        title = metadata.get("title") or metadata.get("og:title") or url
        articles.append({
            "url": url,
            "source_name": source_name,
            "title": title,
            "content": content,
            "date": date.isoformat() if date else None,
            "word_count": len(content.split()),
        })
        print(f"    OK — {len(content.split())} words")

    print(f"  {source_name}: {len(articles)} articles collected")
    return articles
