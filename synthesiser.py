import os
from datetime import datetime

import anthropic

from analyser import ArticleAnalysis

SYNTHESIS_SYSTEM_PROMPT = """You are a senior AI research analyst writing a weekly briefing for a technical audience.
You have been given structured analysis of multiple articles published in the last 7 days.

Write a cohesive, well-structured markdown report that:
1. Opens with a 3-4 sentence executive overview of the week's key themes
2. Groups findings by topic/theme (not by source) — synthesise across articles, don't just list them
3. Highlights the most technically significant developments with concrete details
4. Notes recurring limitations or open problems across the field
5. Ends with a complete sources list

Tone: precise, technical, informative. Avoid marketing language and vague superlatives.
Use markdown headers, bullet points, and bold for key terms."""


def _build_synthesis_prompt(analyses: list[ArticleAnalysis], topics: list[str]) -> str:
    articles_json_lines = []
    for a in analyses:
        articles_json_lines.append(
            f"""### {a.title}
- Source: {a.source_name}
- URL: {a.url}
- Published: {a.published_date or "unknown"}
- Summary: {a.summary}
- Technical details: {"; ".join(a.technical_details) if a.technical_details else "none"}
- Use cases: {"; ".join(a.use_cases) if a.use_cases else "none"}
- Limitations: {"; ".join(a.limitations) if a.limitations else "none"}
- Topics covered: {", ".join(a.relevant_topics) if a.relevant_topics else "none"}
"""
        )

    return f"""Synthesise the following {len(analyses)} article analyses into a weekly AI research briefing.

Research topics of interest: {", ".join(topics)}

---
{"".join(articles_json_lines)}
---

Write the complete markdown report now."""


def synthesise(
    analyses: list[ArticleAnalysis],
    topics: list[str],
    model: str,
    output_path: str,
) -> str:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    prompt = _build_synthesis_prompt(analyses, topics)

    print(f"  Synthesising {len(analyses)} analyses → {output_path}")

    full_text = ""
    with client.messages.stream(
        model=model,
        max_tokens=8192,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=SYNTHESIS_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text_chunk in stream.text_stream:
            print(text_chunk, end="", flush=True)
            full_text += text_chunk

    print()  # newline after streaming output

    # Prepend a datestamped header
    date_str = datetime.now().strftime("%d %B %Y")
    report = f"# AI Research Briefing — {date_str}\n\n{full_text}"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    return output_path
