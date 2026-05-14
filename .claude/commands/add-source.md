Add a new source to the research agent configuration.

Arguments: $ARGUMENTS (optional — can be "Name | URL" or just a URL)

Steps:
1. If $ARGUMENTS is not provided or incomplete, ask the user for:
   - The source name (e.g. "MIT Tech Review")
   - The index/listing page URL (e.g. https://www.technologyreview.com/topic/artificial-intelligence/)
2. Read `config.yaml`.
3. Check if the URL already exists in the `sources` list. If it does, tell the user and stop.
4. Append the new source to the `sources` list in `config.yaml` with `name:` and `url:` fields.
5. Confirm what was added and show the updated sources list.
