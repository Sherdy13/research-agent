import os
from dataclasses import dataclass, fields as dc_fields

import anthropic

MAX_CONTENT_CHARS = 8000

ANALYSIS_SYSTEM_PROMPT = """You are a technical research analyst specialising in AI and machine learning.
Your job is to analyse a single article and extract structured information.

Focus on:
- Core technical concepts and architectures described
- Concrete implementation details, APIs, or code patterns mentioned
- Practical use cases and applications
- Limitations, caveats, or open problems
- Which of the user's research topics are addressed

Be precise and factual. Quote or closely paraphrase specific technical claims rather than generalising.
If information is not present in the article, use null or an empty list — do not invent content."""

ARTICLE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "url": {"type": "string"},
        "published_date": {"type": ["string", "null"]},
        "summary": {"type": "string", "description": "2-3 sentence plain-English summary"},
        "technical_details": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Bullet points of specific technical content",
        },
        "use_cases": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Practical applications described or implied",
        },
        "limitations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Drawbacks, caveats, or open problems mentioned",
        },
        "relevant_topics": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Which of the research topics this article covers",
        },
        "source_name": {"type": "string"},
    },
    "required": [
        "title",
        "url",
        "published_date",
        "summary",
        "technical_details",
        "use_cases",
        "limitations",
        "relevant_topics",
        "source_name",
    ],
    "additionalProperties": False,
}


@dataclass
class ArticleAnalysis:
    title: str
    url: str
    published_date: str | None
    summary: str
    technical_details: list[str]
    use_cases: list[str]
    limitations: list[str]
    relevant_topics: list[str]
    source_name: str


def analyse_article(article: dict, topics: list[str], model: str) -> ArticleAnalysis | None:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    content_snippet = article["content"][:MAX_CONTENT_CHARS]
    if len(article["content"]) > MAX_CONTENT_CHARS:
        content_snippet += "\n\n[...article truncated for length...]"

    user_prompt = f"""Analyse the following article and extract structured information.

Research topics to watch for: {", ".join(topics)}

---
Title: {article["title"]}
URL: {article["url"]}
Source: {article["source_name"]}
Published: {article.get("date") or "unknown"}

Content:
{content_snippet}
---

Return a JSON object matching the required schema."""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": ANALYSIS_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
            tools=[
                {
                    "name": "article_analysis",
                    "description": "Structured analysis of an AI/ML article",
                    "input_schema": ARTICLE_SCHEMA,
                }
            ],
            tool_choice={"type": "tool", "name": "article_analysis"},
        )
    except anthropic.APIError as exc:
        print(f"    API error analysing {article['url']}: {exc}")
        return None

    tool_use = next((b for b in response.content if b.type == "tool_use"), None)
    if not tool_use:
        print(f"    No tool_use block in response for {article['url']}")
        return None

    data = tool_use.input
    valid_keys = {f.name for f in dc_fields(ArticleAnalysis)}

    # Filter to schema keys; if none match, Claude may have wrapped the payload in a single key
    filtered = {k: v for k, v in data.items() if k in valid_keys}
    if not filtered:
        for val in data.values():
            if isinstance(val, dict):
                nested = {k: v for k, v in val.items() if k in valid_keys}
                if nested:
                    filtered = nested
                    break

    if not filtered:
        print(f"    Unparseable tool response for {article['url']} — keys: {list(data.keys())}")
        return None

    try:
        return ArticleAnalysis(**filtered)
    except TypeError as exc:
        print(f"    ArticleAnalysis construction failed for {article['url']}: {exc}")
        return None


def analyse_articles(
    articles: list[dict], topics: list[str], model: str
) -> list[ArticleAnalysis]:
    results: list[ArticleAnalysis] = []
    for i, article in enumerate(articles, 1):
        print(f"  Analysing [{i}/{len(articles)}]: {article['title'][:60]}")
        analysis = analyse_article(article, topics, model)
        if analysis:
            results.append(analysis)
    return results
