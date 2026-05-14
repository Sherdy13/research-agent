Run the weekly AI research pipeline.

Steps:
1. Check that `.env` exists in the project root. If it's missing, warn the user and show the contents of `.env.example` so they know what to fill in.
2. Check that both `FIRECRAWL_API_KEY` and `ANTHROPIC_API_KEY` are set in `.env`. If either is missing, stop and tell the user which key is missing.
3. Run: `python main.py`
4. When the run completes, report:
   - The path of the saved markdown file
   - How many articles were scraped and analysed
   - How many URLs are now tracked in `state.json`
   - Any errors that appeared in the output