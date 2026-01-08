# Web Scraping Directive

## Goal
Scrape data from a target website and store results in a structured format.

## Inputs
- `url` (string, required): The URL to scrape
- `output_format` (string, optional): Format for output data (json, csv, or sheet). Defaults to json.
- `selectors` (dict, optional): CSS selectors for specific data extraction

## Tools/Scripts
- **Primary**: `execution/scrape_single_site.py`
- **Batch**: `execution/scrape_multiple_sites.py` (for multiple URLs)

## Process
1. Validate the URL format
2. Check if site allows scraping (robots.txt check)
3. Execute `scrape_single_site.py` with parameters:
   ```bash
   python execution/scrape_single_site.py --url "<url>" --output-format <format>
   ```
4. Script saves intermediate data to `.tmp/scraped_data_<timestamp>.json`
5. If `output_format` is "sheet", use `execution/upload_to_sheet.py` to create Google Sheet
6. Return the final output location (file path or sheet URL)

## Outputs
- **Intermediate**: `.tmp/scraped_data_<timestamp>.json`
- **Deliverable**: Google Sheet URL (if format=sheet) or JSON file path

## Edge Cases & Learnings

### Rate Limiting
- Some sites limit requests. If you get 429 errors, add `--delay <seconds>` parameter
- Default delay: 1 second between requests

### Dynamic Content
- If content loads via JavaScript, the script won't capture it
- Solution: Use `--dynamic` flag which uses Playwright for JS rendering
- Note: Adds ~2-3 seconds per page

### Authentication Required
- Sites requiring login need session cookies
- Store cookies in `.tmp/cookies.json`
- Pass with `--cookies .tmp/cookies.json`

### API Alternatives
- Always check if the site has an official API first
- APIs are more reliable and faster than scraping

## Error Handling
- **Connection timeout**: Retry up to 3 times with exponential backoff
- **403/401 errors**: Check if authentication is needed
- **404 errors**: Verify URL is correct, fail fast
- **500 errors**: Server issue, retry once after 5 seconds

## Testing
Test with a simple, public site first:
```bash
python execution/scrape_single_site.py --url "https://example.com" --output-format json
```

## Last Updated
2026-01-07 - Initial creation
