# research-agent

A weekly AI research pipeline that scrapes technical blogs, analyses each article with Claude, and synthesises a structured markdown briefing covering the latest developments in AI/ML.

## How it works

1. **Scrape** — Firecrawl fetches each configured source's index page, extracts article links, then scrapes each article
2. **Analyse** — Claude Opus 4.7 analyses each article individually using structured tool use, extracting technical details, use cases, and limitations (prompt caching keeps costs low across the batch)
3. **Synthesise** — Claude Opus 4.7 synthesises all analyses into a cohesive markdown report, grouped by theme rather than source
4. **Save** — Report saved to `research/ai-research-DDMMYY.md`; seen URLs tracked in `state.json` so repeat runs skip already-processed articles

## Setup

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Configure API keys**
```bash
cp .env.example .env
# edit .env and fill in your keys
```

**3. (Optional) Edit sources and topics**

Open `config.yaml` to add/remove blogs or adjust the research topics Claude focuses on.

**4. Run**
```bash
python3 main.py
```

## Configuration

`config.yaml` controls everything:

```yaml
sources:          # index pages to scrape
topics:           # themes to highlight in analysis
analysis:
  days_lookback: 7       # only include articles from last N days
  min_article_length: 200  # skip pages with fewer words
models:
  analyser: claude-opus-4-7
  synthesiser: claude-opus-4-7
```

## Claude Code slash commands

With this project open in Claude Code, three custom commands are available:

| Command | What it does |
|---|---|
| `/research` | Runs the full pipeline |
| `/add-source` | Adds a new blog source to `config.yaml` |
| `/research-status` | Shows last run time, tracked URLs, and links to recent reports |

## Automated weekly schedule

A remote Claude Code routine runs every Monday at 7am (Europe/Berlin). It clones the repo, runs the pipeline, and commits the new report and updated `state.json` back — so URL deduplication carries over between weeks.

Manage the routine at: https://claude.ai/code/routines

## Project structure

```
research-agent/
├── main.py           # orchestration entry point
├── scraper.py        # Firecrawl index + article scraping
├── analyser.py       # per-article Claude analysis
├── synthesiser.py    # Claude synthesis with streaming
├── config.yaml       # sources, topics, model config
├── state.json        # seen URLs + last run timestamp
├── requirements.txt
├── .env.example
└── research/         # generated reports (gitignored)
```

## Environment variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `FIRECRAWL_API_KEY` | Firecrawl API key |
