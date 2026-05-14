import json
import os
import sys
from datetime import datetime, timezone

import yaml
from dotenv import load_dotenv

from scraper import scrape_source
from analyser import analyse_articles
from synthesiser import synthesise

STATE_FILE = "state.json"
CONFIG_FILE = "config.yaml"
RESEARCH_DIR = "research"


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"seen_urls": [], "last_run": None}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_config() -> dict:
    with open(CONFIG_FILE, "r") as f:
        return yaml.safe_load(f)


def check_env() -> bool:
    missing = [k for k in ("FIRECRAWL_API_KEY", "ANTHROPIC_API_KEY") if not os.getenv(k)]
    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in your API keys.")
        return False
    return True


def main() -> None:
    load_dotenv()

    if not check_env():
        sys.exit(1)

    config = load_config()
    state = load_state()

    days_lookback: int = config["analysis"]["days_lookback"]
    min_length: int = config["analysis"]["min_article_length"]
    topics: list[str] = config["topics"]
    sources: list[dict] = config["sources"]
    analyser_model: str = config["models"]["analyser"]
    synthesiser_model: str = config["models"]["synthesiser"]

    seen_urls: set[str] = set(state.get("seen_urls", []))

    # ── 1. Scrape ──────────────────────────────────────────────────────────────
    print("\n=== SCRAPING ===")
    all_articles: list[dict] = []
    for source in sources:
        print(f"\n[{source['name']}]")
        articles = scrape_source(source, days_lookback, seen_urls)
        # apply minimum length filter
        articles = [a for a in articles if a["word_count"] >= min_length]
        all_articles.extend(articles)

    if not all_articles:
        print("\nNo new articles found. Exiting.")
        state["last_run"] = datetime.now(tz=timezone.utc).isoformat()
        save_state(state)
        return

    print(f"\nTotal articles to analyse: {len(all_articles)}")

    # ── 2. Analyse ─────────────────────────────────────────────────────────────
    print("\n=== ANALYSING ===")
    analyses = analyse_articles(all_articles, topics, analyser_model)

    if not analyses:
        print("No analyses produced. Exiting.")
        return

    # ── 3. Synthesise ──────────────────────────────────────────────────────────
    print("\n=== SYNTHESISING ===")
    date_suffix = datetime.now().strftime("%d%m%y")
    output_path = os.path.join(RESEARCH_DIR, f"ai-research-{date_suffix}.md")
    synthesise(analyses, topics, synthesiser_model, output_path)

    # ── 4. Update state ────────────────────────────────────────────────────────
    new_urls = [a["url"] for a in all_articles]
    state["seen_urls"] = list(seen_urls | set(new_urls))
    state["last_run"] = datetime.now(tz=timezone.utc).isoformat()
    save_state(state)

    print(f"\n=== DONE ===")
    print(f"Report saved: {output_path}")
    print(f"Articles processed: {len(all_articles)}")
    print(f"Analyses generated: {len(analyses)}")
    print(f"Total seen URLs tracked: {len(state['seen_urls'])}")


if __name__ == "__main__":
    main()
